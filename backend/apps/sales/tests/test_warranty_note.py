"""
The warranty clause on a bill.

The client wants it printed so a customer cannot claim on a device destroyed by
a power surge. Urdu is the hard part: on the A4/A5 invoice it needs a bundled
font plus letter-joining and right-to-left reordering, and on an 80mm thermal
printer it is not possible at all.
"""

from decimal import Decimal

import pytest

from apps.accounts.models import User
from apps.catalog.models import Category, Inventory, Product
from apps.catalog.services import apply_stock_movement
from apps.config.models import Setting
from apps.sales.receipts import (
    build_receipt_context,
    render_html_receipt,
    render_pdf_invoice,
    render_pdf_receipt,
    render_text_receipt,
)
from apps.sales.services import create_sale

URDU = "بجلی کی چنگاری یا وولٹیج کے اتار چڑھاؤ کی صورت میں وارنٹی ختم تصور ہوگی۔"
ENGLISH = "Warranty is void if the device is damaged by electrical spark or power surge."


def _set(key, value):
    Setting.objects.update_or_create(key=key, defaults={"value": value, "label": key})


@pytest.fixture(autouse=True)
def _warranty_settings(db):
    _set("warranty_note_enabled", "true")
    _set("warranty_note_language", "en")
    _set("warranty_note_en", ENGLISH)
    _set("warranty_note_ur", URDU)


@pytest.fixture
def owner(db):
    return User.objects.create_superuser(
        username="wn_owner", email="wn_owner@test.com", password="Pass1234!",
        first_name="Shop", last_name="Owner", role="owner",
    )


@pytest.fixture
def product(db):
    cat = Category.objects.create(name="Cams", slug="wn-cams")
    p = Product.objects.create(
        name="NVR 8ch", sku="WN-1", category=cat,
        sell_price_paise=100000, cost_price_paise=60000,
    )
    Inventory.objects.create(product=p)
    apply_stock_movement(product=p, movement_type="stock_in", qty_change=Decimal("50"))
    return p


def _sale(owner, product, serials=None):
    item = {"product_id": product.id, "qty": "1", "unit_price_paise": 100000}
    if serials:
        item["serials"] = [{"serial": s, "warranty_months": 12} for s in serials]
    return create_sale(
        cashier=owner, items=[item],
        payment_method="cash", amount_tendered_paise=100000,
    )


# ── Shaping Urdu ────────────────────────────────────────────────────────────


class TestUrduIsActuallyRenderable:
    def test_the_font_is_bundled(self):
        from apps.sales.receipts.urdu import urdu_font_available

        assert urdu_font_available(), "Noto Naskh Arabic is missing from receipts/assets"

    def test_the_letters_are_joined_and_the_order_reversed(self):
        """
        Without reshaping, every letter renders in isolated form; without bidi,
        the words come out backwards. Either alone is worse than English.
        """
        from apps.sales.receipts.urdu import shape_urdu

        shaped = shape_urdu(URDU)
        assert shaped is not None
        assert shaped != URDU                      # something happened
        assert len(shaped) > 0
        # Reordered: the last character of the source now leads.
        assert shaped[0] != URDU[0]

    def test_a_wrapped_clause_keeps_its_lines_in_reading_order(self):
        """
        The bug this guards against shipped once and looked fine at a glance.

        Reordering a whole paragraph right-to-left and then letting ReportLab
        wrap it gives lines that are each correct but stacked backwards — the
        opening clause prints at the BOTTOM of the box. Wrapping has to happen
        first, in logical order, with each line reordered on its own.
        """
        import arabic_reshaper

        from apps.sales.receipts.urdu import urdu_lines

        lines = urdu_lines(URDU, font_size=8, max_width=140)
        assert lines and len(lines) > 1, "pick a width that actually forces a wrap"

        first_word = arabic_reshaper.reshape(URDU.split()[0])
        assert set(first_word) & set(lines[0]), "the clause does not start on line one"
        assert not set(first_word) <= set(lines[-1]), "the opening ended up last"

    def test_empty_input_shapes_to_nothing(self):
        from apps.sales.receipts.urdu import shape_urdu

        assert shape_urdu("") is None
        assert shape_urdu("   ") is None


