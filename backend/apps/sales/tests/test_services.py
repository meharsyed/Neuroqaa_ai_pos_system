from decimal import Decimal

import pytest
from django.db import transaction

from apps.accounts.models import User
from apps.catalog.models import Category, Inventory, Product, StockMovement
from apps.catalog.services import apply_stock_movement
from apps.sales.models import Sale, SaleItem
from apps.sales.services import create_sale, void_sale

# ── Fixtures ────────────────────────────────────────────────────────────────


@pytest.fixture
def cashier(db):
    return User.objects.create_user(
        username="cashier1",
        email="cashier@test.com",
        password="Pass1234!",
        role="cashier",
    )


@pytest.fixture
def owner(db):
    return User.objects.create_user(
        username="owner1",
        email="owner@test.com",
        password="Pass1234!",
        role="owner",
    )


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


def _sale_items(product, qty="2", price=None):
    return [
        {
            "product_id": product.id,
            "qty": qty,
            "unit_price_paise": price or product.sell_price_paise,
        }
    ]


# ── Happy path ───────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestCreateSale:
    def test_creates_sale_with_correct_totals(self, cashier, product):
        sale = create_sale(
            cashier=cashier,
            items=_sale_items(product, qty="3"),
            payment_method="cash",
            amount_tendered_paise=120000,
        )
        assert sale.status == Sale.Status.COMPLETED
        assert sale.subtotal_paise == 3 * 35000
        assert sale.total_paise == 3 * 35000
        assert sale.cashier == cashier

    def test_sale_number_is_readable(self, cashier, product):
        sale = create_sale(
            cashier=cashier,
            items=_sale_items(product),
            amount_tendered_paise=100000,
        )
        assert sale.sale_number.startswith("SALE-")
        assert not sale.sale_number.startswith("TEMP-")

    def test_stock_is_decremented(self, cashier, product):
        create_sale(
            cashier=cashier,
            items=_sale_items(product, qty="5"),
            amount_tendered_paise=200000,
        )
        product.inventory.refresh_from_db()
        assert product.inventory.stock_qty == Decimal("95")  # started at 100

    def test_stock_movement_type_is_sale(self, cashier, product):
        sale = create_sale(
            cashier=cashier,
            items=_sale_items(product, qty="2"),
            amount_tendered_paise=100000,
        )
        movement = StockMovement.objects.filter(product=product, movement_type="sale").latest(
            "created_at"
        )
        assert movement.qty_change == Decimal("-2")
        assert movement.reference == sale.sale_number

    def test_payment_change_calculated_correctly(self, cashier, product):
        sale = create_sale(
            cashier=cashier,
            items=_sale_items(product, qty="1"),
            payment_method="cash",
            amount_tendered_paise=40000,  # Rs.400 tendered for Rs.350 sale
        )
        assert sale.payment.change_paise == 5000  # Rs.50 change

    def test_sale_level_discount_applied(self, cashier, product):
        sale = create_sale(
            cashier=cashier,
            items=_sale_items(product, qty="1"),
            payment_method="cash",
            amount_tendered_paise=35000,
            discount_paise=5000,  # Rs.50 off
        )
        assert sale.subtotal_paise == 35000
        assert sale.discount_paise == 5000
        assert sale.total_paise == 30000

    def test_multi_product_sale(self, cashier, product, product2):
        items = [
            {"product_id": product.id, "qty": "2", "unit_price_paise": 35000},
            {"product_id": product2.id, "qty": "1", "unit_price_paise": 85000},
        ]
        sale = create_sale(
            cashier=cashier,
            items=items,
            amount_tendered_paise=200000,
        )
        assert sale.total_paise == 2 * 35000 + 85000
        assert SaleItem.objects.filter(sale=sale).count() == 2

    def test_creates_payment_record(self, cashier, product):
        sale = create_sale(
            cashier=cashier,
            items=_sale_items(product),
            payment_method="card",
            amount_tendered_paise=35000,
        )
        assert hasattr(sale, "payment")
        assert sale.payment.method == "card"

    def test_sale_item_subtotal_correct(self, cashier, product):
        sale = create_sale(
            cashier=cashier,
            items=_sale_items(product, qty="3"),
            amount_tendered_paise=120000,
        )
        item = sale.items.get()
        assert item.subtotal_paise == 3 * 35000


