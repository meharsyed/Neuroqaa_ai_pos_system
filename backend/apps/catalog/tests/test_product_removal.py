"""
Taking a product off the list.

The rule that matters: a product that has ever been sold must never be deleted,
because every bill it appeared on points at it. A shop producing a two-year-old
invoice for a warranty claim needs that row to still be there.
"""

from decimal import Decimal

import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.catalog.models import Category, Inventory, Product
from apps.catalog.services import apply_stock_movement
from apps.sales.models import Sale
from apps.sales.services import create_sale


def _client_for(user):
    c = APIClient()
    r = c.post(reverse("auth-login"), {"email": user.email, "password": "Pass1234!"})
    c.credentials(HTTP_AUTHORIZATION=f"Bearer {r.data['access']}")
    return c


@pytest.fixture
def owner(db):
    return User.objects.create_superuser(
        username="pr_owner", email="pr_owner@test.com", password="Pass1234!",
        first_name="Shop", last_name="Owner", role="owner",
    )


@pytest.fixture
def owner_client(owner):
    return _client_for(owner)


@pytest.fixture
def category(db):
    return Category.objects.create(name="Cams", slug="pr-cams")


@pytest.fixture
def fresh_product(category):
    """Just typed in. No stock, no movements, no sales."""
    p = Product.objects.create(
        name="Typo Cam", sku="PR-TYPO", category=category,
        sell_price_paise=100000, cost_price_paise=60000,
    )
    Inventory.objects.create(product=p)
    return p


@pytest.fixture
def used_product(category):
    p = Product.objects.create(
        name="Dome 4MP", sku="PR-DOM", category=category,
        sell_price_paise=100000, cost_price_paise=60000,
    )
    Inventory.objects.create(product=p)
    apply_stock_movement(product=p, movement_type="stock_in", qty_change=Decimal("50"))
    return p


@pytest.mark.django_db
class TestRemovingAProduct:
    def test_a_typo_is_deleted_outright(self, owner_client, fresh_product):
        resp = owner_client.delete(f"/api/products/{fresh_product.id}/")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["archived"] is False
        assert not Product.objects.filter(pk=fresh_product.pk).exists()

    def test_a_product_with_history_is_archived_not_deleted(self, owner_client, used_product):
        resp = owner_client.delete(f"/api/products/{used_product.id}/")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["archived"] is True
        used_product.refresh_from_db()
        assert used_product.is_active is False
        assert Product.objects.filter(pk=used_product.pk).exists()

    def test_it_no_longer_returns_a_500(self, owner_client, used_product):
        """
        This used to raise ProtectedError straight through as a 500, which is
        how the feature came to be missing from the interface entirely.
        """
        resp = owner_client.delete(f"/api/products/{used_product.id}/")
        assert resp.status_code < 500

    def test_an_archived_product_stays_on_its_old_bills(self, owner, owner_client, used_product):
        sale = create_sale(
            cashier=owner,
            items=[{"product_id": used_product.id, "qty": "2", "unit_price_paise": 100000}],
            payment_method="cash", amount_tendered_paise=200000,
        )
        owner_client.delete(f"/api/products/{used_product.id}/")

        fetched = Sale.objects.prefetch_related("items__product").get(pk=sale.pk)
        item = fetched.items.get()
        assert item.product.name == "Dome 4MP"
        assert item.subtotal_paise == 200000

        # And the bill still renders — a warranty claim two years on.
        resp = owner_client.get(f"/api/sales/{sale.id}/receipt/pdf/?template=invoice")
        assert resp.status_code == status.HTTP_200_OK

    def test_an_archived_product_leaves_the_till(self, owner_client, used_product):
        owner_client.delete(f"/api/products/{used_product.id}/")
        listed = owner_client.get("/api/products/").data["results"]
        assert used_product.id not in [p["id"] for p in listed]

    def test_it_can_be_found_again_and_restored(self, owner_client, used_product):
        owner_client.delete(f"/api/products/{used_product.id}/")

        archived = owner_client.get("/api/products/?include_inactive=true").data["results"]
        assert used_product.id in [p["id"] for p in archived]

        resp = owner_client.post(f"/api/products/{used_product.id}/restore/")
        assert resp.status_code == status.HTTP_200_OK
        used_product.refresh_from_db()
        assert used_product.is_active is True

    def test_archiving_twice_says_so(self, owner_client, used_product):
        owner_client.delete(f"/api/products/{used_product.id}/")
        resp = owner_client.delete(f"/api/products/{used_product.id}/")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert "already archived" in resp.data["detail"]

    def test_the_interface_can_ask_which_it_will_be(self, owner_client, fresh_product, used_product):
        fresh = owner_client.get(f"/api/products/{fresh_product.id}/removal-check/").data
        assert fresh["can_delete"] is True
        assert fresh["reasons"] == []

        used = owner_client.get(f"/api/products/{used_product.id}/removal-check/").data
        assert used["can_delete"] is False
        assert any("stock" in r for r in used["reasons"])

    def test_a_cashier_cannot_remove_anything(self, db, used_product):
        cashier = User.objects.create_user(
            username="pr_cash", email="pr_cash@test.com", password="Pass1234!",
            role="cashier",
        )
        c = _client_for(cashier)
        assert c.delete(f"/api/products/{used_product.id}/").status_code == status.HTTP_403_FORBIDDEN
        assert c.post(f"/api/products/{used_product.id}/restore/").status_code == status.HTTP_403_FORBIDDEN
