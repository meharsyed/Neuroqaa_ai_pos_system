#!/usr/bin/env python
"""
Setup script for CCTV Store demo data
Adds 10 products, 5 categories, and 10-15 sample bills
"""

import os
import django
from datetime import datetime, timedelta
from decimal import Decimal
import random

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.desktop')
django.setup()

from apps.catalog.models import Category, Product, Inventory
from apps.sales.models import Sale, SaleItem, Payment, Shift
from apps.sales.services import create_sale
from apps.accounts.models import User

print("=" * 60)
print("CCTV STORE DEMO DATA SETUP")
print("=" * 60)

# ====== STEP 1: CREATE CATEGORIES ======
print("\n[1] Creating categories...")

categories_data = [
    {"name": "Dome Cameras", "description": "Fixed and PTZ dome cameras"},
    {"name": "Bullet Cameras", "description": "Outdoor and IR bullet cameras"},
    {"name": "Recording Systems", "description": "DVR and NVR systems"},
    {"name": "Cables & Accessories", "description": "Cables, connectors, power supplies"},
    {"name": "Monitoring Displays", "description": "LCD/LED monitors for surveillance"},
]

categories = {}
for cat_data in categories_data:
    cat, created = Category.objects.get_or_create(
        name=cat_data["name"],
        defaults={"description": cat_data["description"], "tenant_id": 1}
    )
    categories[cat_data["name"]] = cat
    status = "Created" if created else "Existing"
    print(f"  [{status}] {cat.name}")

# ====== STEP 2: CREATE PRODUCTS ======
print("\n[2] Creating products...")

products_data = [
    # Dome Cameras
    {"name": "2MP Fixed Dome Camera", "sku": "DMC-2MP-001", "category": "Dome Cameras", "price_paise": 850000, "stock": 5},
    {"name": "4MP PTZ Dome Camera", "sku": "DMC-4MP-PTZ", "category": "Dome Cameras", "price_paise": 1500000, "stock": 2},
    {"name": "5MP Varifocal Dome", "sku": "DMC-5MP-VAR", "category": "Dome Cameras", "price_paise": 1200000, "stock": 3},

    # Bullet Cameras
    {"name": "2MP Outdoor Bullet", "sku": "BUL-2MP-OUT", "category": "Bullet Cameras", "price_paise": 750000, "stock": 6},
    {"name": "4MP IR Bullet Camera", "sku": "BUL-4MP-IR", "category": "Bullet Cameras", "price_paise": 1100000, "stock": 4},

    # Recording Systems
    {"name": "8CH DVR (1TB)", "sku": "DVR-8CH-1TB", "category": "Recording Systems", "price_paise": 1800000, "stock": 2},
    {"name": "4CH NVR (500GB)", "sku": "NVR-4CH-500", "category": "Recording Systems", "price_paise": 2200000, "stock": 1},

    # Cables & Accessories
    {"name": "CCTV Cable Reel (300m)", "sku": "CAB-300M-REEL", "category": "Cables & Accessories", "price_paise": 450000, "stock": 8},
    {"name": "Power Supply Unit (12V/2A)", "sku": "PSU-12V-2A", "category": "Cables & Accessories", "price_paise": 250000, "stock": 15},

    # Displays
    {"name": "21.5\" LED Monitor", "sku": "MON-215-LED", "category": "Monitoring Displays", "price_paise": 1400000, "stock": 2},
]

products = {}
for prod_data in products_data:
    prod, created = Product.objects.get_or_create(
        sku=prod_data["sku"],
        defaults={
            "name": prod_data["name"],
            "category": categories[prod_data["category"]],
            "sell_price_paise": prod_data["price_paise"],
            "cost_price_paise": int(prod_data["price_paise"] * 0.6),  # 60% cost
            "low_stock_threshold": Decimal("2"),
            "unit": "pcs",
            "tenant_id": 1,
        }
    )

    # Create or update inventory
    inventory, inv_created = Inventory.objects.get_or_create(
        product=prod,
        defaults={
            "stock_qty": Decimal(str(prod_data["stock"])),
            "tenant_id": 1,
        }
    )
    if not inv_created:
        inventory.stock_qty = Decimal(str(prod_data["stock"]))
        inventory.save()

    products[prod_data["sku"]] = prod
    price_pkr = prod_data["price_paise"] / 100
    status = "Created" if created else "Existing"
    print(f"  [{status}] {prod.name} - {price_pkr:.0f} PKR")

print(f"\n  Total: {len(products)} products")