# ── Oversell guard ────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestOversellGuard:
    def test_raises_on_insufficient_stock(self, cashier, product):
        with pytest.raises(ValueError, match="Insufficient stock"):
            create_sale(
                cashier=cashier,
                items=_sale_items(product, qty="999"),
                amount_tendered_paise=9999999,
            )

    def test_no_side_effects_on_oversell(self, cashier, product):
        product.inventory.refresh_from_db()
        initial_qty = product.inventory.stock_qty
        initial_sale_count = Sale.objects.count()

        with pytest.raises(ValueError):
            create_sale(
                cashier=cashier,
                items=_sale_items(product, qty="999"),
                amount_tendered_paise=9999999,
            )

        product.inventory.refresh_from_db()
        assert product.inventory.stock_qty == initial_qty
        assert Sale.objects.count() == initial_sale_count

    def test_aggregated_qty_checked_for_same_product_twice(self, cashier, product):
        # product has 100 units; two lines totalling 110 should fail
        items = [
            {"product_id": product.id, "qty": "60", "unit_price_paise": 35000},
            {"product_id": product.id, "qty": "50", "unit_price_paise": 35000},
        ]
        with pytest.raises(ValueError, match="Insufficient stock"):
            create_sale(cashier=cashier, items=items, amount_tendered_paise=9999999)


# ── Atomicity ─────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestSaleAtomicity:
    def test_full_rollback_on_simulated_crash(self, cashier, product):
        product.inventory.refresh_from_db()
        initial_qty = product.inventory.stock_qty
        initial_sale_count = Sale.objects.count()

        with pytest.raises(RuntimeError):  # noqa: SIM117
            with transaction.atomic():
                create_sale(
                    cashier=cashier,
                    items=_sale_items(product, qty="5"),
                    amount_tendered_paise=200000,
                )
                raise RuntimeError("Simulated crash after create_sale")

        product.inventory.refresh_from_db()
        assert product.inventory.stock_qty == initial_qty
        assert Sale.objects.count() == initial_sale_count


# ── Void sale ─────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestVoidSale:
    def test_void_restores_stock(self, cashier, owner, product):
        sale = create_sale(
            cashier=cashier,
            items=_sale_items(product, qty="5"),
            amount_tendered_paise=200000,
        )
        product.inventory.refresh_from_db()
        assert product.inventory.stock_qty == Decimal("95")

        void_sale(sale=sale, voided_by=owner)

        product.inventory.refresh_from_db()
        assert product.inventory.stock_qty == Decimal("100")

    def test_void_changes_status(self, cashier, owner, product):
        sale = create_sale(
            cashier=cashier,
            items=_sale_items(product),
            amount_tendered_paise=100000,
        )
        void_sale(sale=sale, voided_by=owner)
        sale.refresh_from_db()
        assert sale.status == Sale.Status.VOIDED
        assert sale.voided_by == owner
        assert sale.voided_at is not None

    def test_void_creates_return_movements(self, cashier, owner, product):
        sale = create_sale(
            cashier=cashier,
            items=_sale_items(product, qty="3"),
            amount_tendered_paise=120000,
        )
        void_sale(sale=sale, voided_by=owner)

        return_movement = StockMovement.objects.filter(
            product=product, movement_type="return"
        ).latest("created_at")
        assert return_movement.qty_change == Decimal("3")
        assert f"VOID-{sale.sale_number}" in return_movement.reference

    def test_void_already_voided_raises(self, cashier, owner, product):
        sale = create_sale(
            cashier=cashier,
            items=_sale_items(product),
            amount_tendered_paise=100000,
        )
        void_sale(sale=sale, voided_by=owner)
        with pytest.raises(ValueError, match="already voided"):
            void_sale(sale=sale, voided_by=owner)
