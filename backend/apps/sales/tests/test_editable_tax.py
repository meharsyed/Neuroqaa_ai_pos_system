"""
Tax on a bill.

Two things matter here. The client wants the till able to change the tax on a
bill — and the server must stop taking the browser's word for what the tax is,
which is what it did before: whatever number arrived was stored unexamined.
"""

from decimal import Decimal

import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import ActivityLog, User
from apps.catalog.models import Category, Inventory, Product
from apps.catalog.services import apply_stock_movement
from apps.config.models import Setting
from apps.sales.services import create_sale


def _set(key, value):
    Setting.objects.update_or_create(key=key, defaults={"value": value, "label": key})


@pytest.fixture
def owner(db):
    return User.objects.create_superuser(
        username="tx_owner", email="tx_owner@test.com", password="Pass1234!",
        first_name="Shop", last_name="Owner", role="owner",
    )


@pytest.fixture
def cashier(db):
    return User.objects.create_user(
        username="tx_cash", email="tx_cash@test.com", password="Pass1234!",
        role="cashier",
    )


def _client_for(user):
    c = APIClient()
    r = c.post(reverse("auth-login"), {"email": user.email, "password": "Pass1234!"})
    c.credentials(HTTP_AUTHORIZATION=f"Bearer {r.data['access']}")
    return c


@pytest.fixture
def product(db):
    cat = Category.objects.create(name="Cams", slug="tx-cams")
    p = Product.objects.create(
        name="Dome", sku="TX-1", category=cat,
        sell_price_paise=100000, cost_price_paise=60000,
    )
    Inventory.objects.create(product=p)
    apply_stock_movement(product=p, movement_type="stock_in", qty_change=Decimal("200"))
    return p


def _items(product, qty="10"):
    """Rs 10,000 of goods."""
    return [{"product_id": product.id, "qty": qty, "unit_price_paise": 100000}]


# ── The rate wins ───────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestTaxIsComputed:
    def test_a_rate_produces_the_amount(self, owner, product):
        sale = create_sale(
            cashier=owner, items=_items(product), tax_pct="17",
            payment_method="cash", amount_tendered_paise=1170000,
        )
        assert sale.tax_paise == 170000
        assert sale.tax_pct == Decimal("17")
        assert sale.total_paise == 1170000

    def test_the_rate_applies_after_the_discount(self, owner, product):
        sale = create_sale(
            cashier=owner, items=_items(product), discount_paise=200000, tax_pct="10",
            payment_method="cash", amount_tendered_paise=880000,
        )
        # 10,000 − 2,000 = 8,000 taxable; 10% of that is 800.
        assert sale.tax_paise == 80000
        assert sale.total_paise == 880000

    def test_no_rate_given_falls_back_to_the_shop_setting(self, owner, product):
        _set("tax_pct", "5")
        sale = create_sale(
            cashier=owner, items=_items(product),
            payment_method="cash", amount_tendered_paise=1050000,
        )
        assert sale.tax_paise == 50000
        assert sale.tax_pct == Decimal("5")

    def test_zero_is_a_real_answer_not_a_missing_one(self, owner, product):
        """Setting 0% must mean 0%, not "fall back to the shop's 17%"."""
        _set("tax_pct", "17")
        sale = create_sale(
            cashier=owner, items=_items(product), tax_pct="0",
            payment_method="cash", amount_tendered_paise=1000000,
        )
        assert sale.tax_paise == 0
        assert sale.total_paise == 1000000

    def test_a_half_paisa_rounds_the_same_way_the_till_showed_it(self, owner, product):
        """
        The till computes the tax in JavaScript to show the customer, and the
        server recomputes it to record. They round the same way, or a bill is
        quoted as one number and stored as another.
        """
        sale = create_sale(
            cashier=owner, items=[{"product_id": product.id, "qty": "1",
                                   "unit_price_paise": 100000}],
            tax_pct="2.5", payment_method="cash", amount_tendered_paise=102500,
        )
        # 100000 x 2.5% = 2500 exactly; the half-paisa cases live either side.
        assert sale.tax_paise == 2500
        odd = create_sale(
            cashier=owner, items=[{"product_id": product.id, "qty": "1",
                                   "unit_price_paise": 100001}],
            tax_pct="0.5", payment_method="cash", amount_tendered_paise=200000,
        )
        # 100001 x 0.5% = 500.005 -> 500. Banker's rounding would agree here;
        # the exact .5 case is what differs, and Math.round rounds it up.
        assert odd.tax_paise == 500

    def test_a_flat_amount_is_accepted_with_no_rate_behind_it(self, owner, product):
        sale = create_sale(
            cashier=owner, items=_items(product), tax_paise=12345,
            payment_method="cash", amount_tendered_paise=1012345,
        )
        assert sale.tax_paise == 12345
        assert sale.tax_pct is None      # nothing honest to print as a percentage


