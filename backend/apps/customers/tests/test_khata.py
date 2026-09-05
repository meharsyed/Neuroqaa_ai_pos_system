"""
Khata (customer credit) ledger tests.

The invariant under test throughout is:

    sum(CreditLedgerEntry.delta_paise) == Customer.outstanding_paise

If that holds, a wrong balance can always be explained and repaired. Before the
ledger existed it could not, and voiding a credit sale left the customer owing
the full amount forever.
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
from apps.customers.services import ledger_balance, post_credit_entry
from apps.sales.services import create_return, create_sale, void_sale


# ── Fixtures ────────────────────────────────────────────────────────────────


@pytest.fixture
def owner(db):
    return User.objects.create_superuser(
        username="k_owner", email="k_owner@test.com", password="Pass1234!",
        first_name="Shop", last_name="Owner", role="owner",
    )


@pytest.fixture
def cashier(db):
    return User.objects.create_user(
        username="k_cashier", email="k_cashier@test.com",
        password="Pass1234!", role="cashier",
    )


def _client(user):
    c = APIClient()
    r = c.post(reverse("auth-login"), {"email": user.email, "password": "Pass1234!"})
    c.credentials(HTTP_AUTHORIZATION=f"Bearer {r.data['access']}")
    return c


@pytest.fixture
def owner_client(owner):
    return _client(owner)


@pytest.fixture
def cashier_client(cashier):
    return _client(cashier)


@pytest.fixture
def product(db):
    cat = Category.objects.create(name="NVR", slug="nvr")
    p = Product.objects.create(
        name="4CH NVR (500GB)", sku="NVR-4CH-500", category=cat,
        sell_price_paise=2200000, cost_price_paise=1500000,
    )
    Inventory.objects.create(product=p)
    apply_stock_movement(product=p, movement_type="stock_in", qty_change=Decimal("100"))
    return p


@pytest.fixture
def customer(db):
    return Customer.objects.create(name="Khalid Shah", phone="03191962423")


def _credit_sale(cashier, product, customer, qty="2"):
    return create_sale(
        cashier=cashier,
        items=[{"product_id": product.id, "qty": qty,
                "unit_price_paise": product.sell_price_paise}],
        payment_method="credit", amount_tendered_paise=0, customer_id=customer.id,
    )


def _assert_reconciled(customer):
    customer.refresh_from_db()
    assert ledger_balance(customer) == customer.outstanding_paise, (
        "ledger and stored balance disagree"
    )


# ── The ledger itself ───────────────────────────────────────────────────────


@pytest.mark.django_db
class TestLedger:
    def test_credit_sale_posts_an_entry(self, cashier, product, customer):
        sale = _credit_sale(cashier, product, customer)
        entry = CreditLedgerEntry.objects.get(sale=sale, kind="sale")
        assert entry.delta_paise == sale.total_paise
        assert entry.balance_after_paise == sale.total_paise
        _assert_reconciled(customer)

    def test_entries_are_append_only(self, cashier, product, customer):
        _credit_sale(cashier, product, customer)
        entry = CreditLedgerEntry.objects.first()
        with pytest.raises(ValueError):
            entry.save()
        with pytest.raises(ValueError):
            entry.delete()

    def test_balance_after_tracks_a_running_total(self, cashier, product, customer):
        _credit_sale(cashier, product, customer, qty="1")
        _credit_sale(cashier, product, customer, qty="1")
        entries = list(CreditLedgerEntry.objects.order_by("created_at", "id"))
        running = 0
        for e in entries:
            running += e.delta_paise
            assert e.balance_after_paise == running
        _assert_reconciled(customer)

    def test_a_zero_entry_is_refused(self, customer):
        with pytest.raises(ValueError):
            post_credit_entry(customer=customer, kind="adjustment", delta_paise=0)


# ── Void must give the money back ───────────────────────────────────────────


@pytest.mark.django_db
class TestVoidReversesBalance:
    def test_voiding_a_credit_sale_clears_the_balance(self, owner, cashier, product, customer):
        sale = _credit_sale(cashier, product, customer)
        customer.refresh_from_db()
        assert customer.outstanding_paise == sale.total_paise

        void_sale(sale=sale, voided_by=owner)

        customer.refresh_from_db()
        assert customer.outstanding_paise == 0, "voided credit sale still owed"
        assert CreditLedgerEntry.objects.filter(sale=sale, kind="void").exists()
        _assert_reconciled(customer)

    def test_voiding_a_cash_sale_leaves_the_balance_alone(self, owner, cashier, product, customer):
        _credit_sale(cashier, product, customer)
        customer.refresh_from_db()
        before = customer.outstanding_paise

        cash = create_sale(
            cashier=cashier,
            items=[{"product_id": product.id, "qty": "1",
                    "unit_price_paise": product.sell_price_paise}],
            payment_method="cash", amount_tendered_paise=5000000,
            customer_id=customer.id,
        )
        void_sale(sale=cash, voided_by=owner)

        customer.refresh_from_db()
        assert customer.outstanding_paise == before
        _assert_reconciled(customer)


# ── Returns must reduce what is owed ────────────────────────────────────────


@pytest.mark.django_db
class TestReturnReducesBalance:
    def test_partial_return_reduces_the_balance(self, cashier, product, customer):
        sale = _credit_sale(cashier, product, customer, qty="2")
        customer.refresh_from_db()
        full = customer.outstanding_paise

        create_return(cashier=cashier, original_sale=sale,
                      items=[{"product_id": product.id, "qty": "1"}])

        customer.refresh_from_db()
        assert customer.outstanding_paise == full - product.sell_price_paise
        assert CreditLedgerEntry.objects.filter(sale=sale, kind="return").exists()
        _assert_reconciled(customer)

    def test_void_after_a_partial_return_does_not_double_refund(
        self, owner, cashier, product, customer
    ):
        sale = _credit_sale(cashier, product, customer, qty="2")
        create_return(cashier=cashier, original_sale=sale,
                      items=[{"product_id": product.id, "qty": "1"}])
        void_sale(sale=sale, voided_by=owner)

        customer.refresh_from_db()
        assert customer.outstanding_paise == 0, "balance went negative — refunded twice"
        _assert_reconciled(customer)

    def test_returning_a_cash_sale_leaves_the_balance_alone(self, cashier, product, customer):
        _credit_sale(cashier, product, customer, qty="1")
        customer.refresh_from_db()
        before = customer.outstanding_paise

        cash = create_sale(
            cashier=cashier,
            items=[{"product_id": product.id, "qty": "2",
                    "unit_price_paise": product.sell_price_paise}],
            payment_method="cash", amount_tendered_paise=9000000,
            customer_id=customer.id,
        )
        create_return(cashier=cashier, original_sale=cash,
                      items=[{"product_id": product.id, "qty": "1"}])

        customer.refresh_from_db()
        assert customer.outstanding_paise == before
        _assert_reconciled(customer)


# ── Payments ────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestPayments:
    def test_payment_reduces_the_balance_and_posts_an_entry(
        self, owner, owner_client, cashier, product, customer
    ):
        sale = _credit_sale(cashier, product, customer)
        resp = owner_client.post("/api/customers/record-payment/", {
            "customer_id": customer.id, "amount_paise": 100000,
        }, format="json")
        assert resp.status_code == status.HTTP_201_CREATED

        customer.refresh_from_db()
        assert customer.outstanding_paise == sale.total_paise - 100000
        assert CreditLedgerEntry.objects.filter(kind="payment").exists()
        _assert_reconciled(customer)

    def test_overpayment_is_refused(self, owner_client, cashier, product, customer):
        sale = _credit_sale(cashier, product, customer)
        resp = owner_client.post("/api/customers/record-payment/", {
            "customer_id": customer.id, "amount_paise": sale.total_paise + 1,
        }, format="json")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        customer.refresh_from_db()
        assert customer.outstanding_paise == sale.total_paise
        _assert_reconciled(customer)

    def test_payment_against_a_clear_account_is_refused(self, owner_client, customer):
        resp = owner_client.post("/api/customers/record-payment/", {
            "customer_id": customer.id, "amount_paise": 100,
        }, format="json")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_a_cashier_cannot_write_off_credit(
        self, cashier_client, cashier, product, customer
    ):
        _credit_sale(cashier, product, customer)
        resp = cashier_client.post("/api/customers/record-payment/", {
            "customer_id": customer.id, "amount_paise": 100000,
        }, format="json")
        assert resp.status_code == status.HTTP_403_FORBIDDEN


# ── Serial numbers are globally unique ──────────────────────────────────────


@pytest.mark.django_db
class TestGlobalSerialUniqueness:
    def _payload(self, product, serial):
        return {
            "items": [{
                "product_id": product.id, "qty": "1",
                "unit_price_paise": product.sell_price_paise,
                "serials": [{"serial": serial, "warranty_months": 12}],
            }],
            "payment_method": "cash",
            "amount_tendered_paise": 5000000,
        }

    def test_the_same_serial_cannot_be_sold_twice(self, owner_client, product):
        first = owner_client.post("/api/sales/", self._payload(product, "SN-UNIQ-1"),
                                  format="json")
        assert first.status_code == status.HTTP_201_CREATED

        second = owner_client.post("/api/sales/", self._payload(product, "SN-UNIQ-1"),
                                   format="json")
        assert second.status_code == status.HTTP_400_BAD_REQUEST, (
            "the same physical unit was sold on two invoices"
        )
        assert "serial" in str(second.data).lower()

    def test_different_serials_are_fine(self, owner_client, product):
        assert owner_client.post("/api/sales/", self._payload(product, "SN-UNIQ-A"),
                                 format="json").status_code == status.HTTP_201_CREATED
        assert owner_client.post("/api/sales/", self._payload(product, "SN-UNIQ-B"),
                                 format="json").status_code == status.HTTP_201_CREATED


# ── Detail endpoint and statement ───────────────────────────────────────────


@pytest.mark.django_db
class TestKhataDetail:
    def test_detail_returns_ledger_sales_and_payments(
        self, owner_client, cashier, product, customer
    ):
        sale = _credit_sale(cashier, product, customer)
        owner_client.post("/api/customers/record-payment/", {
            "customer_id": customer.id, "amount_paise": 50000,
        }, format="json")

        resp = owner_client.get(f"/api/customers/{customer.id}/khata/")
        assert resp.status_code == status.HTTP_200_OK
        body = resp.data

        assert body["summary"]["is_reconciled"] is True
        assert body["summary"]["total_charged_paise"] == sale.total_paise
        assert body["summary"]["total_paid_paise"] == 50000
        assert len(body["ledger"]) == 2
        assert body["credit_sales"][0]["sale_number"] == sale.sale_number
        assert len(body["payments"]) == 1

    def test_statement_pdf_renders(self, owner_client, cashier, product, customer):
        _credit_sale(cashier, product, customer)
        resp = owner_client.get(f"/api/customers/{customer.id}/khata/statement/")
        assert resp.status_code == status.HTTP_200_OK
        assert resp["Content-Type"] == "application/pdf"
        assert resp.content[:4] == b"%PDF"

    def test_statement_renders_for_a_customer_with_no_credit(self, owner_client, customer):
        resp = owner_client.get(f"/api/customers/{customer.id}/khata/statement/")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.content[:4] == b"%PDF"

    def test_report_carries_collection_insights(self, owner_client, cashier, product, customer):
        _credit_sale(cashier, product, customer)
        resp = owner_client.get("/api/customers/khata-report/")
        assert resp.status_code == status.HTTP_200_OK
        for key in ("collected_30d_paise", "charged_30d_paise", "net_30d_paise",
                    "largest_balance_paise", "oldest_credit_days", "customer_count"):
            assert key in resp.data


# ── The reconciliation command ──────────────────────────────────────────────


@pytest.mark.django_db
class TestCheckKhataCommand:
    """
    Drift can only be verified by deliberately corrupting a balance, so this is
    exercised against an isolated test database — never live data.
    """

    def _run(self, **kwargs):
        from io import StringIO
        from django.core.management import call_command

        out = StringIO()
        call_command("check_khata", stdout=out, **kwargs)
        return out.getvalue()

    def test_reports_ok_when_everything_reconciles(self, cashier, product, customer):
        _credit_sale(cashier, product, customer)
        assert "OK" in self._run()

    def test_detects_a_drifted_balance(self, cashier, product, customer):
        _credit_sale(cashier, product, customer)
        # Bypass the service on purpose — this is the corruption we must catch.
        Customer.objects.filter(pk=customer.pk).update(
            outstanding_paise=customer.outstanding_paise + 12345
        )
        output = self._run()
        assert "out of balance" in output
        assert "123.45" in output          # the gap, in rupees
        assert "Nothing has been changed" in output

    def test_repair_realigns_and_leaves_an_audit_trail(self, cashier, product, customer):
        sale = _credit_sale(cashier, product, customer)
        Customer.objects.filter(pk=customer.pk).update(
            outstanding_paise=sale.total_paise + 12345
        )

        assert "Repaired 1" in self._run(repair=True)

        customer.refresh_from_db()
        assert customer.outstanding_paise == sale.total_paise + 12345
        _assert_reconciled(customer)
        adj = CreditLedgerEntry.objects.filter(kind="adjustment").first()
        assert adj is not None, "repair must explain itself with an adjustment entry"
        assert adj.delta_paise == 12345
