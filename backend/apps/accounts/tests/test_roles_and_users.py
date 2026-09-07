"""
Roles, permissions and staff accounts.

Every existing catalog and sales test signs in as an owner, which is exactly
why a cashier could reprice stock and zero a khata for months without a single
red test. These tests only ever act as a cashier.
"""

from decimal import Decimal

import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import ActivityLog, User
from apps.catalog.models import Category, Inventory, Product
from apps.catalog.services import apply_stock_movement
from apps.customers.models import Customer
from apps.sales.services import create_sale


# ── Fixtures ────────────────────────────────────────────────────────────────


def _client_for(user, password="Pass1234!"):
    c = APIClient()
    r = c.post(reverse("auth-login"), {"email": user.email, "password": password})
    assert r.status_code == 200, r.data
    c.credentials(HTTP_AUTHORIZATION=f"Bearer {r.data['access']}")
    return c


@pytest.fixture
def owner(db):
    return User.objects.create_superuser(
        username="rl_owner", email="rl_owner@test.com", password="Pass1234!",
        first_name="Shop", last_name="Owner", role="owner",
    )


@pytest.fixture
def manager(db):
    return User.objects.create_user(
        username="rl_mgr", email="rl_mgr@test.com", password="Pass1234!",
        first_name="Man", last_name="Ager", role="manager",
    )


@pytest.fixture
def cashier(db):
    return User.objects.create_user(
        username="rl_cash", email="rl_cash@test.com", password="Pass1234!",
        first_name="Cash", last_name="Ier", role="cashier",
    )


@pytest.fixture
def owner_client(owner):
    return _client_for(owner)


@pytest.fixture
def cashier_client(cashier):
    return _client_for(cashier)


@pytest.fixture
def product(db):
    cat = Category.objects.create(name="Cams", slug="rl-cams")
    p = Product.objects.create(
        name="Dome", sku="RL-1", category=cat,
        sell_price_paise=100000, cost_price_paise=60000,
    )
    Inventory.objects.create(product=p)
    apply_stock_movement(product=p, movement_type="stock_in", qty_change=Decimal("100"))
    return p


# ── The holes this closes ───────────────────────────────────────────────────


@pytest.mark.django_db
class TestACashierCannotTouchTheCatalogue:
    def test_cannot_reprice_a_product(self, cashier_client, product):
        """A Rs 1,000 camera repriced to 1 paisa, sold, and the difference pocketed."""
        resp = cashier_client.patch(
            f"/api/products/{product.id}/", {"sell_price_paise": 1}, format="json"
        )
        assert resp.status_code == status.HTTP_403_FORBIDDEN
        product.refresh_from_db()
        assert product.sell_price_paise == 100000

    def test_cannot_invent_stock(self, cashier_client, product):
        resp = cashier_client.post(
            "/api/inventory/stock-in/",
            {"product": product.id, "qty": "9999"}, format="json",
        )
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_cannot_create_a_category(self, cashier_client):
        resp = cashier_client.post(
            "/api/categories/", {"name": "Junk", "slug": "junk"}, format="json"
        )
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_can_still_read_the_catalogue(self, cashier_client, product):
        """Selling requires seeing what is in stock — reads stay open."""
        assert cashier_client.get("/api/products/").status_code == status.HTTP_200_OK
        assert cashier_client.get(f"/api/products/{product.id}/").status_code == status.HTTP_200_OK

    def test_a_manager_may_still_do_all_of_it(self, manager, product):
        c = _client_for(manager)
        assert c.patch(f"/api/products/{product.id}/", {"sell_price_paise": 120000},
                       format="json").status_code == status.HTTP_200_OK
        assert c.post("/api/inventory/stock-in/", {"product": product.id, "qty": "5"},
                      format="json").status_code == status.HTTP_201_CREATED


