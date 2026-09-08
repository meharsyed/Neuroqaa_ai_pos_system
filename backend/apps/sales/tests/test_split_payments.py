"""
Split payments — "Rs 2,000 now, the rest on khata".

Until now `Payment` was a OneToOneField, so a bill had exactly one method and
a part payment could not be expressed at all. These tests pin down what the
new shape has to guarantee: the money adds up, the khata only ever carries
the unpaid remainder, and every place that reports on a sale reports the
tenders rather than attributing the whole bill to one of them.
"""

from decimal import Decimal

import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.catalog.models import Category, Inventory, Product
from apps.catalog.services import apply_stock_movement
from apps.customers.models import CreditLedgerEntry, Customer
from apps.customers.services import ledger_balance
from apps.sales.models import Payment, Sale
from apps.sales.services import (
    create_return,
    create_sale,
    get_shift_reconciliation,
    open_shift,
    void_sale,
)


# ── Fixtures ────────────────────────────────────────────────────────────────


@pytest.fixture
def owner(db):
    return User.objects.create_superuser(
        username="sp_owner", email="sp_owner@test.com", password="Pass1234!",
        first_name="Shop", last_name="Owner", role="owner",
    )


@pytest.fixture
def client_auth(owner):
    c = APIClient()
    r = c.post(reverse("auth-login"), {"email": owner.email, "password": "Pass1234!"})
    c.credentials(HTTP_AUTHORIZATION=f"Bearer {r.data['access']}")
    return c


@pytest.fixture
def product(db):
    cat = Category.objects.create(name="Cams", slug="sp-cams")
    p = Product.objects.create(
        name="4MP Bullet", sku="SP-BUL-1", category=cat,
        sell_price_paise=100000, cost_price_paise=60000,   # Rs 1,000
    )
    Inventory.objects.create(product=p)
    apply_stock_movement(product=p, movement_type="stock_in", qty_change=Decimal("500"))
    return p


@pytest.fixture
def customer(db):
    return Customer.objects.create(name="Split Ali", phone="03007654321")


def _items(product, qty="10"):
    """Rs 10,000 of stock by default."""
    return [{"product_id": product.id, "qty": qty, "unit_price_paise": 100000}]


def _tender(method, amount, tendered=None):
    return {"method": method, "amount_paise": amount,
            "amount_tendered_paise": tendered if tendered is not None else amount}


# ── The core arithmetic ─────────────────────────────────────────────────────


@pytest.mark.django_db
class TestPartPayment:
    def test_cash_now_rest_on_khata(self, owner, product, customer):
        sale = create_sale(
            cashier=owner, items=_items(product), customer_id=customer.id,
            tenders=[_tender("cash", 200000)],           # Rs 2,000 of Rs 10,000
        )
        sale.refresh_from_db()
        assert sale.total_paise == 1000000
        assert sale.amount_paid_paise == 200000
        assert sale.credit_paise == 800000

        methods = {p.method: p.amount_paise for p in sale.payments.all()}
        assert methods == {"cash": 200000, "credit": 800000}

    def test_only_the_unpaid_part_reaches_the_khata(self, owner, product, customer):
        create_sale(
            cashier=owner, items=_items(product), customer_id=customer.id,
            tenders=[_tender("cash", 200000)],
        )
        customer.refresh_from_db()
        assert customer.outstanding_paise == 800000
        assert ledger_balance(customer) == 800000

    def test_two_tenders_can_settle_a_bill_in_full(self, owner, product, customer):
        sale = create_sale(
            cashier=owner, items=_items(product), customer_id=customer.id,
            tenders=[_tender("cash", 400000), _tender("card", 600000)],
        )
        sale.refresh_from_db()
        assert sale.amount_paid_paise == 1000000
        assert sale.credit_paise == 0
        # Nothing on khata means no credit row and no ledger entry at all.
        assert not sale.payments.filter(method="credit").exists()
        customer.refresh_from_db()
        assert customer.outstanding_paise == 0

    def test_cash_change_is_worked_out_per_tender(self, owner, product, customer):
        sale = create_sale(
            cashier=owner, items=_items(product), customer_id=customer.id,
            tenders=[_tender("cash", 200000, tendered=250000)],
        )
        cash = sale.payments.get(method="cash")
        assert cash.amount_paise == 200000
        assert cash.amount_tendered_paise == 250000
        assert cash.change_paise == 50000
        # The change does not count as money taken.
        assert sale.amount_paid_paise == 200000

    def test_a_card_tender_never_gives_change(self, owner, product, customer):
        sale = create_sale(
            cashier=owner, items=_items(product), customer_id=customer.id,
            tenders=[_tender("card", 300000, tendered=350000)],
        )
        assert sale.payments.get(method="card").change_paise == 0


# ── What must be refused ────────────────────────────────────────────────────


@pytest.mark.django_db
class TestSplitPaymentsAreGuarded:
    def test_a_remainder_with_no_customer_is_refused(self, owner, product):
        with pytest.raises(ValueError, match="khata"):
            create_sale(
                cashier=owner, items=_items(product),
                tenders=[_tender("cash", 200000)],
            )
        # And nothing survives the refusal.
        assert Sale.objects.count() == 0
        assert Payment.objects.count() == 0

    def test_overpaying_the_bill_is_refused(self, owner, product, customer):
        with pytest.raises(ValueError, match="more than the bill"):
            create_sale(
                cashier=owner, items=_items(product), customer_id=customer.id,
                tenders=[_tender("cash", 900000), _tender("card", 900000)],
            )
        assert Sale.objects.count() == 0

    def test_credit_cannot_be_given_as_a_tender(self, owner, product, customer):
        with pytest.raises(ValueError, match="not a tender"):
            create_sale(
                cashier=owner, items=_items(product), customer_id=customer.id,
                tenders=[_tender("credit", 200000)],
            )

    def test_a_zero_tender_is_refused(self, owner, product, customer):
        with pytest.raises(ValueError, match="more than zero"):
            create_sale(
                cashier=owner, items=_items(product), customer_id=customer.id,
                tenders=[_tender("cash", 0)],
            )

    def test_tendering_less_than_the_tender_settles_is_refused(self, owner, product, customer):
        with pytest.raises(ValueError, match="less than"):
            create_sale(
                cashier=owner, items=_items(product), customer_id=customer.id,
                tenders=[_tender("cash", 200000, tendered=150000)],
            )

    def test_an_unknown_method_is_refused(self, owner, product, customer):
        with pytest.raises(ValueError, match="Unknown payment method"):
            create_sale(
                cashier=owner, items=_items(product), customer_id=customer.id,
                tenders=[_tender("bitcoin", 200000)],
            )

    def test_a_part_payment_is_still_held_to_the_credit_limit(self, owner, product, customer):
        customer.credit_limit_paise = 500000     # Rs 5,000 of credit allowed
        customer.save(update_fields=["credit_limit_paise"])

        # Rs 10,000 bill, Rs 2,000 down — Rs 8,000 of credit, over the limit.
        with pytest.raises(ValueError, match="Credit limit exceeded"):
            create_sale(
                cashier=owner, items=_items(product), customer_id=customer.id,
                tenders=[_tender("cash", 200000)],
            )
        # Rs 6,000 down leaves Rs 4,000 — inside it.
        sale = create_sale(
            cashier=owner, items=_items(product), customer_id=customer.id,
            tenders=[_tender("cash", 600000)],
        )
        assert sale.credit_paise == 400000


# ── The old single-method API keeps working ─────────────────────────────────


