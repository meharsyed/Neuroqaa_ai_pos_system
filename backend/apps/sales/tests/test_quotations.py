"""
Quotations.

The tests that matter here are the negative ones. A quotation is a document,
not a transaction: it must not move stock, must not appear in revenue, and
must never be mistakable for a tax invoice. Those are the things a future
refactor is most likely to break.
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
from apps.customers.models import Customer
from apps.sales.models import Sale
from apps.sales.quotations import BusinessProfile, Quotation
from apps.sales.quotation_services import (
    create_quotation,
    mark_converted,
    quotation_to_cart,
    revise_quotation,
)
from apps.sales.reports import daily_summary
from apps.sales.services import create_sale


def _client_for(user):
    c = APIClient()
    r = c.post(reverse("auth-login"), {"email": user.email, "password": "Pass1234!"})
    c.credentials(HTTP_AUTHORIZATION=f"Bearer {r.data['access']}")
    return c


@pytest.fixture
def owner(db):
    return User.objects.create_superuser(
        username="qt_owner", email="qt_owner@test.com", password="Pass1234!",
        first_name="Shop", last_name="Owner", role="owner",
    )


@pytest.fixture
def cashier(db):
    return User.objects.create_user(
        username="qt_cash", email="qt_cash@test.com", password="Pass1234!", role="cashier",
    )


@pytest.fixture
def owner_client(owner):
    return _client_for(owner)


@pytest.fixture
def product(db):
    cat = Category.objects.create(name="Cams", slug="qt-cams")
    p = Product.objects.create(
        name="Dome 4MP", sku="QT-DOM", category=cat, unit="pcs",
        sell_price_paise=100000, cost_price_paise=60000,
    )
    Inventory.objects.create(product=p)
    apply_stock_movement(product=p, movement_type="stock_in", qty_change=Decimal("100"))
    return p


@pytest.fixture
def profile(db):
    return BusinessProfile.objects.create(
        name="Speed Tech Solutions", address="Agha Siraj Complex, Quetta",
        phone="+92 321 8131109", tax_number="1234567-8", is_default=True,
    )


def _lines(product):
    return [
        {"product_id": product.id, "qty": "4"},
        # The line the whole feature exists for: work the shop does not stock.
        {"name": "Cat-6 cable, 90m — supplied and laid", "qty": "1",
         "unit_price_paise": 1800000},
    ]


# ── A quotation is not a transaction ────────────────────────────────────────


@pytest.mark.django_db
class TestAQuotationChangesNothing:
    def test_it_does_not_move_stock(self, owner, product):
        product.inventory.refresh_from_db()      # the fixture stocked it
        before = product.inventory.stock_qty
        assert before == Decimal("100.000")
        create_quotation(created_by=owner, items=_lines(product))
        product.inventory.refresh_from_db()
        assert product.inventory.stock_qty == before

    def test_it_does_not_appear_in_revenue(self, owner, product):
        create_quotation(created_by=owner, items=_lines(product))
        summary = daily_summary(timezone.localdate())
        assert summary["total_revenue_paise"] == 0
        assert summary["transaction_count"] == 0

    def test_it_creates_no_sale(self, owner, product):
        create_quotation(created_by=owner, items=_lines(product))
        assert Sale.objects.count() == 0

    def test_it_never_takes_a_sale_number(self, owner, product):
        q = create_quotation(created_by=owner, items=_lines(product))
        assert q.number.startswith("QT-")
        assert "SALE-" not in q.number

    def test_it_touches_no_customer_balance(self, owner, product, db):
        customer = Customer.objects.create(name="Corp Ltd", phone="03001234567")
        create_quotation(created_by=owner, items=_lines(product), customer_id=customer.id)
        customer.refresh_from_db()
        assert customer.outstanding_paise == 0


# ── The arithmetic ──────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestTheNumbers:
    def test_off_catalogue_lines_are_priced_by_hand_and_counted(self, owner, product):
        q = create_quotation(created_by=owner, items=_lines(product))
        assert q.items.count() == 2
        assert q.subtotal_paise == 4 * 100000 + 1800000     # Rs 22,000
        assert q.total_paise == q.subtotal_paise

        off = q.items.get(product__isnull=True)
        assert off.is_off_catalogue
        assert off.line_total_paise == 1800000

    def test_a_catalogue_line_takes_the_shelf_price_when_none_is_given(self, owner, product):
        q = create_quotation(created_by=owner, items=[{"product_id": product.id, "qty": "2"}])
        assert q.items.get().unit_price_paise == 100000

    def test_a_catalogue_line_can_be_quoted_at_a_different_price(self, owner, product):
        q = create_quotation(
            created_by=owner,
            items=[{"product_id": product.id, "qty": "2", "unit_price_paise": 85000}],
        )
        assert q.total_paise == 170000

    def test_discount_tax_and_installation_stack_in_the_right_order(self, owner, product):
        q = create_quotation(
            created_by=owner,
            items=[{"product_id": product.id, "qty": "10", "unit_price_paise": 100000}],
            discount_paise=100000, tax_pct="10", installation_paise=500000,
        )
        # 10,000 − 1,000 = 9,000 taxable; +900 tax; +5,000 labour untaxed.
        assert q.subtotal_paise == 1000000
        assert q.tax_paise == 90000
        assert q.total_paise == 1490000

    def test_the_document_keeps_its_own_wording_when_the_product_changes(
        self, owner, product
    ):
        """
        A quotation is a document. It has to keep saying what it said on the
        day it went out, even if the product is renamed or repriced after.
        """
        q = create_quotation(created_by=owner, items=[{"product_id": product.id, "qty": "1"}])
        product.name = "Dome 4MP (2027 model)"
        product.sell_price_paise = 250000
        product.save()

        item = q.items.get()
        assert item.name == "Dome 4MP"
        assert item.unit_price_paise == 100000
        q.refresh_from_db()
        assert q.total_paise == 100000


@pytest.mark.django_db
class TestWhatIsRefused:
    def test_a_quotation_with_no_lines(self, owner):
        with pytest.raises(ValueError, match="at least one line"):
            create_quotation(created_by=owner, items=[])

    def test_a_line_with_neither_product_nor_description(self, owner):
        with pytest.raises(ValueError, match="needs a description"):
            create_quotation(created_by=owner, items=[{"qty": "1", "unit_price_paise": 100}])

    def test_a_zero_quantity(self, owner, product):
        with pytest.raises(ValueError, match="more than zero"):
            create_quotation(created_by=owner, items=[{"product_id": product.id, "qty": "0"}])

    def test_a_line_discount_bigger_than_the_line(self, owner, product):
        with pytest.raises(ValueError, match="more than the line"):
            create_quotation(
                created_by=owner,
                items=[{"product_id": product.id, "qty": "1",
                        "unit_price_paise": 100000, "discount_paise": 200000}],
            )

    def test_a_product_that_does_not_exist(self, owner):
        with pytest.raises(ValueError, match="does not exist"):
            create_quotation(created_by=owner, items=[{"product_id": 999999, "qty": "1"}])


# ── Revisions ───────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestRevisions:
    def test_a_revision_keeps_the_number_and_bumps_the_revision(self, owner, product):
        """
        A negotiation is one document that moves, not a pile of near-identical
        ones — the number the customer was given first still finds it.
        """
        q = create_quotation(created_by=owner, items=_lines(product))
        original = q.number

        revise_quotation(
            quotation=q, created_by=owner,
            items=[{"product_id": product.id, "qty": "6"}],
        )
        q.refresh_from_db()
        assert q.number == original
        assert q.revision == 2
        assert q.display_number.endswith("rev 2")
        assert q.items.count() == 1
        assert q.total_paise == 600000

    def test_revising_only_the_lines_leaves_everything_else_alone(
        self, owner_client, product
    ):
        """
        The revise endpoint takes a partial payload. If DRF applied the
        serializer's declared defaults to the fields the UI did not send, a
        cashier changing one quantity would silently wipe the tax rate, the
        installation charge and the validity period off the quotation.
        """
        created = owner_client.post("/api/quotations/", {
            "items": [{"product_id": product.id, "qty": "2"}],
            "customer_name": "Balochistan Textiles Ltd",
            "tax_pct": "17", "discount_paise": 30000,
            "installation_paise": 250000, "installation_note": "Two technicians",
            "valid_days": 45, "notes": "Half up front.",
        }, format="json")
        qid = created.data["id"]

        revised = owner_client.post(f"/api/quotations/{qid}/revise/", {
            "items": [{"product_id": product.id, "qty": "5"}],
        }, format="json")

        assert revised.status_code == status.HTTP_200_OK, revised.data
        assert revised.data["revision"] == 2
        assert revised.data["subtotal_paise"] == 500000        # the change asked for
        # …and nothing else moved.
        assert revised.data["customer_name"] == "Balochistan Textiles Ltd"
        assert revised.data["tax_pct"] == "17.00"
        assert revised.data["discount_paise"] == 30000
        assert revised.data["installation_paise"] == 250000
        assert revised.data["installation_note"] == "Two technicians"
        assert revised.data["valid_days"] == 45
        assert revised.data["notes"] == "Half up front."

    def test_a_converted_quotation_cannot_be_revised(self, owner, product):
        q = create_quotation(created_by=owner, items=_lines(product))
        sale = create_sale(
            cashier=owner,
            items=[{"product_id": product.id, "qty": "1", "unit_price_paise": 100000}],
            payment_method="cash", amount_tendered_paise=100000,
        )
        mark_converted(quotation=q, sale=sale)
        with pytest.raises(ValueError, match="already become a sale"):
            revise_quotation(quotation=q, created_by=owner, notes="too late")


@pytest.mark.django_db
class TestValidity:
    def test_a_quotation_states_when_it_stops_being_good(self, owner, product):
        q = create_quotation(created_by=owner, items=_lines(product), valid_days=15)
        assert q.valid_until == (timezone.localdate() + timezone.timedelta(days=15))
        assert q.is_expired is False


# ── Turning it into a sale ──────────────────────────────────────────────────


@pytest.mark.django_db
class TestConvertingToASale:
    def test_the_cart_payload_separates_what_the_till_can_actually_sell(
        self, owner, product
    ):
        """
        Off-catalogue lines cannot deduct stock — there is nothing to deduct —
        so they come back separately for the cashier rather than being
        silently dropped from the sale.
        """
        q = create_quotation(created_by=owner, items=_lines(product))
        cart = quotation_to_cart(q)

        assert len(cart["items"]) == 1
        assert cart["items"][0]["product_id"] == product.id
        assert len(cart["off_catalogue_items"]) == 1
        assert "Cat-6" in cart["off_catalogue_items"][0]["name"]

    def test_an_archived_product_falls_out_of_the_sellable_list(self, owner, product):
        q = create_quotation(created_by=owner, items=[{"product_id": product.id, "qty": "2"}])
        product.is_active = False
        product.save(update_fields=["is_active"])

        cart = quotation_to_cart(q)
        assert cart["items"] == []
        assert len(cart["off_catalogue_items"]) == 1

    def test_the_terms_carry_across(self, owner, product):
        q = create_quotation(
            created_by=owner, items=_lines(product),
            discount_paise=50000, tax_pct="17",
            installation_paise=300000, installation_note="Two technicians, one day",
        )
        cart = quotation_to_cart(q)
        assert cart["discount_paise"] == 50000
        assert cart["tax_pct"] == "17.00"
        assert cart["installation_paise"] == 300000
        assert cart["installation_note"] == "Two technicians, one day"

    def test_converting_links_the_two_and_marks_it_accepted(self, owner, product):
        q = create_quotation(created_by=owner, items=_lines(product))
        sale = create_sale(
            cashier=owner,
            items=[{"product_id": product.id, "qty": "4", "unit_price_paise": 100000}],
            payment_method="cash", amount_tendered_paise=400000,
        )
        mark_converted(quotation=q, sale=sale, user=owner)
        q.refresh_from_db()
        assert q.converted_sale_id == sale.pk
        assert q.status == "accepted"
        assert q.converted_at is not None


# ── The printed document ────────────────────────────────────────────────────


@pytest.mark.django_db
class TestThePrintedQuotation:
    def test_it_renders(self, owner, product, profile):
        from apps.sales.receipts.quotation_pdf import render_quotation_pdf

        q = create_quotation(
            created_by=owner, items=_lines(product), profile_id=profile.id,
            customer_name="Balochistan Textiles Ltd",
            customer_address="Industrial Estate, Quetta",
            discount_paise=50000, tax_pct="17", installation_paise=400000,
            installation_note="Two technicians, one day",
            notes="Delivery within 5 working days of order.",
        )
        pdf = render_quotation_pdf(q)
        assert pdf[:4] == b"%PDF"
        assert len(pdf) > 2000

    def test_a_whole_number_rate_prints_without_decimals(self, owner, product, profile):
        """
        "{Decimal('17.00'):g}" keeps its trailing zeros, so the quotation
        printed "Tax (17.00%)" where the invoice for the same rate prints
        "Tax (17%)". Two documents from one shop disagreeing on the format of
        the same number.
        """
        from decimal import Decimal

        q = create_quotation(created_by=owner, items=_lines(product),
                             profile_id=profile.id, tax_pct="17")
        assert q.tax_pct == Decimal("17.00")
        assert f"{float(q.tax_pct):g}" == "17"

    def test_it_renders_without_a_business_profile(self, owner, product):
        """A quotation raised before anyone set a letterhead up must still print."""
        from apps.sales.receipts.quotation_pdf import render_quotation_pdf

        q = create_quotation(created_by=owner, items=_lines(product))
        assert render_quotation_pdf(q)[:4] == b"%PDF"

    def test_it_picks_the_default_profile_by_itself(self, owner, product, profile):
        q = create_quotation(created_by=owner, items=_lines(product))
        assert q.profile_id == profile.id


@pytest.mark.django_db
class TestBusinessProfiles:
    def test_the_shop_has_a_letterhead_out_of_the_box(self, db):
        """
        Migration 0014 builds one from the shop's own settings, so the first
        quotation anyone raises prints with a proper header rather than
        needing a trip to Settings first.
        """
        assert BusinessProfile.objects.filter(is_default=True).exists()

    def test_only_one_profile_can_be_the_default(self, db, profile):
        second = BusinessProfile.objects.create(name="Speed Tech Enterprises", is_default=True)
        profile.refresh_from_db()
        assert second.is_default is True
        assert profile.is_default is False

    def test_a_cashier_cannot_change_a_letterhead(self, cashier, profile):
        c = _client_for(cashier)
        assert c.get("/api/business-profiles/").status_code == status.HTTP_200_OK
        assert c.patch(f"/api/business-profiles/{profile.id}/", {"name": "Fake Co"},
                       format="json").status_code == status.HTTP_403_FORBIDDEN


# ── The API ────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestTheApi:
    def _payload(self, product):
        return {
            "items": [
                {"product_id": product.id, "qty": "4"},
                {"name": "Cat-6 cable, 90m — supplied and laid", "qty": "1",
                 "unit_price_paise": 1800000},
            ],
            "customer_name": "Balochistan Textiles Ltd",
            "valid_days": 30,
        }

    def test_a_cashier_can_raise_one(self, cashier, product):
        """Quoting is counter work, not a management task."""
        resp = _client_for(cashier).post("/api/quotations/", self._payload(product), format="json")
        assert resp.status_code == status.HTTP_201_CREATED, resp.data
        assert resp.data["total_paise"] == 2200000
        assert len(resp.data["items"]) == 2

    def test_the_pdf_endpoint_returns_a_pdf(self, owner_client, product, profile):
        created = owner_client.post("/api/quotations/", self._payload(product), format="json")
        resp = owner_client.get(f"/api/quotations/{created.data['id']}/pdf/")
        assert resp.status_code == status.HTTP_200_OK
        assert resp["Content-Type"] == "application/pdf"
        assert resp.content[:4] == b"%PDF"

    def test_an_empty_quotation_is_a_400(self, owner_client):
        resp = owner_client.post("/api/quotations/", {"items": []}, format="json")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_a_line_with_no_product_and_no_name_is_a_400(self, owner_client):
        resp = owner_client.post(
            "/api/quotations/", {"items": [{"qty": "1", "unit_price_paise": 500}]},
            format="json",
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert "product or a description" in str(resp.data)

    def test_status_can_be_moved_along(self, owner_client, product):
        created = owner_client.post("/api/quotations/", self._payload(product), format="json")
        resp = owner_client.post(f"/api/quotations/{created.data['id']}/status/",
                                 {"status": "sent"}, format="json")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["status"] == "sent"

    def test_an_unknown_status_is_refused(self, owner_client, product):
        created = owner_client.post("/api/quotations/", self._payload(product), format="json")
        resp = owner_client.post(f"/api/quotations/{created.data['id']}/status/",
                                 {"status": "banana"}, format="json")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_the_cart_endpoint_answers(self, owner_client, product):
        created = owner_client.post("/api/quotations/", self._payload(product), format="json")
        resp = owner_client.get(f"/api/quotations/{created.data['id']}/to-cart/")
        assert resp.status_code == status.HTTP_200_OK
        assert len(resp.data["items"]) == 1
        assert len(resp.data["off_catalogue_items"]) == 1