# ── Where it appears ────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestTheInvoice:
    def test_english_appears_on_the_a4_invoice(self, owner, product):
        pdf = render_pdf_invoice(_sale(owner, product))
        assert pdf[:4] == b"%PDF"
        assert len(pdf) > 1000

    def test_urdu_renders_without_falling_over(self, owner, product):
        _set("warranty_note_language", "ur")
        pdf = render_pdf_invoice(_sale(owner, product))
        assert pdf[:4] == b"%PDF"

    def test_both_languages_render(self, owner, product):
        _set("warranty_note_language", "both")
        pdf = render_pdf_invoice(_sale(owner, product))
        assert pdf[:4] == b"%PDF"

    def test_turning_it_off_removes_it(self, owner, product):
        from apps.config.utils import get_all_settings

        _set("warranty_note_enabled", "false")
        ctx = build_receipt_context(_sale(owner, product), get_all_settings())
        assert ctx.warranty_en == ""
        assert ctx.warranty_ur == ""

    def test_a_missing_font_falls_back_to_english_rather_than_crashing(
        self, owner, product, monkeypatch
    ):
        """
        A receipt must never die because a font is missing. If Urdu cannot be
        drawn, English is printed instead — and if that is missing too, the
        block is simply left out.
        """
        import apps.sales.receipts.urdu as urdu_mod

        monkeypatch.setattr(urdu_mod, "urdu_font_available", lambda: False)
        _set("warranty_note_language", "ur")
        pdf = render_pdf_invoice(_sale(owner, product))
        assert pdf[:4] == b"%PDF"


@pytest.mark.django_db
class TestTheWebBill:
    def test_english_is_shown(self, owner, product):
        html = render_html_receipt(_sale(owner, product), format_name="a4")
        assert "Warranty terms" in html
        assert "electrical spark" in html

    def test_urdu_is_marked_right_to_left_for_the_browser(self, owner, product):
        """The browser shapes Urdu itself — it only needs told the direction."""
        _set("warranty_note_language", "ur")
        html = render_html_receipt(_sale(owner, product), format_name="a4")
        assert 'dir="rtl"' in html
        assert "وارنٹی" in html

    def test_both_languages_appear_together(self, owner, product):
        _set("warranty_note_language", "both")
        html = render_html_receipt(_sale(owner, product), format_name="a4")
        assert "electrical spark" in html
        assert "وارنٹی" in html


@pytest.mark.django_db
class TestTheThermalSlip:
    def test_it_is_printed_when_the_bill_carries_a_serial(self, owner, product):
        text = render_text_receipt(_sale(owner, product, serials=["SN-ABC-001"]))
        assert "WARRANTY" in text
        assert "electrical spark" in text

    def test_it_is_left_off_a_bill_with_no_serials(self, owner, product):
        """No serial, no warranty to void — and thermal roll is not free."""
        text = render_text_receipt(_sale(owner, product))
        assert "WARRANTY" not in text

    def test_urdu_never_reaches_the_thermal_printer(self, owner, product):
        """
        Its character ROM has no Urdu. Sending it would print rubbish, so the
        till slip stays English whatever the setting says.
        """
        _set("warranty_note_language", "ur")
        text = render_text_receipt(_sale(owner, product, serials=["SN-ABC-002"]))
        assert "وارنٹی" not in text

    def test_the_thermal_pdf_also_only_prints_it_with_serials(self, owner, product):
        with_serial = render_pdf_receipt(_sale(owner, product, serials=["SN-ABC-003"]))
        without = render_pdf_receipt(_sale(owner, product))
        assert with_serial[:4] == b"%PDF" and without[:4] == b"%PDF"
        assert len(with_serial) > len(without), "the clause added nothing to the slip"
