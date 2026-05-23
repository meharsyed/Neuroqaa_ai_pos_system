import io
import pytest
from decimal import Decimal
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.catalog.models import Category, Inventory, Product, StockMovement


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def user(db):
    return User.objects.create_superuser(
        username="admin", email="admin@test.com",
        password="Pass1234!", first_name="Admin", last_name="User", role="owner",
    )


@pytest.fixture
def auth_client(api_client, user):
    resp = api_client.post(reverse("auth-login"), {"email": user.email, "password": "Pass1234!"})
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {resp.data['access']}")
    return api_client


@pytest.fixture
def category(db):
    return Category.objects.create(name="Sanitary Fittings", slug="sanitary-fittings")


@pytest.fixture
def product(category):
    p = Product.objects.create(
        name="Basin Tap Chrome",
        sku="TAP-001",
        category=category,
        sell_price_paise=85000,
        cost_price_paise=55000,
        low_stock_threshold=Decimal("5"),
    )
    Inventory.objects.create(product=p)
    return p


# ---------------------------------------------------------------------------
# Categories
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestCategoryAPI:
    def test_list_categories(self, auth_client, category):
        resp = auth_client.get("/api/categories/")
        assert resp.status_code == status.HTTP_200_OK
        names = [c["name"] for c in resp.data["results"]]
        assert "Sanitary Fittings" in names

    def test_create_category(self, auth_client):
        resp = auth_client.post("/api/categories/", {"name": "Wall Tiles", "slug": "wall-tiles"})
        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.data["name"] == "Wall Tiles"

    def test_search_category(self, auth_client, category):
        resp = auth_client.get("/api/categories/?search=sanitary")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["count"] >= 1


# ---------------------------------------------------------------------------
# Products
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestProductAPI:
    def test_list_products(self, auth_client, product):
        resp = auth_client.get("/api/products/")
        assert resp.status_code == status.HTTP_200_OK
        skus = [p["sku"] for p in resp.data["results"]]
        assert "TAP-001" in skus

    def test_create_product_creates_inventory(self, auth_client, category):
        resp = auth_client.post("/api/products/", {
            "name": "Shower Head", "sku": "SH-001",
            "category": category.id, "unit": "pcs",
            "cost_price_paise": 45000, "sell_price_paise": 65000,
        })
        assert resp.status_code == status.HTTP_201_CREATED
        assert Inventory.objects.filter(product__sku="SH-001").exists()

    def test_product_has_formatted_prices(self, auth_client, product):
        resp = auth_client.get(f"/api/products/{product.id}/")
        assert resp.data["cost_price"] == "Rs. 550.00"
        assert resp.data["sell_price"] == "Rs. 850.00"

    def test_filter_by_category(self, auth_client, product, category):
        resp = auth_client.get(f"/api/products/?category={category.id}")
        assert resp.status_code == status.HTTP_200_OK
        assert all(p["category"] == category.id for p in resp.data["results"])

    def test_search_by_sku(self, auth_client, product):
        resp = auth_client.get("/api/products/?search=TAP-001")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["count"] >= 1

    def test_search_by_barcode(self, auth_client, product):
        product.barcode = "8901234567890"
        product.save()
        resp = auth_client.get("/api/products/?barcode=8901234567890")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["count"] == 1

    def test_low_stock_endpoint(self, auth_client, product):
        # Put product below threshold
        from apps.catalog.services import apply_stock_movement
        apply_stock_movement(product=product, movement_type="stock_in", qty_change=Decimal("3"))
        resp = auth_client.get("/api/products/low-stock/")
        assert resp.status_code == status.HTTP_200_OK
        skus = [p["sku"] for p in resp.data]
        assert "TAP-001" in skus

    def test_low_stock_excludes_ok_products(self, auth_client, product):
        from apps.catalog.services import apply_stock_movement
        apply_stock_movement(product=product, movement_type="stock_in", qty_change=Decimal("100"))
        resp = auth_client.get("/api/products/low-stock/")
        skus = [p["sku"] for p in resp.data]
        assert "TAP-001" not in skus


# ---------------------------------------------------------------------------
# Inventory / Stock-in
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestInventoryAPI:
    def test_stock_in_creates_movement(self, auth_client, product):
        resp = auth_client.post("/api/inventory/stock-in/", {
            "product": product.id,
            "qty": "50.000",
            "cost_price_paise": 55000,
            "reference": "PO-2026-001",
        })
        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.data["movement_type"] == "stock_in"
        assert Decimal(resp.data["qty_after"]) == Decimal("50")

    def test_stock_in_updates_inventory(self, auth_client, product):
        auth_client.post("/api/inventory/stock-in/", {"product": product.id, "qty": "25"})
        product.inventory.refresh_from_db()
        assert product.inventory.stock_qty == Decimal("25")

    def test_stock_in_rejects_zero_qty(self, auth_client, product):
        resp = auth_client.post("/api/inventory/stock-in/", {"product": product.id, "qty": "0"})
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_stock_in_requires_auth(self, api_client, product):
        resp = api_client.post("/api/inventory/stock-in/", {"product": product.id, "qty": "10"})
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED


# ---------------------------------------------------------------------------
# CSV Import
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestCSVImport:
    def _make_csv(self, rows: list[dict]) -> io.BytesIO:
        headers = "name,sku,barcode,category,unit,cost_price,sell_price,low_stock_threshold,is_active"
        lines = [headers] + [
            ",".join(str(r.get(h, "")) for h in headers.split(","))
            for r in rows
        ]
        return io.BytesIO("\n".join(lines).encode("utf-8"))

    def test_import_creates_products_and_inventory(self, auth_client, category):
        csv_file = self._make_csv([
            {"name": "Floor Tile 60x60", "sku": "FT-060", "category": category.name,
             "unit": "pcs", "cost_price": "180", "sell_price": "250", "is_active": "True"},
            {"name": "Wall Tile 30x60", "sku": "WT-306", "category": category.name,
             "unit": "pcs", "cost_price": "150", "sell_price": "210", "is_active": "True"},
        ])
        resp = auth_client.post(
            "/api/products/import/",
            {"file": csv_file},
            format="multipart",
        )
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["imported"] == 2
        assert Product.objects.filter(sku__in=["FT-060", "WT-306"]).count() == 2
        assert Inventory.objects.filter(product__sku__in=["FT-060", "WT-306"]).count() == 2

    def test_import_converts_rupees_to_paise(self, auth_client, category):
        csv_file = self._make_csv([
            {"name": "Test Tile", "sku": "TEST-001", "category": category.name,
             "unit": "pcs", "cost_price": "250.50", "sell_price": "350.00", "is_active": "True"},
        ])
        auth_client.post("/api/products/import/", {"file": csv_file}, format="multipart")
        product = Product.objects.get(sku="TEST-001")
        assert product.cost_price_paise == 25050
        assert product.sell_price_paise == 35000

    def test_import_updates_existing_product(self, auth_client, product):
        csv_file = self._make_csv([
            {"name": "Basin Tap Chrome Updated", "sku": product.sku,
             "unit": "pcs", "cost_price": "600", "sell_price": "900", "is_active": "True"},
        ])
        resp = auth_client.post("/api/products/import/", {"file": csv_file}, format="multipart")
        assert resp.status_code == status.HTTP_200_OK
        product.refresh_from_db()
        assert product.sell_price_paise == 90000

    def test_import_no_file_returns_400(self, auth_client):
        resp = auth_client.post("/api/products/import/", {}, format="multipart")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST