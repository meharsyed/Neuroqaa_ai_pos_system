"""
Installation charges — labour the shop bills, collects, and hands to a technician.

The whole point of this feature is a number that the customer pays but the shop
does not earn. So the tests that matter are the ones proving it stays OUT of
revenue and profit while staying IN the amount due, the receipts and the khata.
"""

from decimal import Decimal

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.catalog.models import Category, Inventory, Product
from apps.catalog.services import apply_stock_movement
from apps.customers.models import CreditLedgerEntry, Customer
from apps.customers.services import ledger_balance
from apps.sales.reports import audit_report, daily_summary
from apps.sales.services import (
    create_return,
    create_sale,
    get_shift_reconciliation,
    open_shift,
    void_sale,
)


@pytest.fixture
def owner(db):
    return User.objects.create_superuser(
        username="in_owner", email="in_owner@test.com", password="Pass1234!",
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
    cat = Category.objects.create(name="Cams", slug="in-cams")
    p = Product.objects.create(
        name="Dome 4MP", sku="IN-DOM-1", category=cat,
        sell_price_paise=100000, cost_price_paise=60000,   # Rs 1,000 / Rs 600
    )
    Inventory.objects.create(product=p)
    apply_stock_movement(product=p, movement_type="stock_in", qty_change=Decimal("500"))
    return p


@pytest.fixture
def customer(db):
    return Customer.objects.create(name="Install Ali", phone="03009998877")


def _items(product, qty="10"):
    """Rs 10,000 of goods."""
    return [{"product_id": product.id, "qty": qty, "unit_price_paise": 100000}]


def _tender(method, amount, tendered=None):
    return {"method": method, "amount_paise": amount,
            "amount_tendered_paise": tendered if tendered is not None else amount}


# ── The arithmetic ──────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestTheBillAddsUp:
    def test_the_customer_pays_goods_plus_installation(self, owner, product):
        sale = create_sale(
            cashier=owner, items=_items(product),
            installation_paise=500000,                      # Rs 5,000 labour
            payment_method="cash", amount_tendered_paise=1500000,
        )
        assert sale.total_paise == 1000000                  # goods only
        assert sale.installation_paise == 500000
        assert sale.amount_due_paise == 1500000             # what was handed over
        assert sale.credit_paise == 0

    def test_change_is_worked_out_against_the_amount_due(self, owner, product):
        sale = create_sale(
            cashier=owner, items=_items(product), installation_paise=500000,
            payment_method="cash", amount_tendered_paise=1600000,
        )
        # Rs 16,000 tendered on a Rs 15,000 bill — Rs 1,000 back, not Rs 6,000.
        assert sale.primary_payment.change_paise == 100000

    def test_installation_is_not_taxed_as_goods(self, owner, product):
        sale = create_sale(
            cashier=owner, items=_items(product), tax_paise=170000,
            installation_paise=500000,
            payment_method="cash", amount_tendered_paise=1670000,
        )
        # 10,000 goods + 1,700 tax = 11,700 revenue; labour rides on top untaxed.
        assert sale.total_paise == 1170000
        assert sale.amount_due_paise == 1670000

    def test_a_negative_installation_charge_is_refused(self, owner, product):
        with pytest.raises(ValueError, match="cannot be negative"):
            create_sale(
                cashier=owner, items=_items(product), installation_paise=-1,
                payment_method="cash", amount_tendered_paise=1000000,
            )

    def test_a_bill_without_installation_is_completely_unchanged(self, owner, product):
        sale = create_sale(
            cashier=owner, items=_items(product),
            payment_method="cash", amount_tendered_paise=1000000,
        )
        assert sale.installation_paise == 0
        assert sale.amount_due_paise == sale.total_paise


# ── The reason the feature exists ───────────────────────────────────────────


@pytest.mark.django_db
class TestItIsNeverRevenue:
    def test_it_stays_out_of_the_daily_revenue(self, owner, product):
        create_sale(
            cashier=owner, items=_items(product), installation_paise=500000,
            payment_method="cash", amount_tendered_paise=1500000,
        )
        summary = daily_summary(timezone.localdate())
        assert summary["total_revenue_paise"] == 1000000     # not 1,500,000
        assert summary["installation"]["charged_paise"] == 500000
        assert summary["installation"]["collected_paise"] == 500000
        assert summary["installation"]["outstanding_paise"] == 0

    def test_it_stays_out_of_gross_profit_and_margin(self, owner, product):
        today = timezone.localdate()
        create_sale(
            cashier=owner, items=_items(product), installation_paise=500000,
            payment_method="cash", amount_tendered_paise=1500000,
        )
        rep = audit_report(today, today)
        # Rs 10,000 revenue against Rs 6,000 of cost — labour must not flatter it.
        assert rep["total_revenue_paise"] == 1000000
        assert rep["gross_profit_paise"] == 400000
        assert rep["gross_margin_pct"] == 40.0
        assert rep["installation"]["charged_paise"] == 500000

    def test_the_payment_breakdown_still_sums_to_revenue_plus_labour(self, owner, product):
        """
        The tenders record real money, so cash here is 15,000 while revenue is
        10,000. That difference IS the installation, and it must be explainable.
        """
        create_sale(
            cashier=owner, items=_items(product), installation_paise=500000,
            payment_method="cash", amount_tendered_paise=1500000,
        )
        s = daily_summary(timezone.localdate())
        taken = sum(v["total_paise"] for v in s["payment_breakdown"].values())
        assert taken == s["total_revenue_paise"] + s["installation"]["charged_paise"]

    def test_the_drawer_expects_the_labour_money_too(self, owner, product):
        shift = open_shift(cashier=owner, opening_float_paise=0)
        create_sale(
            cashier=owner, items=_items(product), installation_paise=500000,
            payment_method="cash", amount_tendered_paise=1500000,
        )
        # It is real cash in the till even though it is not revenue.
        assert get_shift_reconciliation(shift=shift)["expected_cash_paise"] == 1500000


# ── On the khata ────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestOnCredit:
    def test_the_customer_owes_the_labour_too(self, owner, product, customer):
        create_sale(
            cashier=owner, items=_items(product), installation_paise=500000,
            customer_id=customer.id, payment_method="credit",
        )
        customer.refresh_from_db()
        assert customer.outstanding_paise == 1500000
        assert ledger_balance(customer) == 1500000

    def test_goods_debt_and_labour_debt_are_separate_ledger_entries(
        self, owner, product, customer
    ):
        sale = create_sale(
            cashier=owner, items=_items(product), installation_paise=500000,
            customer_id=customer.id, payment_method="credit",
        )
        kinds = {
            e.kind: e.delta_paise
            for e in CreditLedgerEntry.objects.filter(sale=sale)
        }
        assert kinds == {"sale": 1000000, "installation": 500000}

    def test_money_at_the_till_clears_the_labour_first(self, owner, product, customer):
        """
        The technician did the work; he should not have to wait for the customer
        to clear the goods as well. Rs 5,000 down on a Rs 15,000 bill therefore
        settles the labour in full and leaves the goods outstanding.
        """
        sale = create_sale(
            cashier=owner, items=_items(product), installation_paise=500000,
            customer_id=customer.id, tenders=[_tender("cash", 500000)],
        )
        kinds = {
            e.kind: e.delta_paise
            for e in CreditLedgerEntry.objects.filter(sale=sale)
        }
        assert kinds == {"sale": 1000000}          # no installation entry at all
        assert sale.installation_collected_paise == 500000
        assert sale.installation_unpaid_paise == 0

    def test_a_part_payment_smaller_than_the_labour_splits_it(
        self, owner, product, customer
    ):
        sale = create_sale(
            cashier=owner, items=_items(product), installation_paise=500000,
            customer_id=customer.id, tenders=[_tender("cash", 200000)],
        )
        kinds = {
            e.kind: e.delta_paise
            for e in CreditLedgerEntry.objects.filter(sale=sale)
        }
        assert kinds == {"sale": 1000000, "installation": 300000}
        assert sale.installation_collected_paise == 200000

    def test_labour_on_credit_counts_against_the_credit_limit(
        self, owner, product, customer
    ):
        customer.credit_limit_paise = 1200000      # Rs 12,000
        customer.save(update_fields=["credit_limit_paise"])
        # Rs 10,000 goods alone would pass; with Rs 5,000 labour it must not.
        with pytest.raises(ValueError, match="Credit limit exceeded"):
            create_sale(
                cashier=owner, items=_items(product), installation_paise=500000,
                customer_id=customer.id, payment_method="credit",
            )
        assert CreditLedgerEntry.objects.count() == 0

    def test_the_outstanding_report_counts_uncollected_labour(
        self, owner, product, customer
    ):
        create_sale(
            cashier=owner, items=_items(product), installation_paise=500000,
            customer_id=customer.id, payment_method="credit",
        )
        inst = daily_summary(timezone.localdate())["installation"]
        assert inst["charged_paise"] == 500000
        assert inst["collected_paise"] == 0
        assert inst["outstanding_paise"] == 500000   # nothing to pay the technician yet


# ── Reversals ───────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestReversals:
    def test_voiding_clears_the_labour_debt_as_well(self, owner, product, customer):
        sale = create_sale(
            cashier=owner, items=_items(product), installation_paise=500000,
            customer_id=customer.id, payment_method="credit",
        )
        void_sale(sale=sale, voided_by=owner)
        customer.refresh_from_db()
        assert customer.outstanding_paise == 0
        assert ledger_balance(customer) == 0

    def test_returning_the_goods_does_not_cancel_the_labour(
        self, owner, product, customer
    ):
        """
        The camera comes back; the technician's day on a ladder does not. A full
        goods return must leave the installation debt standing.
        """
        sale = create_sale(
            cashier=owner, items=_items(product), installation_paise=500000,
            customer_id=customer.id, payment_method="credit",
        )
        create_return(
            cashier=owner, original_sale=sale,
            items=[{"product_id": product.id, "qty": "10"}],
        )
        customer.refresh_from_db()
        assert customer.outstanding_paise == 500000     # the labour, still owed
        assert ledger_balance(customer) == 500000

    def test_a_discounted_return_cannot_eat_into_the_labour_debt(
        self, owner, product, customer
    ):
        """
        A return is priced at the undiscounted unit price, so on a discounted
        bill the goods coming back are "worth" more than the goods debt. The
        ceiling has to be the goods actually charged to the khata — otherwise
        the overflow silently wipes out labour the customer still owes.

        Rs 10,000 of goods less Rs 2,000 bill discount = Rs 8,000 charged,
        plus Rs 5,000 labour = Rs 13,000 owed. Returning every unit is priced
        at Rs 10,000, which is Rs 2,000 more than the goods debt.
        """
        sale = create_sale(
            cashier=owner, items=_items(product), discount_paise=200000,
            installation_paise=500000, customer_id=customer.id,
            payment_method="credit",
        )
        customer.refresh_from_db()
        assert customer.outstanding_paise == 1300000

        create_return(
            cashier=owner, original_sale=sale,
            items=[{"product_id": product.id, "qty": "10"}],
        )
        customer.refresh_from_db()
        # Exactly the labour is left. Not Rs 3,000 — that would mean the return
        # had paid off Rs 2,000 of the technician's money.
        assert customer.outstanding_paise == 500000
        assert ledger_balance(customer) == 500000


# ── The API and the receipts ────────────────────────────────────────────────


@pytest.mark.django_db
class TestApiAndReceipts:
    def _post(self, client, product, **extra):
        payload = {
            "items": [{"product_id": product.id, "qty": "10", "unit_price_paise": 100000}],
            "payment_method": "cash",
            "amount_tendered_paise": 1500000,
        }
        payload.update(extra)
        return client.post("/api/sales/", payload, format="json")

    def test_the_api_accepts_and_reports_it(self, client_auth, product):
        resp = self._post(client_auth, product, installation_paise=500000,
                          installation_note="Imran — 3rd floor")
        assert resp.status_code == status.HTTP_201_CREATED, resp.data
        assert resp.data["total_paise"] == 1000000
        assert resp.data["installation_paise"] == 500000
        assert resp.data["amount_due_paise"] == 1500000
        assert resp.data["installation_note"] == "Imran — 3rd floor"

    def test_the_api_refuses_a_negative_charge(self, client_auth, product):
        resp = self._post(client_auth, product, installation_paise=-500)
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.fixture
    def inst_sale(self, owner, product):
        return create_sale(
            cashier=owner, items=_items(product), installation_paise=500000,
            installation_note="Imran", payment_method="cash",
            amount_tendered_paise=1500000,
        )

    def test_the_context_separates_goods_from_labour(self, inst_sale):
        from apps.config.utils import get_all_settings
        from apps.sales.receipts import build_receipt_context

        ctx = build_receipt_context(inst_sale, get_all_settings())
        assert ctx.has_installation
        assert ctx.total_paise == 1000000
        assert ctx.amount_due_paise == 1500000
        assert ctx.installation_note == "Imran"

    def test_the_text_receipt_shows_both_and_names_the_amount_due(self, inst_sale):
        from apps.sales.receipts import render_text_receipt

        text = render_text_receipt(inst_sale)
        assert "10,000.00" in text
        assert "5,000.00" in text
        assert "15,000.00" in text
        assert "AMOUNT DUE" in text

    def test_the_amount_in_words_states_what_is_payable(self, inst_sale):
        """
        On an invoice the words are the legally operative figure. Quoting the
        goods total there while the box above says Rs 15,000 would make the
        document contradict itself.
        """
        from apps.sales.receipts import render_html_receipt

        html = render_html_receipt(inst_sale, format_name="a4")
        assert "Fifteen thousand" in html
        assert "Ten thousand rupees only" not in html

    def test_the_html_receipt_shows_both(self, inst_sale):
        from apps.sales.receipts import render_html_receipt

        html = render_html_receipt(inst_sale, format_name="a4")
        assert "Installation" in html
        assert "Amount due" in html
        assert "15,000.00" in html

    def test_both_pdfs_render(self, inst_sale):
        from apps.sales.receipts import render_pdf_invoice, render_pdf_receipt

        for pdf in (render_pdf_invoice(inst_sale), render_pdf_receipt(inst_sale)):
            assert pdf[:4] == b"%PDF"
            assert len(pdf) > 1000

    def test_the_whatsapp_message_quotes_the_amount_due(self, inst_sale, owner):
        from django.test import RequestFactory

        from apps.sales.sharing import build_share_payload

        req = RequestFactory().get("/api/sales/1/share/")
        req.user = owner
        msg = build_share_payload(inst_sale, req)["message"]
        assert "15,000.00" in msg
        assert "installation" in msg.lower()