@pytest.mark.django_db
class TestLegacyCallersAreUnaffected:
    def test_a_plain_cash_sale_is_recorded_as_fully_paid(self, owner, product):
        sale = create_sale(
            cashier=owner, items=_items(product),
            payment_method="cash", amount_tendered_paise=1000000,
        )
        assert sale.amount_paid_paise == 1000000
        assert sale.credit_paise == 0
        assert sale.payments.count() == 1

    def test_a_plain_credit_sale_puts_the_whole_bill_on_khata(self, owner, product, customer):
        sale = create_sale(
            cashier=owner, items=_items(product), payment_method="credit",
            amount_tendered_paise=0, customer_id=customer.id,
        )
        assert sale.amount_paid_paise == 0
        assert sale.credit_paise == 1000000
        assert sale.payments.get().method == "credit"


# ── Reversals only give back what was actually owed ─────────────────────────


@pytest.mark.django_db
class TestReversingASplitSale:
    def test_voiding_reverses_only_the_khata_part(self, owner, product, customer):
        sale = create_sale(
            cashier=owner, items=_items(product), customer_id=customer.id,
            tenders=[_tender("cash", 200000)],
        )
        customer.refresh_from_db()
        assert customer.outstanding_paise == 800000

        void_sale(sale=sale, voided_by=owner)
        customer.refresh_from_db()
        # The Rs 8,000 comes off; the Rs 2,000 cash is refunded at the till,
        # not turned into credit the customer can spend.
        assert customer.outstanding_paise == 0
        assert ledger_balance(customer) == 0
        assert (
            CreditLedgerEntry.objects.filter(sale=sale, kind="void").get().delta_paise
            == -800000
        )

    def test_a_return_never_takes_more_off_the_khata_than_went_on_it(
        self, owner, product, customer
    ):
        sale = create_sale(
            cashier=owner, items=_items(product), customer_id=customer.id,
            tenders=[_tender("cash", 200000)],       # Rs 8,000 on khata
        )
        # Return every unit — Rs 10,000 of goods against Rs 8,000 of credit.
        create_return(
            cashier=owner, original_sale=sale,
            items=[{"product_id": product.id, "qty": "10"}],
        )
        customer.refresh_from_db()
        assert customer.outstanding_paise == 0        # not -200000
        assert ledger_balance(customer) == 0


# ── Reporting has to follow the money, not the sale ─────────────────────────


@pytest.mark.django_db
class TestReportingSplitsTheMoneyCorrectly:
    def test_the_drawer_only_expects_the_cash_that_was_taken(self, owner, product, customer):
        shift = open_shift(cashier=owner, opening_float_paise=100000)  # Rs 1,000 float
        create_sale(
            cashier=owner, items=_items(product), customer_id=customer.id,
            tenders=[_tender("cash", 200000), _tender("card", 300000)],
        )   # create_sale links the sale to the cashier's open shift itself
        rec = get_shift_reconciliation(shift=shift)
        # Rs 2,000 cash — not the Rs 10,000 bill, and not the Rs 3,000 card.
        assert rec["cash_sales_total_paise"] == 200000
        assert rec["expected_cash_paise"] == 300000

    def test_the_daily_breakdown_splits_a_bill_across_its_tenders(
        self, owner, product, customer
    ):
        from django.utils import timezone

        from apps.sales.reports import daily_summary

        create_sale(
            cashier=owner, items=_items(product), customer_id=customer.id,
            tenders=[_tender("cash", 200000), _tender("card", 300000)],
        )
        breakdown = daily_summary(timezone.localdate())["payment_breakdown"]
        assert breakdown["cash"]["total_paise"] == 200000
        assert breakdown["card"]["total_paise"] == 300000
        assert breakdown["credit"]["total_paise"] == 500000
        # The tenders add up to the bill — the old code counted it three times.
        assert sum(v["total_paise"] for v in breakdown.values()) == 1000000


# ── The API and the receipts ────────────────────────────────────────────────