@pytest.mark.django_db
class TestCostPricesAreNotForTheCounter:
    def test_a_cashier_never_receives_the_cost_price(self, cashier_client, product):
        """
        Knowing the cost tells a cashier exactly how far a price can be dropped
        before anyone notices. The field is removed, not merely hidden.
        """
        resp = cashier_client.get(f"/api/products/{product.id}/")
        assert resp.status_code == status.HTTP_200_OK
        assert "cost_price_paise" not in resp.data
        assert "cost_price" not in resp.data
        assert resp.data["sell_price_paise"] == 100000     # selling still works

    def test_a_cashier_cannot_pull_the_inventory_valuation(self, cashier_client):
        resp = cashier_client.get("/api/reports/inventory/")
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_an_owner_sees_both(self, owner_client, product):
        assert "cost_price_paise" in owner_client.get(f"/api/products/{product.id}/").data
        assert owner_client.get("/api/reports/inventory/").status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestTheKhataBalanceIsTheLedgersAlone:
    def test_a_cashier_cannot_zero_a_balance(self, cashier_client, db):
        cust = Customer.objects.create(
            name="Victim", phone="03001112222", outstanding_paise=500000
        )
        resp = cashier_client.patch(
            f"/api/customers/{cust.id}/", {"outstanding_paise": 0}, format="json"
        )
        cust.refresh_from_db()
        # The write is ignored rather than refused — it is simply not a field
        # anyone may set. What matters is that the money did not move.
        assert cust.outstanding_paise == 500000, "a PATCH rewrote the khata balance"
        assert resp.status_code in (status.HTTP_200_OK, status.HTTP_403_FORBIDDEN)

    def test_not_even_an_owner_can(self, owner_client, db):
        """Balances move through the ledger or not at all — role is irrelevant."""
        cust = Customer.objects.create(
            name="Victim2", phone="03001113333", outstanding_paise=500000
        )
        owner_client.patch(
            f"/api/customers/{cust.id}/", {"outstanding_paise": 0}, format="json"
        )
        cust.refresh_from_db()
        assert cust.outstanding_paise == 500000

    def test_a_cashier_can_still_edit_the_things_they_should(self, cashier_client, db):
        cust = Customer.objects.create(name="Ali", phone="03004445555")
        resp = cashier_client.patch(
            f"/api/customers/{cust.id}/", {"notes": "prefers evening delivery"},
            format="json",
        )
        assert resp.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestReturnsAreCapped:
    def _sale(self, owner, product, qty="10"):
        return create_sale(
            cashier=owner,
            items=[{"product_id": product.id, "qty": qty, "unit_price_paise": 100000}],
            payment_method="cash", amount_tendered_paise=1000000,
        )

    def test_a_cashier_cannot_return_more_than_the_ceiling(
        self, cashier_client, owner, product
    ):
        """Rs 10,000 of goods against a Rs 5,000 default ceiling."""
        sale = self._sale(owner, product)
        resp = cashier_client.post(
            f"/api/sales/{sale.id}/return/",
            {"items": [{"product_id": product.id, "qty": "10"}]}, format="json",
        )
        assert resp.status_code == status.HTTP_403_FORBIDDEN
        assert "5,000.00" in str(resp.data)

    def test_a_cashier_can_handle_an_everyday_return(
        self, cashier_client, owner, product
    ):
        sale = self._sale(owner, product)
        resp = cashier_client.post(
            f"/api/sales/{sale.id}/return/",
            {"items": [{"product_id": product.id, "qty": "2"}]}, format="json",
        )
        assert resp.status_code == status.HTTP_201_CREATED

    def test_the_ceiling_is_the_owners_to_set(self, cashier_client, owner, owner_client, product):
        owner_client.patch("/api/settings/cashier_return_limit_paise/",
                           {"value": "2000000"}, format="json")
        sale = self._sale(owner, product)
        resp = cashier_client.post(
            f"/api/sales/{sale.id}/return/",
            {"items": [{"product_id": product.id, "qty": "10"}]}, format="json",
        )
        assert resp.status_code == status.HTTP_201_CREATED

    def test_an_owner_is_never_capped(self, owner_client, owner, product):
        sale = self._sale(owner, product)
        resp = owner_client.post(
            f"/api/sales/{sale.id}/return/",
            {"items": [{"product_id": product.id, "qty": "10"}]}, format="json",
        )
        assert resp.status_code == status.HTTP_201_CREATED


