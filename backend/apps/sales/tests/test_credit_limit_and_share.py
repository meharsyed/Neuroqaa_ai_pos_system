"""
Credit limits and shareable receipt links.

The credit-limit tests exist because an unbounded khata is the one remaining
way this system can lose money quietly: every other guard refuses bad input,
but a customer with no ceiling can simply keep taking goods.
"""

from decimal import Decimal

import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.catalog.models import Category, Inventory, Product
from apps.catalog.services import apply_stock_movement
from apps.config.models import Setting
from apps.customers.models import CreditLedgerEntry, Customer
from apps.customers.services import available_credit, effective_credit_limit
from apps.sales.models import Sale
from apps.sales.services import create_sale


# ── Fixtures ────────────────────────────────────────────────────────────────


@pytest.fixture
def owner(db):
    return User.objects.create_superuser(
        username="cl_owner", email="cl_owner@test.com", password="Pass1234!",
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
    cat = Category.objects.create(name="Cams", slug="cams")
    p = Product.objects.create(
        name="2MP Dome", sku="CL-DMC-1", category=cat,
        sell_price_paise=100000, cost_price_paise=60000,   # Rs 1,000
    )
    Inventory.objects.create(product=p)
    apply_stock_movement(product=p, movement_type="stock_in", qty_change=Decimal("500"))
    return p


@pytest.fixture
def customer(db):
    return Customer.objects.create(name="Ali", phone="03331122333")


def _set(key, value):
    Setting.objects.update_or_create(key=key, defaults={"value": value})


def _credit(cashier, product, customer, qty="1"):
    return create_sale(
        cashier=cashier,
        items=[{"product_id": product.id, "qty": qty,
                "unit_price_paise": product.sell_price_paise}],
        payment_method="credit", amount_tendered_paise=0, customer_id=customer.id,
    )


# ── Limit resolution ────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestLimitResolution:
    def test_no_limit_anywhere_means_unlimited(self, customer):
        _set("default_credit_limit_paise", "0")
        assert effective_credit_limit(customer) is None
        assert available_credit(customer) is None

    def test_shop_default_applies_when_customer_has_none(self, customer):
        _set("default_credit_limit_paise", "500000")
        assert effective_credit_limit(customer) == 500000
        assert available_credit(customer) == 500000

    def test_customer_limit_beats_the_shop_default(self, customer):
        _set("default_credit_limit_paise", "500000")
        customer.credit_limit_paise = 200000
        customer.save()
        assert effective_credit_limit(customer) == 200000

    def test_customer_zero_means_no_credit_at_all(self, customer):
        """An explicit 0 on the customer must not fall through to the default."""
        _set("default_credit_limit_paise", "500000")
        customer.credit_limit_paise = 0
        customer.save()
        assert effective_credit_limit(customer) == 0
        assert available_credit(customer) == 0

    def test_available_credit_shrinks_as_debt_grows(self, owner, product, customer):
        _set("default_credit_limit_paise", "0")
        customer.credit_limit_paise = 500000
        customer.save()
        _credit(owner, product, customer, qty="2")   # Rs 2,000
        customer.refresh_from_db()
        assert available_credit(customer) == 500000 - customer.outstanding_paise


# ── Enforcement ─────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestLimitEnforcement:
    def test_a_sale_over_the_limit_is_refused(self, owner, product, customer):
        _set("default_credit_limit_paise", "0")
        customer.credit_limit_paise = 150000        # Rs 1,500
        customer.save()
        with pytest.raises(ValueError, match="Credit limit exceeded"):
            _credit(owner, product, customer, qty="2")   # Rs 2,000

    def test_a_sale_exactly_at_the_limit_is_allowed(self, owner, product, customer):
        _set("default_credit_limit_paise", "0")
        customer.credit_limit_paise = 200000
        customer.save()
        sale = _credit(owner, product, customer, qty="2")
        customer.refresh_from_db()
        assert customer.outstanding_paise == sale.total_paise == 200000

    def test_the_limit_counts_existing_debt(self, owner, product, customer):
        _set("default_credit_limit_paise", "0")
        customer.credit_limit_paise = 250000
        customer.save()
        _credit(owner, product, customer, qty="2")       # owes 2,000, 500 left
        with pytest.raises(ValueError, match="Credit limit exceeded"):
            _credit(owner, product, customer, qty="1")   # needs 1,000

    def test_a_refused_sale_leaves_nothing_behind(self, owner, product, customer):
        _set("default_credit_limit_paise", "100000")
        stock_before = Inventory.objects.get(product=product).stock_qty
        sales_before = Sale.objects.count()
        ledger_before = CreditLedgerEntry.objects.count()

        with pytest.raises(ValueError):
            _credit(owner, product, customer, qty="5")

        assert Inventory.objects.get(product=product).stock_qty == stock_before
        assert Sale.objects.count() == sales_before
        assert CreditLedgerEntry.objects.count() == ledger_before
        customer.refresh_from_db()
        assert customer.outstanding_paise == 0

    def test_cash_sales_ignore_the_limit(self, owner, product, customer):
        _set("default_credit_limit_paise", "100")   # Rs 1
        sale = create_sale(
            cashier=owner,
            items=[{"product_id": product.id, "qty": "5",
                    "unit_price_paise": product.sell_price_paise}],
            payment_method="cash", amount_tendered_paise=1000000,
            customer_id=customer.id,
        )
        assert sale.status == "completed"

    def test_the_api_returns_400_with_a_readable_reason(
        self, client_auth, product, customer
    ):
        _set("default_credit_limit_paise", "0")
        customer.credit_limit_paise = 100000
        customer.save()
        resp = client_auth.post("/api/sales/", {
            "items": [{"product_id": product.id, "qty": "5",
                       "unit_price_paise": product.sell_price_paise}],
            "payment_method": "credit", "amount_tendered_paise": 0,
            "customer_id": customer.id,
        }, format="json")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert "credit limit" in str(resp.data).lower()

    def test_the_serializer_exposes_available_credit(self, client_auth, customer):
        _set("default_credit_limit_paise", "0")
        customer.credit_limit_paise = 300000
        customer.save()
        resp = client_auth.get(f"/api/customers/{customer.id}/")
        assert resp.data["effective_credit_limit_paise"] == 300000
        assert resp.data["available_credit_paise"] == 300000


# ── Shareable receipt links ─────────────────────────────────────────────────


@pytest.mark.django_db
class TestReceiptSharing:
    @pytest.fixture(autouse=True)
    def _enable(self):
        _set("receipt_share_enabled", "true")
        _set("receipt_link_days", "30")
        _set("public_base_url", "")
        _set("default_credit_limit_paise", "0")

    def _sale(self, owner, product, customer):
        return create_sale(
            cashier=owner,
            items=[{"product_id": product.id, "qty": "2",
                    "unit_price_paise": product.sell_price_paise}],
            payment_method="cash", amount_tendered_paise=500000,
            customer_id=customer.id,
        )

    def test_share_endpoint_returns_a_link_and_a_message(
        self, client_auth, owner, product, customer
    ):
        sale = self._sale(owner, product, customer)
        resp = client_auth.get(f"/api/sales/{sale.pk}/share/")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["enabled"] is True
        assert "/r/" in resp.data["public_url"]
        assert sale.sale_number in resp.data["message"]
        # local phone normalised to international form for wa.me
        assert resp.data["customer_phone"] == "923331122333"
        assert resp.data["whatsapp_url"].startswith("https://wa.me/923331122333?text=")

    def test_a_customerless_sale_still_shares(self, client_auth, owner, product):
        sale = create_sale(
            cashier=owner,
            items=[{"product_id": product.id, "qty": "1",
                    "unit_price_paise": product.sell_price_paise}],
            payment_method="cash", amount_tendered_paise=500000,
        )
        resp = client_auth.get(f"/api/sales/{sale.pk}/share/")
        assert resp.data["customer_phone"] is None
        assert resp.data["whatsapp_url"].startswith("https://wa.me/?text=")

    def test_the_public_link_renders_the_bill_without_a_login(
        self, client_auth, owner, product, customer
    ):
        sale = self._sale(owner, product, customer)
        url = client_auth.get(f"/api/sales/{sale.pk}/share/").data["public_url"]
        path = url[url.index("/r/"):]

        anon = APIClient()          # deliberately unauthenticated
        resp = anon.get(path)
        assert resp.status_code == status.HTTP_200_OK
        assert sale.sale_number in resp.content.decode()
        assert resp["X-Robots-Tag"].startswith("noindex")

    def test_a_tampered_token_is_refused(self, client_auth):
        anon = APIClient()
        assert anon.get("/r/not-a-real-token/").status_code == 410

    def test_an_expired_link_is_refused(self, client_auth, owner, product, customer, monkeypatch):
        sale = self._sale(owner, product, customer)
        url = client_auth.get(f"/api/sales/{sale.pk}/share/").data["public_url"]
        path = url[url.index("/r/"):]

        from apps.sales import sharing

        monkeypatch.setattr(sharing, "link_max_age_seconds", lambda: 0)
        assert APIClient().get(path).status_code == 410

    def test_turning_sharing_off_kills_existing_links(
        self, client_auth, owner, product, customer
    ):
        sale = self._sale(owner, product, customer)
        url = client_auth.get(f"/api/sales/{sale.pk}/share/").data["public_url"]
        path = url[url.index("/r/"):]

        _set("receipt_share_enabled", "false")
        assert APIClient().get(path).status_code == 410

        resp = client_auth.get(f"/api/sales/{sale.pk}/share/")
        assert resp.data["enabled"] is False
        assert resp.data["public_url"] == ""

    def test_a_configured_public_base_url_wins(self, client_auth, owner, product, customer):
        _set("public_base_url", "https://bills.example.com/")
        sale = self._sale(owner, product, customer)
        resp = client_auth.get(f"/api/sales/{sale.pk}/share/")
        assert resp.data["public_url"].startswith("https://bills.example.com/r/")

    def test_credit_sale_message_mentions_the_balance(
        self, client_auth, owner, product, customer
    ):
        sale = _credit(owner, product, customer, qty="2")
        resp = client_auth.get(f"/api/sales/{sale.pk}/share/")
        assert "Outstanding balance" in resp.data["message"]

    def test_html_receipt_endpoint_works(self, client_auth, owner, product, customer):
        sale = self._sale(owner, product, customer)
        resp = client_auth.get(f"/api/sales/{sale.pk}/receipt/html/")
        assert resp.status_code == status.HTTP_200_OK
        assert resp["Content-Type"].startswith("text/html")
        assert sale.sale_number in resp.content.decode()


@pytest.mark.django_db
@pytest.mark.parametrize("raw,expected", [
    ("03331122333", "923331122333"),
    ("0333 112 2333", "923331122333"),
    ("+92 333 1122333", "923331122333"),
    ("923331122333", "923331122333"),
    ("00923331122333", "923331122333"),
    ("3331122333", "923331122333"),
    ("123", None),
    (None, None),
    ("", None),
])
def test_phone_normalisation(raw, expected):
    from apps.sales.sharing import normalise_pk_phone

    assert normalise_pk_phone(raw) == expected


# ── Who may change a limit ──────────────────────────────────────────────────


@pytest.mark.django_db
class TestLimitIsRoleGated:
    def _cashier_client(self, db):
        u = User.objects.create_user(
            username="cl_cash", email="cl_cash@test.com",
            password="Pass1234!", role="cashier",
        )
        c = APIClient()
        r = c.post(reverse("auth-login"), {"email": u.email, "password": "Pass1234!"})
        c.credentials(HTTP_AUTHORIZATION=f"Bearer {r.data['access']}")
        return c

    def test_an_owner_can_set_a_limit(self, client_auth, customer):
        resp = client_auth.patch(
            f"/api/customers/{customer.id}/", {"credit_limit_paise": 250000}, format="json"
        )
        assert resp.status_code == status.HTTP_200_OK
        customer.refresh_from_db()
        assert customer.credit_limit_paise == 250000

    def test_a_cashier_cannot_raise_a_limit(self, db, customer):
        cashier = self._cashier_client(db)
        resp = cashier.patch(
            f"/api/customers/{customer.id}/", {"credit_limit_paise": 9999999}, format="json"
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert "owner or manager" in str(resp.data).lower()
        customer.refresh_from_db()
        assert customer.credit_limit_paise is None

    def test_a_cashier_can_still_edit_other_fields(self, db, customer):
        cashier = self._cashier_client(db)
        resp = cashier.patch(
            f"/api/customers/{customer.id}/", {"notes": "prefers evening delivery"},
            format="json",
        )
        assert resp.status_code == status.HTTP_200_OK

    def test_a_negative_limit_is_refused(self, client_auth, customer):
        resp = client_auth.patch(
            f"/api/customers/{customer.id}/", {"credit_limit_paise": -100}, format="json"
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_clearing_the_limit_falls_back_to_the_shop_default(self, client_auth, customer):
        _set("default_credit_limit_paise", "400000")
        client_auth.patch(
            f"/api/customers/{customer.id}/", {"credit_limit_paise": 100000}, format="json"
        )
        client_auth.patch(
            f"/api/customers/{customer.id}/", {"credit_limit_paise": None}, format="json"
        )
        customer.refresh_from_db()
        assert customer.credit_limit_paise is None
        assert effective_credit_limit(customer) == 400000
