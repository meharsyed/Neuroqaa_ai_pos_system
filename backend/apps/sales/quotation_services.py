"""Creating, revising and converting quotations."""

from decimal import Decimal


def _rate(value) -> Decimal | None:
    """A tax rate at the column's precision, or None."""
    if value in (None, ""):
        return None
    rate = Decimal(str(value)).quantize(Decimal("0.01"))
    if rate < 0 or rate > 100:
        raise ValueError("A tax rate must be between 0 and 100 percent.")
    return rate

from django.db import transaction
from django.utils import timezone

from apps.accounts.activity import log_activity

from .quotations import BusinessProfile, Quotation, QuotationItem


def _number_for(quotation: Quotation) -> str:
    return f"QT-{timezone.localdate():%Y%m%d}-{quotation.pk:05d}"


def _line_from(raw: dict) -> dict:
    """
    Normalise one line, whether it names a catalogue product or not.

    A catalogue line still stores its own name, sku and price rather than
    reading through to the product: a quotation is a document, and it must
    keep saying what it said on the day it went out even if the product is
    renamed or repriced afterwards.
    """
    from apps.catalog.models import Product

    product = None
    pid = raw.get("product_id")
    if pid:
        try:
            product = Product.objects.select_related("category").get(pk=pid)
        except Product.DoesNotExist:
            raise ValueError(f"Product {pid} does not exist.")

    name = (raw.get("name") or "").strip() or (product.name if product else "")
    if not name:
        raise ValueError("Every line needs a description.")

    qty = Decimal(str(raw.get("qty") or 1))
    if qty <= 0:
        raise ValueError(f"Quantity must be more than zero on '{name}'.")

    unit_price = raw.get("unit_price_paise")
    if unit_price is None:
        unit_price = product.sell_price_paise if product else 0
    unit_price = int(unit_price)
    if unit_price < 0:
        raise ValueError(f"A price cannot be negative on '{name}'.")

    discount = int(raw.get("discount_paise") or 0)
    if discount < 0:
        raise ValueError(f"A discount cannot be negative on '{name}'.")
    if discount > int(qty * unit_price):
        raise ValueError(f"The discount on '{name}' is more than the line itself.")

    return {
        "product": product,
        "name": name,
        "sku": (raw.get("sku") or (product.sku if product else "")).strip(),
        "description": (raw.get("description") or "").strip(),
        "qty": qty,
        "unit": (raw.get("unit") or (product.unit if product else "")).strip(),
        "unit_price_paise": unit_price,
        "discount_paise": discount,
    }


@transaction.atomic
def create_quotation(
    *,
    created_by,
    items: list[dict],
    profile_id: int | None = None,
    customer_id: int | None = None,
    customer_name: str = "",
    customer_phone: str = "",
    customer_address: str = "",
    discount_paise: int = 0,
    tax_pct: Decimal | float | str | None = None,
    installation_paise: int = 0,
    installation_note: str = "",
    valid_days: int = 15,
    notes: str = "",
    terms: str = "",
) -> Quotation:
    if not items:
        raise ValueError("A quotation needs at least one line.")

    lines = [_line_from(raw) for raw in items]

    if profile_id is None:
        default = BusinessProfile.objects.filter(is_default=True, is_active=True).first()
        profile_id = default.pk if default else None

    quotation = Quotation.objects.create(
        created_by=created_by,
        profile_id=profile_id,
        customer_id=customer_id,
        customer_name=customer_name.strip(),
        customer_phone=customer_phone.strip(),
        customer_address=customer_address.strip(),
        discount_paise=max(0, int(discount_paise)),
        tax_pct=_rate(tax_pct),
        installation_paise=max(0, int(installation_paise)),
        installation_note=installation_note.strip(),
        valid_days=max(1, int(valid_days)),
        notes=notes,
        terms=terms,
    )
    quotation.number = _number_for(quotation)

    for position, line in enumerate(lines):
        QuotationItem.objects.create(quotation=quotation, position=position, **line)

    quotation.recalculate()
    quotation.save()

    log_activity(
        "quotation_created",
        user=created_by,
        details={"number": quotation.number, "total_paise": quotation.total_paise},
    )
    return quotation


@transaction.atomic
def revise_quotation(*, quotation: Quotation, created_by, **changes) -> Quotation:
    """
    Replace a quotation's contents and bump the revision.

    A negotiation is one document that moves, not a pile of near-identical
    ones — the customer is looking at "QT-…-00007 rev 3", and the number they
    were given first still finds it.
    """
    if quotation.converted_sale_id:
        raise ValueError("This quotation has already become a sale.")

    items = changes.pop("items", None)
    if items is not None:
        if not items:
            raise ValueError("A quotation needs at least one line.")
        lines = [_line_from(raw) for raw in items]
        quotation.items.all().delete()
        for position, line in enumerate(lines):
            QuotationItem.objects.create(quotation=quotation, position=position, **line)

    for field in (
        "profile_id", "customer_id", "customer_name", "customer_phone",
        "customer_address", "discount_paise", "installation_paise",
        "installation_note", "valid_days", "notes", "terms", "status",
    ):
        if field in changes and changes[field] is not None:
            setattr(quotation, field, changes[field])
    if "tax_pct" in changes:
        quotation.tax_pct = _rate(changes["tax_pct"])

    quotation.revision += 1
    quotation.recalculate()
    quotation.save()
    return quotation


def quotation_to_cart(quotation: Quotation) -> dict:
    """
    What the till needs to pick this quotation up.

    Catalogue lines come back with a product id so they deduct stock when the
    sale completes. Off-catalogue lines cannot — there is nothing to deduct —
    so they are handed back separately for the cashier to deal with rather
    than silently dropped.
    """
    stocked, off_catalogue = [], []
    for item in quotation.items.select_related("product"):
        row = {
            "name": item.name,
            "sku": item.sku,
            "qty": str(item.qty),
            "unit_price_paise": item.unit_price_paise,
            "discount_paise": item.discount_paise,
        }
        if item.product_id and item.product and item.product.is_active:
            stocked.append({**row, "product_id": item.product_id})
        else:
            off_catalogue.append(row)

    return {
        "quotation_id": quotation.pk,
        "number": quotation.display_number,
        "customer_id": quotation.customer_id,
        "items": stocked,
        "off_catalogue_items": off_catalogue,
        "discount_paise": quotation.discount_paise,
        "tax_pct": str(quotation.tax_pct) if quotation.tax_pct is not None else None,
        "installation_paise": quotation.installation_paise,
        "installation_note": quotation.installation_note,
    }


def mark_converted(*, quotation: Quotation, sale, user=None) -> Quotation:
    quotation.converted_sale = sale
    quotation.converted_at = timezone.now()
    quotation.status = Quotation.Status.ACCEPTED
    quotation.save(update_fields=["converted_sale", "converted_at", "status", "updated_at"])
    log_activity(
        "quotation_converted",
        user=user or quotation.created_by,
        details={"number": quotation.number, "sale_number": sale.sale_number},
    )
    return quotation
