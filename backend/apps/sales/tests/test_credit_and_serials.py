"""
Regression tests for the five demo-day fixes (D1-D5).

Each test here maps to a bug that shipped silently. If one of these fails,
that bug is back.
"""

from datetime import date
from decimal import Decimal

import pytest
from rest_framework import status
from rest_framework.test import APIClient
from django.urls import reverse

from apps.accounts.models import User
from apps.catalog.models import Category, Inventory, Product
from apps.catalog.services import apply_stock_movement
from apps.customers.models import Customer
from apps.sales.models import Payment, Sale
from apps.sales.reports import audit_report, audit_report_pdf, daily_summary
from apps.sales.services import create_sale


# ── Fixtures ────────────────────────────────────────────────────────────────


@pytest.fixture
def cashier(db):
    return User.objects.create_user(
        username="cashier_credit", email="cashier_credit@test.com",
        password="Pass1234!", role="cashier",
    )


@pytest.fixture
def client_auth(cashier):
    c = APIClient()
    resp = c.post(reverse("auth-login"), {"email": cashier.email, "password": "Pass1234!"})
    c.credentials(HTTP_AUTHORIZATION=f"Bearer {resp.data['access']}")
    return c


@pytest.fixture
def product(db):
    cat = Category.objects.create(name="Cameras", slug="cameras")
    p = Product.objects.create(
        name="2MP Fixed Dome Camera", sku="DMC-2MP-001", category=cat,
        sell_price_paise=850000, cost_price_paise=500000,
    )
    Inventory.objects.create(product=p)
    apply_stock_movement(product=p, movement_type="stock_in", qty_change=Decimal("50"))
    return p


@pytest.fixture
def customer(db):
    return Customer.objects.create(name="Khalid Shah", phone="03191962423")


def _items(product, qty="2", serials=None):
    item = {
        "product_id": product.id,
        "qty": qty,
        "unit_price_paise": product.sell_price_paise,
    }
    if serials is not None:
        item["serials"] = serials
    return [item]


# ── D3: the credit Payment must be linked to its sale ───────────────────────


@pytest.mark.django_db
class TestCreditPaymentIsLinked:
    def test_credit_sale_has_a_linked_payment(self, cashier, product, customer):
        sale = create_sale(
            cashier=cashier, items=_items(product), payment_method="credit",
            amount_tendered_paise=0, customer_id=customer.id,
        )
        sale.refresh_from_db()
        assert sale.payment is not None, "credit Payment was created with sale=None again"
        assert sale.payment.method == "credit"

    def test_nothing_is_tendered_on_a_credit_sale(self, cashier, product, customer):
        sale = create_sale(
            cashier=cashier, items=_items(product), payment_method="credit",
            amount_tendered_paise=0, customer_id=customer.id,
        )
        assert sale.payment.amount_tendered_paise == 0
        assert sale.payment.change_paise == 0

    def test_no_orphan_payment_rows_are_created(self, cashier, product, customer):
        create_sale(
            cashier=cashier, items=_items(product), payment_method="credit",
            amount_tendered_paise=0, customer_id=customer.id,
        )
        assert Payment.objects.filter(sale__isnull=True).count() == 0

    def test_customer_balance_increases_by_the_total(self, cashier, product, customer):
        sale = create_sale(
            cashier=cashier, items=_items(product), payment_method="credit",
            amount_tendered_paise=0, customer_id=customer.id,
        )
        customer.refresh_from_db()
        assert customer.outstanding_paise == sale.total_paise

    def test_receipt_says_credit_not_cash(self, cashier, product, customer):
        """The whole point of D3: the printed receipt must not claim cash."""
        from apps.sales.receipts import build_receipt_context

        sale = create_sale(
            cashier=cashier, items=_items(product), payment_method="credit",
            amount_tendered_paise=0, customer_id=customer.id,
        )
        ctx = build_receipt_context(Sale.objects.get(pk=sale.pk), {})
        assert ctx.payment_method == "credit"
        assert ctx.tendered_paise == 0


# ── D4: a credit sale with no customer bills nobody ─────────────────────────


@pytest.mark.django_db
class TestCreditRequiresCustomer:
    def test_credit_without_customer_is_rejected(self, client_auth, product):
        resp = client_auth.post("/api/sales/", {
            "items": _items(product),
            "payment_method": "credit",
            "amount_tendered_paise": 0,
        }, format="json")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert "customer" in str(resp.data).lower()

    def test_rejected_credit_sale_creates_nothing(self, client_auth, product):
        before = Sale.objects.count()
        client_auth.post("/api/sales/", {
            "items": _items(product),
            "payment_method": "credit",
            "amount_tendered_paise": 0,
        }, format="json")
        assert Sale.objects.count() == before

    def test_cash_sale_still_works_without_a_customer(self, client_auth, product):
        resp = client_auth.post("/api/sales/", {
            "items": _items(product),
            "payment_method": "cash",
            "amount_tendered_paise": 2000000,
        }, format="json")
        assert resp.status_code == status.HTTP_201_CREATED