@pytest.mark.django_db
class TestTheServerNoLongerTakesTheBrowsersWord:
    def test_tax_larger_than_the_bill_is_refused(self, owner, product):
        with pytest.raises(ValueError, match="more than the bill"):
            create_sale(
                cashier=owner, items=_items(product), tax_paise=99999999,
                payment_method="cash", amount_tendered_paise=99999999,
            )

    def test_a_negative_amount_is_refused(self, owner, product):
        with pytest.raises(ValueError, match="cannot be negative"):
            create_sale(
                cashier=owner, items=_items(product), tax_paise=-100,
                payment_method="cash", amount_tendered_paise=1000000,
            )

    def test_a_rate_over_a_hundred_percent_is_refused(self, owner, product):
        with pytest.raises(ValueError, match="between 0 and 100"):
            create_sale(
                cashier=owner, items=_items(product), tax_pct="150",
                payment_method="cash", amount_tendered_paise=1000000,
            )

    def test_the_api_refuses_a_bad_rate(self, owner, product):
        resp = _client_for(owner).post("/api/sales/", {
            "items": [{"product_id": product.id, "qty": "1", "unit_price_paise": 100000}],
            "tax_pct": "150", "payment_method": "cash", "amount_tendered_paise": 100000,
        }, format="json")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST


# ── The till may change it ─────────────────────────────────────────────────


@pytest.mark.django_db
class TestAnyoneAtTheTillMayChangeIt:
    def test_a_cashier_can_set_the_rate_on_a_bill(self, cashier, product):
        resp = _client_for(cashier).post("/api/sales/", {
            "items": [{"product_id": product.id, "qty": "10", "unit_price_paise": 100000}],
            "tax_pct": "5", "payment_method": "cash", "amount_tendered_paise": 1050000,
        }, format="json")
        assert resp.status_code == status.HTTP_201_CREATED, resp.data
        assert resp.data["tax_paise"] == 50000

    def test_changing_it_leaves_a_record(self, cashier, product):
        """
        The client is not FBR-registered, so the till is trusted with this — but
        trusted and unrecorded are different things.
        """
        _set("tax_pct", "17")
        _client_for(cashier).post("/api/sales/", {
            "items": [{"product_id": product.id, "qty": "1", "unit_price_paise": 100000}],
            "tax_pct": "0", "payment_method": "cash", "amount_tendered_paise": 100000,
        }, format="json")
        entry = ActivityLog.objects.filter(action="tax_overridden").first()
        assert entry is not None
        assert entry.details["shop_rate_pct"] == "17"
        assert entry.details["applied_pct"] == "0.00"

    def test_using_the_shop_rate_is_not_an_override(self, cashier, product):
        _set("tax_pct", "17")
        _client_for(cashier).post("/api/sales/", {
            "items": [{"product_id": product.id, "qty": "1", "unit_price_paise": 100000}],
            "tax_pct": "17", "payment_method": "cash", "amount_tendered_paise": 117000,
        }, format="json")
        assert not ActivityLog.objects.filter(action="tax_overridden").exists()


# ── What gets printed ──────────────────────────────────────────────────────


@pytest.mark.django_db
class TestTheReceiptPrintsTheRateThatWasCharged:
    def test_the_bills_own_rate_is_printed_not_todays_setting(self, owner, product):
        """
        The receipt read the live setting, so raising the shop rate rewrote the
        percentage on every past invoice the next time it was printed.
        """
        _set("tax_pct", "5")
        sale = create_sale(
            cashier=owner, items=_items(product), tax_pct="5",
            payment_method="cash", amount_tendered_paise=1050000,
        )
        _set("tax_pct", "17")          # the shop puts its rate up

        from apps.config.utils import get_all_settings
        from apps.sales.receipts import build_receipt_context, render_html_receipt

        ctx = build_receipt_context(sale, get_all_settings())
        assert ctx.tax_pct == 5.0
        assert "(5%)" in render_html_receipt(sale, format_name="a4")

    def test_every_format_quotes_the_same_rate(self, owner, product):
        """
        The till slip rounded the rate to a whole number, so a bill taxed at
        21.5% printed "Tax (22%)" on the slip and "Tax (21.5%)" on the A4 for
        the same sale. Two documents, one sale, two rates.
        """
        from apps.sales.receipts import build_receipt_context, render_html_receipt
        from apps.config.utils import get_all_settings

        sale = create_sale(
            cashier=owner, items=_items(product), tax_pct="21.5",
            payment_method="cash", amount_tendered_paise=1215000,
        )
        ctx = build_receipt_context(sale, get_all_settings())
        assert f"{ctx.tax_pct:g}" == "21.5"
        assert "(21.5%)" in render_html_receipt(sale, format_name="a4")

        # The thermal slip builds its own label; check the text it produces.
        pct = f" ({ctx.tax_pct:g}%)" if ctx.tax_pct else ""
        assert pct == " (21.5%)", "the till slip is rounding the rate again"

    def test_a_flat_amount_prints_no_percentage_at_all(self, owner, product):
        """Printing "Tax (17%)" next to an amount that is not 17% is a lie."""
        _set("tax_pct", "17")
        sale = create_sale(
            cashier=owner, items=_items(product), tax_paise=12345,
            payment_method="cash", amount_tendered_paise=1012345,
        )
        from apps.sales.receipts import render_html_receipt

        html = render_html_receipt(sale, format_name="a4")
        assert "123.45" in html
        assert "(17%)" not in html
