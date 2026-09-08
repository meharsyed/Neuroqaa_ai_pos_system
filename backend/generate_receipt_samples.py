"""
Generate 8 sample receipts in all formats (PDF/HTML/text) for manual testing

Run from project root:
    cd backend && python manage.py shell < generate_receipt_samples.py
"""

import os
import sys
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.catalog.models import Category, Product
from apps.customers.models import Customer
from apps.sales.models import Sale, SaleItem, Payment
from apps.sales.receipts import (
    render_pdf_receipt,
    render_pdf_invoice,
    render_html_receipt,
    render_text_receipt,
)
from apps.config.utils import get_all_settings

User = get_user_model()


def ensure_samples_dir():
    """Create tmp/receipt_samples directory"""
    path = "tmp/receipt_samples"
    os.makedirs(path, exist_ok=True)
    return path


def create_user():
    """Get or create test cashier"""
    user, _ = User.objects.get_or_create(
        username="sample_cashier",
        defaults={
            "email": "sample@test.com",
            "first_name": "Sample",
            "last_name": "Cashier",
            "role": "cashier"
        }
    )
    return user


def create_products():
    """Get or create test products"""
    category, _ = Category.objects.get_or_create(name="Sample Products")
    products = {}

    product_data = [
        ("Widget A", "WIDGET-A", 25000),
        ("Widget B", "WIDGET-B", 50000),
        ("Deluxe Widget", "WIDGET-DLX", 150000),
        ("Premium Set", "SET-PREM", 300000),
    ]

    for name, sku, price in product_data:
        p, _ = Product.objects.get_or_create(
            sku=sku,
            defaults={"name": name, "category": category, "sell_price_paise": price}
        )
        products[sku] = p

    return products


def create_customer():
    """Get or create test customer"""
    customer, _ = Customer.objects.get_or_create(
        phone="+92 321 1234567",
        defaults={"name": "Sample Customer"}
    )
    return customer


def create_sale(cashier, products, customer=None, **sale_kwargs):
    """Create a sale with items and payment"""
    sale = Sale.objects.create(
        cashier=cashier,
        customer=customer,
        **sale_kwargs
    )

    # Add items to sale
    for product, qty in products:
        SaleItem.objects.create(
            sale=sale,
            product=product,
            qty=Decimal(str(qty)),
            unit_price_paise=product.sell_price_paise,
            subtotal_paise=int(product.sell_price_paise * qty),
        )

    # Recalculate totals
    subtotal = sum(item.subtotal_paise for item in sale.items.all())
    sale.subtotal_paise = subtotal
    sale.tax_paise = int(subtotal * 0.17)
    sale.total_paise = subtotal + sale.tax_paise - (sale.discount_paise or 0)
    sale.save()

    # Create payment
    Payment.objects.create(
        sale=sale,
        method="cash",
        amount_tendered_paise=sale.total_paise + 10000,  # Add change
        change_paise=10000,
    )

    return sale


def generate_samples():
    """Generate 8 sample sales and render all formats"""
    print("📋 Generating receipt samples...")

    samples_dir = ensure_samples_dir()
    print(f"📁 Using directory: {samples_dir}")

    cashier = create_user()
    products = create_products()
    customer = create_customer()
    shop_settings = get_all_settings()

    # Sample 1: Single item
    print("1️⃣  Single item sale...")
    sale = create_sale(
        cashier,
        [(products["WIDGET-A"], 1)],
        customer,
        discount_paise=0,
    )
    _save_all_formats(sale, samples_dir, "1_single_item")

    # Sample 2: Three items
    print("2️⃣  Three items sale...")
    sale = create_sale(
        cashier,
        [(products["WIDGET-A"], 2), (products["WIDGET-B"], 1), (products["Widget B"], 0.5)],
        customer,
        discount_paise=0,
    )
    _save_all_formats(sale, samples_dir, "2_three_items")

    # Sample 3: Decimal quantities
    print("3️⃣  Decimal quantity sale...")
    sale = create_sale(
        cashier,
        [(products["WIDGET-B"], 2.5)],
        customer,
        discount_paise=0,
    )
    _save_all_formats(sale, samples_dir, "3_decimal_qty")

    # Sample 4: With bill discount
    print("4️⃣  Bill discount sale...")
    sale = create_sale(
        cashier,
        [(products["WIDGET-DLX"], 1), (products["WIDGET-A"], 3)],
        customer,
        discount_paise=10000,  # 100 Rs discount
    )
    _save_all_formats(sale, samples_dir, "4_bill_discount")

    # Sample 5: Large order (25 items)
    print("5️⃣  Large order...")
    items = [
        (products["WIDGET-A"], 5),
        (products["WIDGET-B"], 10),
        (products["WIDGET-DLX"], 3),
        (products["SET-PREM"], 2),
        (products["WIDGET-A"], 5),  # Re-use for variety
    ]
    sale = create_sale(
        cashier,
        items,
        customer,
        discount_paise=0,
    )
    _save_all_formats(sale, samples_dir, "5_large_order")

    # Sample 6: No customer
    print("6️⃣  Walk-in (no customer)...")
    sale = create_sale(
        cashier,
        [(products["WIDGET-A"], 1)],
        customer=None,
        discount_paise=0,
    )
    _save_all_formats(sale, samples_dir, "6_no_customer")

    # Sample 7: Voided sale
    print("7️⃣  Voided sale...")
    sale = create_sale(
        cashier,
        [(products["WIDGET-B"], 2)],
        customer,
        discount_paise=0,
    )
    sale.status = "voided"
    sale.save()
    _save_all_formats(sale, samples_dir, "7_voided")

    # Sample 8: Return/credit note
    print("8️⃣  Return sale...")
    sale = create_sale(
        cashier,
        [(products["WIDGET-DLX"], 1)],
        customer,
        discount_paise=0,
        sale_type="return",
    )
    _save_all_formats(sale, samples_dir, "8_return")

    # Summary
    print("\n✅ Receipt samples generated:")
    files = sorted(os.listdir(samples_dir))
    for f in files:
        fpath = os.path.join(samples_dir, f)
        size = os.path.getsize(fpath) / 1024
        print(f"   {f} ({size:.1f} KB)")

    print(f"\n📂 All files saved to: {samples_dir}/")


def _save_all_formats(sale, base_dir, name):
    """Save receipt in all formats"""
    try:
        # PDF Receipt (80mm thermal)
        pdf_receipt = render_pdf_receipt(sale)
        with open(f"{base_dir}/{name}_thermal.pdf", "wb") as f:
            f.write(pdf_receipt)

        # PDF Invoice (A4)
        pdf_invoice = render_pdf_invoice(sale)
        with open(f"{base_dir}/{name}_invoice.pdf", "wb") as f:
            f.write(pdf_invoice)

        # HTML A4
        html_a4 = render_html_receipt(sale, format_name="a4")
        with open(f"{base_dir}/{name}_view_a4.html", "w") as f:
            f.write(html_a4)

        # HTML Thermal
        html_thermal = render_html_receipt(sale, format_name="thermal")
        with open(f"{base_dir}/{name}_view_thermal.html", "w") as f:
            f.write(html_thermal)

        # Text receipt
        text = render_text_receipt(sale)
        with open(f"{base_dir}/{name}.txt", "w") as f:
            f.write(text)

        print(f"   ✓ Saved {name}")
    except Exception as e:
        print(f"   ✗ Error saving {name}: {e}")


if __name__ == "__main__":
    try:
        generate_samples()
        print("\n🎉 Done!")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