@pytest.mark.django_db
class TestTheApiAcceptsAndReportsSplits:
    def _payload(self, product, customer, tenders):
        return {
            "items": [{"product_id": product.id, "qty": "10", "unit_price_paise": 100000}],
            "customer_id": customer.id,
            "tenders": tenders,
        }

    def test_posting_tenders_creates_a_part_paid_sale(self, client_auth, product, customer):
        resp = client_auth.post(
            "/api/sales/",
            self._payload(product, customer,
                          [{"method": "cash", "amount_paise": 200000,
                            "amount_tendered_paise": 200000}]),
            format="json",
        )
        assert resp.status_code == status.HTTP_201_CREATED, resp.data
        assert resp.data["amount_paid_paise"] == 200000
        assert resp.data["credit_paise"] == 800000
        assert {p["method"] for p in resp.data["payments"]} == {"cash", "credit"}

    def test_the_single_payment_field_still_answers(self, client_auth, product, customer):
        """BillsPage and the dashboard read sale.payment.method — keep it working."""
        resp = client_auth.post(
            "/api/sales/",
            self._payload(product, customer,
                          [{"method": "cash", "amount_paise": 200000,
                            "amount_tendered_paise": 250000}]),
            format="json",
        )
        assert resp.data["payment"]["method"] == "cash"      # not "credit"
        assert resp.data["payment"]["change_paise"] == 50000

    def test_the_api_refuses_khata_as_a_tender(self, client_auth, product, customer):
        resp = client_auth.post(
            "/api/sales/",
            self._payload(product, customer,
                          [{"method": "credit", "amount_paise": 200000}]),
            format="json",
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert "khata" in str(resp.data).lower()

    def test_a_remainder_with_no_customer_is_a_400_not_a_500(self, client_auth, product):
        resp = client_auth.post(
            "/api/sales/",
            {
                "items": [{"product_id": product.id, "qty": "10",
                           "unit_price_paise": 100000}],
                "tenders": [{"method": "cash", "amount_paise": 200000}],
            },
            format="json",
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert "customer" in str(resp.data).lower()


@pytest.mark.django_db
class TestEveryReceiptShowsTheSplit:
    @pytest.fixture
    def split_sale(self, owner, product, customer):
        return create_sale(
            cashier=owner, items=_items(product), customer_id=customer.id,
            tenders=[_tender("cash", 200000)],
        )

    def test_the_context_carries_both_tenders(self, split_sale):
        from apps.config.utils import get_all_settings
        from apps.sales.receipts import build_receipt_context

        ctx = build_receipt_context(split_sale, get_all_settings())
        assert ctx.is_split
        assert ctx.credit_paise == 800000
        assert ctx.amount_paid_paise == 200000
        # The primary tender is the cash, not the khata line.
        assert ctx.payment_method == "cash"

    def test_the_text_receipt_states_the_cash_and_the_balance(self, split_sale):
        from apps.sales.receipts import render_text_receipt

        text = render_text_receipt(split_sale)
        assert "2,000.00" in text
        assert "8,000.00" in text
        assert "Khata" in text

    def test_the_html_receipt_states_the_cash_and_the_balance(self, split_sale):
        from apps.sales.receipts import render_html_receipt

        html = render_html_receipt(split_sale, format_name="a4")
        assert "2,000.00" in html
        assert "8,000.00" in html
        assert "Balance due" in html

    def test_both_pdfs_render(self, split_sale):
        from apps.sales.receipts import render_pdf_invoice, render_pdf_receipt

        for pdf in (render_pdf_invoice(split_sale), render_pdf_receipt(split_sale)):
            assert pdf[:4] == b"%PDF"
            assert len(pdf) > 1000

    def test_the_whatsapp_message_names_the_balance(self, split_sale, owner):
        from django.test import RequestFactory

        from apps.sales.sharing import build_share_payload

        req = RequestFactory().get("/api/sales/1/share/")
        req.user = owner
        msg = build_share_payload(split_sale, req)["message"]
        assert "Paid now" in msg
        assert "On khata" in msg
