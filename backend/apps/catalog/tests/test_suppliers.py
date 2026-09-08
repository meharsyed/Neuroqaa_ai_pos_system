"""
Suppliers: who a batch of stock was bought from.

Deliberately mirrors test_product_removal.py's shape (helper login client,
owner/cashier fixtures) rather than reusing test_api.py's module-level
`user`/`auth_client` fixtures, since this file specifically needs both an
owner and a cashier client to exercise the permission boundary.

Covers: plain CRUD, the read-for-everyone/write-for-management split, the
deactivate-vs-delete behaviour once a supplier has purchase history under it
(the same PROTECT footgun Product.destroy() already guards against), stock-in
attaching a supplier to the resulting movement, and a supplier's purchase
history being served by filtering the existing movements endpoint rather than
a new one.
"""

from decimal import Decimal

import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.catalog.models import Category, Inventory, Product, StockMovement, Supplier
from apps.catalog.services import apply_stock_movement


def _client_for(user):
    c = APIClient()
    r = c.post(reverse("auth-login"), {"email": user.email, "password": "Pass1234!"})
    c.credentials(HTTP_AUTHORIZATION=f"Bearer {r.data['access']}")
    return c


@pytest.fixture
def owner(db):
    return User.objects.create_superuser(
        username="sup_owner", email="sup_owner@test.com", password="Pass1234!",
        first_name="Shop", last_name="Owner", role="owner",
    )


@pytest.fixture
def owner_client(owner):
    return _client_for(owner)


@pytest.fixture
def cashier(db):
    return User.objects.create_user(
        username="sup_cash", email="sup_cash@test.com", password="Pass1234!",
        role="cashier",
    )


@pytest.fixture
def cashier_client(cashier):
    return _client_for(cashier)


@pytest.fixture
def supplier(db):
    return Supplier.objects.create(
        name="Al-Karam Traders", contact_person="Imran", phone="03001234567",
    )


@pytest.fixture
def category(db):
    return Category.objects.create(name="CCTV", slug="cctv")


@pytest.fixture
def product(category):
    p = Product.objects.create(
        name="4MP Bullet Camera", sku="CAM-4MP-01", category=category,
        sell_price_paise=850000, cost_price_paise=550000,
        low_stock_threshold=Decimal("5"),
    )
    Inventory.objects.create(product=p)
    return p


# ---------------------------------------------------------------------------
# CRUD + permissions
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestSupplierAPI:
    def test_list_suppliers(self, owner_client, supplier):
        resp = owner_client.get("/api/suppliers/")
        assert resp.status_code == status.HTTP_200_OK
        names = [s["name"] for s in resp.data["results"]]
        assert "Al-Karam Traders" in names

    def test_cashier_can_read_suppliers(self, cashier_client, supplier):
        # Needed to pick a supplier while stocking a product — read access is
        # not restricted to management the way writes are.
        resp = cashier_client.get("/api/suppliers/")
        assert resp.status_code == status.HTTP_200_OK

    def test_owner_can_create_supplier(self, owner_client):
        # format="json" matters here, not just style: DRF's BooleanField
        # treats a field missing from multipart/HTML-form data as an
        # unchecked checkbox (False), bypassing the model's is_active=True
        # default entirely. A real client (axios) always sends JSON, so this
        # is what the actual create path does.
        resp = owner_client.post("/api/suppliers/", {
            "name": "Zafar Electronics", "phone": "03211234567",
        }, format="json")
        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.data["name"] == "Zafar Electronics"
        assert resp.data["is_active"] is True

    def test_cashier_cannot_create_supplier(self, cashier_client):
        resp = cashier_client.post("/api/suppliers/", {"name": "Should Not Save"}, format="json")
        assert resp.status_code == status.HTTP_403_FORBIDDEN
        assert not Supplier.objects.filter(name="Should Not Save").exists()

    def test_owner_can_update_supplier(self, owner_client, supplier):
        resp = owner_client.patch(f"/api/suppliers/{supplier.id}/", {"phone": "03009999999"}, format="json")
        assert resp.status_code == status.HTTP_200_OK
        supplier.refresh_from_db()
        assert supplier.phone == "03009999999"

    def test_search_supplier(self, owner_client, supplier):
        resp = owner_client.get("/api/suppliers/?search=Karam")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["count"] >= 1

    def test_requires_auth(self):
        resp = APIClient().get("/api/suppliers/")
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED


