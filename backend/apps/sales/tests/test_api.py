from decimal import Decimal

import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.catalog.models import Category, Inventory, Product
from apps.catalog.services import apply_stock_movement
from apps.sales.services import create_sale

# ── Fixtures ────────────────────────────────────────────────────────────────


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def owner(db):
    return User.objects.create_superuser(
        username="owner",
        email="owner@test.com",
        password="Pass1234!",
        first_name="Shop",
        last_name="Owner",
        role="owner",
    )


@pytest.fixture
def cashier(db):
    return User.objects.create_user(
        username="cashier1",
        email="cashier@test.com",
        password="Pass1234!",
        role="cashier",
    )


def _auth(client, user):
    resp = client.post(reverse("auth-login"), {"email": user.email, "password": "Pass1234!"})
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {resp.data['access']}")
    return client


@pytest.fixture
def owner_client(api_client, owner):
    return _auth(api_client, owner)


@pytest.fixture
def cashier_client(api_client, cashier):
    return _auth(api_client, cashier)


@pytest.fixture
def category(db):
    return Category.objects.create(name="Tiles", slug="tiles")


@pytest.fixture
def product(category):
    p = Product.objects.create(
        name="Ceramic Tile 30x30",
        sku="TILE-001",
        category=category,
        sell_price_paise=35000,
        cost_price_paise=25000,
        barcode="8901234567890",
    )
    Inventory.objects.create(product=p)
    apply_stock_movement(product=p, movement_type="stock_in", qty_change=Decimal("100"))
    return p


@pytest.fixture
def product2(category):
    p = Product.objects.create(
        name="Basin Tap",
        sku="TAP-001",
        category=category,
        sell_price_paise=85000,
        cost_price_paise=55000,
    )
    Inventory.objects.create(product=p)
    apply_stock_movement(product=p, movement_type="stock_in", qty_change=Decimal("50"))
    return p


# ── Create sale ───────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestCreateSaleAPI:
    def _payload(self, product, qty="2"):
        return {
            "items": [
                {"product_id": product.id, "qty": qty, "unit_price_paise": product.sell_price_paise}
            ],
            "payment_method": "cash",
            "amount_tendered_paise": 200000,
        }

    def test_happy_path_returns_201(self, cashier_client, product):
        resp = cashier_client.post("/api/sales/", self._payload(product), format="json")
        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.data["status"] == "completed"
        assert resp.data["sale_number"].startswith("SALE-")

    def test_response_includes_items_and_payment(self, cashier_client, product):
        resp = cashier_client.post("/api/sales/", self._payload(product), format="json")
        assert len(resp.data["items"]) == 1
        assert resp.data["items"][0]["product_sku"] == "TILE-001"
        assert resp.data["payment"]["method"] == "cash"

    def test_stock_decremented_after_sale(self, cashier_client, product):
        cashier_client.post("/api/sales/", self._payload(product, qty="5"), format="json")
        product.inventory.refresh_from_db()
        assert product.inventory.stock_qty == Decimal("95")

    def test_oversell_returns_400(self, cashier_client, product):
        payload = self._payload(product, qty="999")
        resp = cashier_client.post("/api/sales/", payload, format="json")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert "Insufficient stock" in resp.data["detail"]

    def test_empty_items_returns_400(self, cashier_client):
        payload = {"items": [], "payment_method": "cash", "amount_tendered_paise": 100}
        resp = cashier_client.post("/api/sales/", payload, format="json")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_inactive_product_returns_400(self, cashier_client, product):
        product.is_active = False
        product.save()
        resp = cashier_client.post("/api/sales/", self._payload(product), format="json")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_requires_auth(self, api_client, product):
        resp = api_client.post("/api/sales/", self._payload(product), format="json")
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_multi_product_sale(self, cashier_client, product, product2):
        payload = {
            "items": [
                {"product_id": product.id, "qty": "2", "unit_price_paise": 35000},
                {"product_id": product2.id, "qty": "1", "unit_price_paise": 85000},
            ],
            "payment_method": "cash",
            "amount_tendered_paise": 200000,
        }
        resp = cashier_client.post("/api/sales/", payload, format="json")
        assert resp.status_code == status.HTTP_201_CREATED
        assert len(resp.data["items"]) == 2
        assert resp.data["total_paise"] == 2 * 35000 + 85000


# ── List / Retrieve ────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestSaleListAPI:
    def test_list_sales(self, cashier_client, cashier, product):
        create_sale(
            cashier=cashier,
            items=[{"product_id": product.id, "qty": "1", "unit_price_paise": 35000}],
            amount_tendered_paise=35000,
        )
        resp = cashier_client.get("/api/sales/")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["count"] >= 1

    def test_retrieve_sale(self, cashier_client, cashier, product):
        sale = create_sale(
            cashier=cashier,
            items=[{"product_id": product.id, "qty": "1", "unit_price_paise": 35000}],
            amount_tendered_paise=35000,
        )
        resp = cashier_client.get(f"/api/sales/{sale.pk}/")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["sale_number"] == sale.sale_number


# ── Void sale ─────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestVoidSaleAPI:
    def test_owner_can_void(self, owner_client, owner, product):
        sale = create_sale(
            cashier=owner,
            items=[{"product_id": product.id, "qty": "3", "unit_price_paise": 35000}],
            amount_tendered_paise=120000,
        )
        resp = owner_client.post(f"/api/sales/{sale.pk}/void/")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["status"] == "voided"

    def test_cashier_cannot_void(self, cashier_client, cashier, product):
        sale = create_sale(
            cashier=cashier,
            items=[{"product_id": product.id, "qty": "1", "unit_price_paise": 35000}],
            amount_tendered_paise=35000,
        )
        resp = cashier_client.post(f"/api/sales/{sale.pk}/void/")
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_void_restores_stock(self, owner_client, owner, product):
        sale = create_sale(
            cashier=owner,
            items=[{"product_id": product.id, "qty": "5", "unit_price_paise": 35000}],
            amount_tendered_paise=200000,
        )
        owner_client.post(f"/api/sales/{sale.pk}/void/")
        product.inventory.refresh_from_db()
        assert product.inventory.stock_qty == Decimal("100")  # restored to original


# ── Barcode lookup ────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestBarcodeLookupAPI:
    def test_barcode_returns_product(self, cashier_client, product):
        resp = cashier_client.get(f"/api/products/barcode/{product.barcode}/")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["sku"] == "TILE-001"

    def test_missing_barcode_returns_404(self, cashier_client):
        resp = cashier_client.get("/api/products/barcode/NOTEXIST/")
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_inactive_product_not_found_by_barcode(self, cashier_client, product):
        product.is_active = False
        product.save()
        resp = cashier_client.get(f"/api/products/barcode/{product.barcode}/")
        assert resp.status_code == status.HTTP_404_NOT_FOUND