# ====== STEP 3: CREATE SAMPLE SALES ======
print("\n[3] Creating sample sales transactions...")

payment_methods = ["cash", "card", "bank_transfer"]

sale_configs = [
    {"items": [("DMC-2MP-001", 2), ("CAB-300M-REEL", 1)], "discount_pct": 5},
    {"items": [("BUL-2MP-OUT", 1), ("PSU-12V-2A", 2)], "discount_pct": 0},
    {"items": [("DVR-8CH-1TB", 1), ("DMC-4MP-PTZ", 2), ("MON-215-LED", 1)], "discount_pct": 10},
    {"items": [("NVR-4CH-500", 1), ("BUL-4MP-IR", 1), ("CAB-300M-REEL", 1)], "discount_pct": 0},
    {"items": [("DMC-5MP-VAR", 3), ("PSU-12V-2A", 3)], "discount_pct": 7},
    {"items": [("BUL-2MP-OUT", 2), ("MON-215-LED", 1), ("CAB-300M-REEL", 1)], "discount_pct": 3},
    {"items": [("DMC-2MP-001", 1), ("BUL-4MP-IR", 1), ("DVR-8CH-1TB", 1)], "discount_pct": 8},
    {"items": [("PSU-12V-2A", 5)], "discount_pct": 0},
    {"items": [("DMC-4MP-PTZ", 1), ("NVR-4CH-500", 1)], "discount_pct": 5},
    {"items": [("CAB-300M-REEL", 2), ("BUL-2MP-OUT", 1)], "discount_pct": 2},
    {"items": [("DMC-2MP-001", 1), ("BUL-2MP-OUT", 1)], "discount_pct": 0},
    {"items": [("DVR-8CH-1TB", 1), ("CAB-300M-REEL", 2)], "discount_pct": 5},
    {"items": [("MON-215-LED", 2)], "discount_pct": 15},
    {"items": [("BUL-4MP-IR", 2), ("PSU-12V-2A", 4)], "discount_pct": 0},
]

# Get or create a default cashier user
cashier, _ = User.objects.get_or_create(
    username="demo_cashier",
    defaults={
        "email": "cashier@cctv.demo",
        "first_name": "Demo",
        "last_name": "Cashier",
        "role": "cashier",
        "is_active": True,
    }
)

sales_created = 0
for idx, config in enumerate(sale_configs):
    try:
        # Build items list
        items = []
        total_before_discount = 0

        for sku, qty in config["items"]:
            product = products[sku]
            total_before_discount += product.sell_price_paise * qty
            items.append({
                "product_id": product.id,
                "qty": qty,
                "unit_price_paise": product.sell_price_paise,
                "discount_paise": 0,
            })

        # Calculate discount
        discount_paise = int(total_before_discount * config["discount_pct"] / 100)

        # Calculate total
        total_paise = total_before_discount - discount_paise

        # Create sale
        sale = create_sale(
            cashier=cashier,
            items=items,
            payment_method=random.choice(payment_methods),
            amount_tendered_paise=total_paise + random.randint(0, 10000),
            discount_paise=discount_paise,
        )

        # Update created_at to spread over past 4 days
        days_back = idx % 4
        sale.created_at = datetime.now() - timedelta(days=days_back, hours=random.randint(0, 23))
        sale.save()

        total_pkr = total_paise / 100
        sales_created += 1
        print(f"  [Bill {idx + 1}] {len(config['items'])} items, Total: {total_pkr:.0f} PKR (Discount: {config['discount_pct']}%)")
    except Exception as e:
        print(f"  [ERROR] Bill {idx + 1} failed: {str(e)}")

# ====== FINAL SUMMARY ======
print("\n" + "=" * 60)
print("SETUP COMPLETE!")
print("=" * 60)

try:
    cat_count = Category.objects.count()
    prod_count = Product.objects.count()
    sale_count = Sale.objects.count()

    print(f"\nDatabase Statistics:")
    print(f"  Categories: {cat_count}")
    print(f"  Products: {prod_count}")
    print(f"  Sales Created: {sales_created}")
    print(f"  Total Sales in DB: {sale_count}")

    print(f"\nYou can now:")
    print(f"  1. Start the frontend: npm run dev")
    print(f"  2. Open dashboard: http://localhost:5173/dashboard")
    print(f"  3. View products: http://localhost:5173/products")
    print(f"  4. Check bills: http://localhost:5173/bills")
    print(f"  5. View reports: http://localhost:5173/audit")

except Exception as e:
    print(f"Error getting statistics: {str(e)}")

print("\n" + "=" * 60)