# ── Staff accounts ──────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestStaffAccounts:
    def test_an_owner_can_create_a_cashier_who_can_then_sign_in(self, owner_client, db):
        resp = owner_client.post("/api/auth/users/", {
            "email": "New.Cashier@test.com", "first_name": "New", "last_name": "Hand",
            "role": "cashier", "password": "TempPass99!",
        }, format="json")
        assert resp.status_code == status.HTTP_201_CREATED, resp.data
        assert resp.data["role"] == "cashier"
        assert resp.data["must_change_password"] is True
        # The password never comes back out.
        assert "password" not in resp.data

        login = APIClient().post(reverse("auth-login"),
                                 {"email": "new.cashier@test.com", "password": "TempPass99!"})
        assert login.status_code == status.HTTP_200_OK
        assert login.data["user"]["must_change_password"] is True

    def test_a_manager_cannot_manage_staff(self, manager, db):
        """Otherwise a manager promotes himself and the roles mean nothing."""
        c = _client_for(manager)
        assert c.get("/api/auth/users/").status_code == status.HTTP_403_FORBIDDEN
        assert c.post("/api/auth/users/", {
            "email": "x@test.com", "first_name": "X", "last_name": "Y",
            "role": "owner", "password": "TempPass99!",
        }, format="json").status_code == status.HTTP_403_FORBIDDEN

    def test_a_cashier_cannot_see_the_staff_list(self, cashier_client):
        assert cashier_client.get("/api/auth/users/").status_code == status.HTTP_403_FORBIDDEN

    def test_a_duplicate_email_is_refused_readably(self, owner_client, cashier):
        resp = owner_client.post("/api/auth/users/", {
            "email": cashier.email, "first_name": "Copy", "last_name": "Cat",
            "role": "cashier", "password": "TempPass99!",
        }, format="json")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert "already uses that email" in str(resp.data)

    def test_a_weak_password_is_refused(self, owner_client):
        resp = owner_client.post("/api/auth/users/", {
            "email": "weak@test.com", "first_name": "W", "last_name": "K",
            "role": "cashier", "password": "12345678",
        }, format="json")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_deactivating_stops_the_sign_in_and_keeps_the_history(
        self, owner_client, cashier
    ):
        resp = owner_client.patch(f"/api/auth/users/{cashier.id}/",
                                  {"is_active": False}, format="json")
        assert resp.status_code == status.HTTP_200_OK
        assert User.objects.filter(pk=cashier.pk).exists()      # never deleted

        login = APIClient().post(reverse("auth-login"),
                                 {"email": cashier.email, "password": "Pass1234!"})
        assert login.status_code != status.HTTP_200_OK

    def test_an_owner_cannot_lock_themselves_out(self, owner_client, owner):
        assert owner_client.patch(f"/api/auth/users/{owner.id}/",
                                  {"is_active": False}, format="json"
                                  ).status_code == status.HTTP_400_BAD_REQUEST
        assert owner_client.patch(f"/api/auth/users/{owner.id}/",
                                  {"role": "cashier"}, format="json"
                                  ).status_code == status.HTTP_400_BAD_REQUEST

    def test_the_last_owner_cannot_be_demoted(self, owner_client, owner, manager):
        """Even by another owner — somebody has to be able to put it all back."""
        assert User.objects.filter(role="owner", is_active=True).count() == 1
        resp = owner_client.patch(f"/api/auth/users/{owner.id}/",
                                  {"role": "manager"}, format="json")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestPasswords:
    def test_an_owner_can_reset_a_forgotten_password(self, owner_client, cashier):
        resp = owner_client.post(f"/api/auth/users/{cashier.id}/set-password/",
                                 {"password": "BrandNew99!"}, format="json")
        assert resp.status_code == status.HTTP_200_OK

        login = APIClient().post(reverse("auth-login"),
                                 {"email": cashier.email, "password": "BrandNew99!"})
        assert login.status_code == status.HTTP_200_OK
        # Temporary by definition.
        assert login.data["user"]["must_change_password"] is True

    def test_a_cashier_cannot_reset_anybody_elses(self, cashier_client, owner):
        resp = cashier_client.post(f"/api/auth/users/{owner.id}/set-password/",
                                   {"password": "Hijacked99!"}, format="json")
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_anyone_can_change_their_own(self, cashier_client, cashier):
        resp = cashier_client.post("/api/auth/change-password/", {
            "current_password": "Pass1234!", "new_password": "MyOwnPass99!",
        }, format="json")
        assert resp.status_code == status.HTTP_200_OK
        cashier.refresh_from_db()
        assert cashier.must_change_password is False
        assert APIClient().post(reverse("auth-login"), {
            "email": cashier.email, "password": "MyOwnPass99!",
        }).status_code == status.HTTP_200_OK

    def test_changing_it_requires_knowing_the_old_one(self, cashier_client):
        resp = cashier_client.post("/api/auth/change-password/", {
            "current_password": "wrong", "new_password": "MyOwnPass99!",
        }, format="json")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert "not your current password" in str(resp.data)

    def test_the_same_password_again_is_refused(self, cashier_client):
        resp = cashier_client.post("/api/auth/change-password/", {
            "current_password": "Pass1234!", "new_password": "Pass1234!",
        }, format="json")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST


# ── The trail ───────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestTheAuditTrailRecordsWhatItShould:
    def test_a_failed_login_is_recorded(self, db, cashier):
        APIClient().post(reverse("auth-login"),
                         {"email": cashier.email, "password": "not-it"})
        entry = ActivityLog.objects.filter(action="login_failed").first()
        assert entry is not None, "a password-guessing run would leave no trace"
        assert entry.details["email"] == cashier.email
        # The attempted password must never be written down.
        assert "not-it" not in str(entry.details)

    def test_a_stock_adjustment_is_recorded(self, owner_client, product):
        owner_client.post("/api/inventory/stock-in/",
                          {"product": product.id, "qty": "25", "notes": "from Karachi"},
                          format="json")
        entry = ActivityLog.objects.filter(action="stock_in").first()
        assert entry is not None, "stock appearing from nowhere left no trace"
        assert entry.details["qty"] == "25.000"

    def test_a_settings_change_is_recorded(self, owner_client):
        owner_client.patch("/api/settings/tax_pct/", {"value": "17"}, format="json")
        entry = ActivityLog.objects.filter(action="setting_changed").first()
        assert entry is not None
        assert entry.details["key"] == "tax_pct"
        assert entry.details["to"] == "17"

    def test_creating_and_changing_staff_is_recorded(self, owner_client, cashier):
        owner_client.post("/api/auth/users/", {
            "email": "trail@test.com", "first_name": "T", "last_name": "R",
            "role": "cashier", "password": "TempPass99!",
        }, format="json")
        owner_client.patch(f"/api/auth/users/{cashier.id}/",
                           {"role": "manager"}, format="json")
        assert ActivityLog.objects.filter(action="user_created").exists()
        assert ActivityLog.objects.filter(action="user_updated").exists()