# ---------------------------------------------------------------------------
# Deactivate vs. delete — the PROTECT boundary
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestSupplierRemoval:
    def test_unused_supplier_is_deleted_outright(self, owner_client, supplier):
        resp = owner_client.delete(f"/api/suppliers/{supplier.id}/")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["archived"] is False
        assert not Supplier.objects.filter(id=supplier.id).exists()

    def test_supplier_with_purchase_history_is_deactivated_not_deleted(
        self, owner_client, supplier, product
    ):
        apply_stock_movement(
            product=product, movement_type="stock_in", qty_change=Decimal("10"),
            supplier=supplier,
        )
        resp = owner_client.delete(f"/api/suppliers/{supplier.id}/")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["archived"] is True
        # Still there — deactivated, not gone. This is the exact case that
        # would otherwise hit StockMovement.supplier's PROTECT and 500.
        supplier.refresh_from_db()
        assert supplier.is_active is False

    def test_deactivated_supplier_hidden_from_default_list_but_not_gone(
        self, owner_client, supplier, product
    ):
        apply_stock_movement(
            product=product, movement_type="stock_in", qty_change=Decimal("10"),
            supplier=supplier,
        )
        owner_client.delete(f"/api/suppliers/{supplier.id}/")

        resp = owner_client.get("/api/suppliers/")
        assert supplier.id not in [s["id"] for s in resp.data["results"]]

        resp = owner_client.get("/api/suppliers/?include_inactive=true")
        assert supplier.id in [s["id"] for s in resp.data["results"]]

    def test_restore_reactivates_a_deactivated_supplier(self, owner_client, supplier, product):
        apply_stock_movement(
            product=product, movement_type="stock_in", qty_change=Decimal("10"),
            supplier=supplier,
        )
        owner_client.delete(f"/api/suppliers/{supplier.id}/")
        resp = owner_client.post(f"/api/suppliers/{supplier.id}/restore/")
        assert resp.status_code == status.HTTP_200_OK
        supplier.refresh_from_db()
        assert supplier.is_active is True


# ---------------------------------------------------------------------------
# Stock-in with a supplier attached
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestStockInWithSupplier:
    def test_stock_in_attaches_supplier_to_the_movement(self, owner_client, product, supplier):
        resp = owner_client.post(
            "/api/inventory/stock-in/",
            {
                "product": product.id, "qty": "50", "cost_price_paise": 55000,
                "supplier": supplier.id, "reference": "PO-2026-014",
            },
            format="json",
        )
        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.data["supplier"] == supplier.id
        assert resp.data["supplier_name"] == supplier.name

        movement = StockMovement.objects.get(id=resp.data["id"])
        assert movement.supplier_id == supplier.id

    def test_stock_in_without_supplier_still_works_unchanged(self, owner_client, product):
        # The whole point of making this optional: nobody who ignores it is
        # affected.
        resp = owner_client.post(
            "/api/inventory/stock-in/", {"product": product.id, "qty": "10"}, format="json",
        )
        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.data["supplier"] is None

    def test_stock_in_rejects_an_inactive_supplier(self, owner_client, product, supplier):
        supplier.is_active = False
        supplier.save(update_fields=["is_active"])
        resp = owner_client.post(
            "/api/inventory/stock-in/",
            {"product": product.id, "qty": "10", "supplier": supplier.id},
            format="json",
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST


# ---------------------------------------------------------------------------
# Purchase history — reusing the movements endpoint, not a new one
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestSupplierPurchaseHistory:
    def test_movements_endpoint_filters_by_supplier_and_type(
        self, owner_client, product, supplier
    ):
        other_supplier = Supplier.objects.create(name="Other Traders")
        apply_stock_movement(
            product=product, movement_type="stock_in", qty_change=Decimal("20"),
            cost_price_paise=50000, supplier=supplier, reference="PO-1",
        )
        apply_stock_movement(
            product=product, movement_type="stock_in", qty_change=Decimal("5"),
            cost_price_paise=48000, supplier=other_supplier, reference="PO-2",
        )
        # A sale (or any non-stock-in movement) for the same product must never
        # show up in a supplier's purchase history.
        apply_stock_movement(product=product, movement_type="sale", qty_change=Decimal("-2"))

        resp = owner_client.get(f"/api/movements/?supplier={supplier.id}&movement_type=stock_in")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["count"] == 1
        row = resp.data["results"][0]
        assert row["supplier"] == supplier.id
        assert row["product"] == product.id
        assert row["cost_price_paise"] == 50000
        assert row["reference"] == "PO-1"