# ── D1: a duplicate serial must not 500 and lose the cart ───────────────────


@pytest.mark.django_db
class TestDuplicateSerial:
    def test_duplicate_serial_returns_400_not_500(self, client_auth, product):
        dupes = [{"serial": "SN-DUP-1"}, {"serial": "SN-DUP-1"}]
        resp = client_auth.post("/api/sales/", {
            "items": _items(product, qty="2", serials=dupes),
            "payment_method": "cash",
            "amount_tendered_paise": 2000000,
        }, format="json")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST, (
            f"expected a clean 400, got {resp.status_code}"
        )
        assert "serial" in str(resp.data).lower()

    def test_duplicate_serial_rolls_back_completely(self, client_auth, product):
        before_sales = Sale.objects.count()
        before_stock = Inventory.objects.get(product=product).stock_qty
        client_auth.post("/api/sales/", {
            "items": _items(product, qty="2", serials=[{"serial": "SN-X"}, {"serial": "SN-X"}]),
            "payment_method": "cash",
            "amount_tendered_paise": 2000000,
        }, format="json")
        assert Sale.objects.count() == before_sales
        assert Inventory.objects.get(product=product).stock_qty == before_stock

    def test_distinct_serials_are_accepted(self, client_auth, product):
        resp = client_auth.post("/api/sales/", {
            "items": _items(product, qty="2",
                            serials=[{"serial": "SN-A", "warranty_months": 12},
                                     {"serial": "SN-B", "warranty_months": 12}]),
            "payment_method": "cash",
            "amount_tendered_paise": 2000000,
        }, format="json")
        assert resp.status_code == status.HTTP_201_CREATED


# ── D2: reporting must survive a credit sale ────────────────────────────────


@pytest.mark.django_db
class TestReportsWithCreditSales:
    @pytest.fixture(autouse=True)
    def _a_credit_and_a_cash_sale(self, cashier, product, customer):
        create_sale(cashier=cashier, items=_items(product), payment_method="credit",
                    amount_tendered_paise=0, customer_id=customer.id)
        create_sale(cashier=cashier, items=_items(product), payment_method="cash",
                    amount_tendered_paise=2000000)

    def test_daily_summary_does_not_crash(self):
        data = daily_summary(date.today())
        assert data["transaction_count"] == 2
        assert "credit" in data["payment_breakdown"]

    def test_no_none_key_in_payment_breakdown(self):
        """A None key is what made the PDF export raise AttributeError."""
        data = daily_summary(date.today())
        assert None not in data["payment_breakdown"]
        assert all(isinstance(k, str) for k in data["payment_breakdown"])

    def test_audit_report_pdf_renders(self):
        data = audit_report(date.today(), date.today())
        pdf = audit_report_pdf(data, shop_name="Speed Tech Solutions")
        assert pdf[:4] == b"%PDF"
        assert len(pdf) > 1000

    def test_legacy_credit_sale_with_no_payment_row(self, cashier, product):
        """Sales made before the D3 fix have no Payment at all; grouping them
        must still work rather than blowing up on None.upper()."""
        sale = create_sale(cashier=cashier, items=_items(product),
                           payment_method="cash", amount_tendered_paise=2000000)
        Payment.objects.filter(sale=sale).delete()

        data = daily_summary(date.today())
        assert None not in data["payment_breakdown"]
        pdf = audit_report_pdf(audit_report(date.today(), date.today()))
        assert pdf[:4] == b"%PDF"


# ── Receipts render for a credit sale in every format ───────────────────────


@pytest.mark.django_db
def test_all_three_renderers_handle_a_credit_sale(cashier, product, customer):
    from apps.sales.receipts import (
        build_receipt_context, document, thermal_pdf, render_text_receipt,
    )

    sale = create_sale(cashier=cashier, items=_items(product), payment_method="credit",
                       amount_tendered_paise=0, customer_id=customer.id)
    sale = Sale.objects.get(pk=sale.pk)
    ctx = build_receipt_context(sale, {})

    for size in ("a4", "a5"):
        pdf = document.render(ctx, size)
        assert pdf[:4] == b"%PDF", f"{size} invoice did not render"
    for width in (80, 58):
        pdf = thermal_pdf.render(ctx, width)
        assert pdf[:4] == b"%PDF", f"{width}mm slip did not render"

    text = render_text_receipt(sale)
    assert sale.sale_number in text
