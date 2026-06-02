from decimal import Decimal

import pytest
from django.db import transaction

from apps.catalog.models import Category, Inventory, Product, StockMovement
from apps.catalog.services import apply_stock_movement, set_opening_stock


@pytest.fixture
def category(db):
    return Category.objects.create(name="Floor Tiles", slug="floor-tiles")


@pytest.fixture
def product(category):
    p = Product.objects.create(
        name="Blue Ceramic Tile 30x30",
        sku="TILE-001",
        category=category,
        sell_price_paise=35000,
        cost_price_paise=25000,
        low_stock_threshold=Decimal("20"),
    )
    Inventory.objects.create(product=p)
    return p


@pytest.mark.django_db
class TestApplyStockMovement:
    def test_stock_in_increases_qty(self, product):
        movement = apply_stock_movement(
            product=product,
            movement_type=StockMovement.MovementType.STOCK_IN,
            qty_change=Decimal("100"),
        )
        product.inventory.refresh_from_db()
        assert product.inventory.stock_qty == Decimal("100")
        assert movement.qty_after == Decimal("100")
        assert movement.qty_change == Decimal("100")
        assert movement.movement_type == "stock_in"

    def test_sale_decreases_qty(self, product):
        apply_stock_movement(product=product, movement_type="stock_in", qty_change=Decimal("100"))
        apply_stock_movement(product=product, movement_type="sale", qty_change=Decimal("-10"))
        product.inventory.refresh_from_db()
        assert product.inventory.stock_qty == Decimal("90")

    def test_fractional_qty_supported(self, product):
        """Inventory supports kg/litre with 3 decimal places."""
        apply_stock_movement(
            product=product, movement_type="stock_in", qty_change=Decimal("15.750")
        )
        product.inventory.refresh_from_db()
        assert product.inventory.stock_qty == Decimal("15.750")

    def test_movement_writes_qty_after_snapshot(self, product):
        apply_stock_movement(product=product, movement_type="stock_in", qty_change=Decimal("50"))
        apply_stock_movement(product=product, movement_type="sale", qty_change=Decimal("-5"))
        movements = list(StockMovement.objects.filter(product=product).order_by("created_at"))
        assert movements[0].qty_after == Decimal("50")
        assert movements[1].qty_after == Decimal("45")

    def test_multiple_movements_are_accumulated(self, product):
        apply_stock_movement(product=product, movement_type="stock_in", qty_change=Decimal("100"))
        apply_stock_movement(product=product, movement_type="sale", qty_change=Decimal("-10"))
        apply_stock_movement(product=product, movement_type="return", qty_change=Decimal("2"))
        product.inventory.refresh_from_db()
        assert product.inventory.stock_qty == Decimal("92")
        assert StockMovement.objects.filter(product=product).count() == 3

    def test_cost_price_captured_on_stock_in(self, product):
        movement = apply_stock_movement(
            product=product,
            movement_type="stock_in",
            qty_change=Decimal("50"),
            cost_price_paise=24000,
        )
        assert movement.cost_price_paise == 24000

    def test_reference_stored(self, product):
        movement = apply_stock_movement(
            product=product,
            movement_type="stock_in",
            qty_change=Decimal("50"),
            reference="PO-2026-001",
        )
        assert movement.reference == "PO-2026-001"


@pytest.mark.django_db
class TestAppendOnlyEnforcement:
    def test_update_raises_value_error(self, product):
        movement = apply_stock_movement(
            product=product, movement_type="stock_in", qty_change=Decimal("50")
        )
        with pytest.raises(ValueError, match="append-only"):
            movement.save()

    def test_delete_raises_value_error(self, product):
        movement = apply_stock_movement(
            product=product, movement_type="stock_in", qty_change=Decimal("50")
        )
        with pytest.raises(ValueError, match="append-only"):
            movement.delete()


@pytest.mark.django_db
class TestAtomicity:
    def test_both_writes_roll_back_on_failure(self, product):
        initial_qty = product.inventory.stock_qty
        initial_count = StockMovement.objects.filter(product=product).count()

        with pytest.raises(RuntimeError):  # noqa: SIM117
            with transaction.atomic():
                apply_stock_movement(
                    product=product, movement_type="stock_in", qty_change=Decimal("50")
                )
                raise RuntimeError("Simulated mid-transaction crash")

        product.inventory.refresh_from_db()
        assert product.inventory.stock_qty == initial_qty
        assert StockMovement.objects.filter(product=product).count() == initial_count


@pytest.mark.django_db
class TestSetOpeningStock:
    def test_sets_stock_when_zero(self, product):
        movement = set_opening_stock(product=product, qty=Decimal("200"), cost_price_paise=25000)
        product.inventory.refresh_from_db()
        assert product.inventory.stock_qty == Decimal("200")
        assert movement.movement_type == "opening"

    def test_raises_if_stock_already_set(self, product):
        set_opening_stock(product=product, qty=Decimal("100"))
        with pytest.raises(ValueError, match="already has stock"):
            set_opening_stock(product=product, qty=Decimal("50"))


@pytest.mark.django_db
class TestIsLowStock:
    def test_low_stock_flag_when_below_threshold(self, product):
        apply_stock_movement(product=product, movement_type="stock_in", qty_change=Decimal("15"))
        product.inventory.refresh_from_db()
        assert product.inventory.is_low_stock is True  # threshold=20, qty=15

    def test_ok_when_above_threshold(self, product):
        apply_stock_movement(product=product, movement_type="stock_in", qty_change=Decimal("50"))
        product.inventory.refresh_from_db()
        assert product.inventory.is_low_stock is False  # threshold=20, qty=50

    def test_no_low_stock_when_threshold_is_zero(self, product):
        product.low_stock_threshold = Decimal("0")
        product.save()
        apply_stock_movement(product=product, movement_type="stock_in", qty_change=Decimal("5"))
        product.inventory.refresh_from_db()
        assert product.inventory.is_low_stock is False
