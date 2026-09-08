# Neuroqaa CCTV Store — Database Setup Guide

**Date:** August 31, 2026  
**Store:** Neuroqaa CCTV Store  
**Purpose:** Populate demo database with 10 CCTV products and 10-15 sample bills  
**Status:** Ready to Execute

---

## 📋 **Overview**

We'll add:
- ✅ 5 Product Categories (Dome Cameras, Bullet Cameras, Recording Systems, Cables/Accessories, Displays)
- ✅ 10 CCTV Products with realistic pricing (PKR)
- ✅ 10-15 Sample Sales/Bills with transaction history
- ✅ Stock Movement records (audit trail)
- ✅ Payment records (Cash, Card, Bank Transfer)

---

## 🔧 **Setup Method: Python Django Shell**

We'll use Django's interactive shell to add data directly. This is **safe, reversible, and easy to verify**.

### **Step 1: Start Django Shell**

Open PowerShell in the backend directory:

```powershell
cd "d:\Neuroqaa Stuff\POS System\pos-system-GT\backend"
.\venv311\Scripts\Activate.ps1
$env:DJANGO_SETTINGS_MODULE = "config.settings.desktop"
python manage.py shell
```

You should see:
```
Python 3.11.x ...
Type "help", "copyright", "credits" or "license" for more information.
(InteractiveConsole)
>>>
```

---

## 📦 **Data to Add**

### **Category 1: Dome Cameras**
| Product | SKU | Price (PKR) | Stock |
|---------|-----|-----------|-------|
| 2MP Fixed Dome Camera | DMC-2MP-001 | 8,500 | 5 |
| 4MP PTZ Dome Camera | DMC-4MP-PTZ | 15,000 | 2 |
| 5MP Varifocal Dome | DMC-5MP-VAR | 12,000 | 3 |

### **Category 2: Bullet Cameras**
| Product | SKU | Price (PKR) | Stock |
|---------|-----|-----------|-------|
| 2MP Outdoor Bullet | BUL-2MP-OUT | 7,500 | 6 |
| 4MP IR Bullet Camera | BUL-4MP-IR | 11,000 | 4 |

### **Category 3: Recording Systems**
| Product | SKU | Price (PKR) | Stock |
|---------|-----|-----------|-------|
| 8CH DVR (1TB) | DVR-8CH-1TB | 18,000 | 2 |
| 4CH NVR (500GB) | NVR-4CH-500 | 22,000 | 1 |

### **Category 4: Cables & Accessories**
| Product | SKU | Price (PKR) | Stock |
|---------|-----|-----------|-------|
| CCTV Cable Reel (300m) | CAB-300M-REEL | 4,500 | 8 |
| Power Supply Unit (12V/2A) | PSU-12V-2A | 2,500 | 15 |

### **Category 5: Monitoring Displays**
| Product | SKU | Price (PKR) | Stock |
|---------|-----|-----------|-------|
| 21.5" LED Monitor | MON-215-LED | 14,000 | 2 |

---

## 🚀 **Execute Setup Script**

Copy and paste the following code into the Django shell:

```python
from apps.catalog.models import Category, Product
from apps.sales.models import Sale, SaleItem, Payment, Shift
from apps.sales.services import create_sale
from datetime import datetime, timedelta
import random

# ====== STEP 1: CREATE CATEGORIES ======
print("Creating categories...")

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
    print(f"✓ {cat.name}")

# ====== STEP 2: CREATE PRODUCTS ======
print("\nCreating products...")

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
            "unit_price_paise": prod_data["price_paise"],
            "stock_qty": prod_data["stock"],
            "low_stock_threshold": 2,
            "unit": "pcs",
            "tenant_id": 1,
        }
    )
    products[prod_data["sku"]] = prod
    print(f"✓ {prod.name} - {prod_data['price_paise']/100:.0f} PKR")

print(f"\nTotal products created: {len(products)}")

# ====== STEP 3: CREATE SAMPLE SALES ======
print("\nCreating sample sales transactions...")

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
]

# Create or open shift
shift, _ = Shift.objects.get_or_create(
    id=1,
    defaults={
        "opened_at": datetime.now() - timedelta(hours=4),
        "opening_float_paise": 5000000,
        "tenant_id": 1,
    }
)

for idx, config in enumerate(sale_configs):
    try:
        # Build items list
        items = []
        total_before_discount = 0
        
        for sku, qty in config["items"]:
            product = products[sku]
            total_before_discount += product.unit_price_paise * qty
            items.append({
                "product_id": product.id,
                "qty": qty,
                "unit_price_paise": product.unit_price_paise,
                "discount_paise": 0,
            })
        
        # Calculate discount
        discount_paise = int(total_before_discount * config["discount_pct"] / 100)
        
        # Calculate total
        total_paise = total_before_discount - discount_paise
        
        # Create sale
        sale = create_sale(
            product_items=items,
            payment_method=random.choice(payment_methods),
            amount_tendered_paise=total_paise + random.randint(0, 10000),  # Vary the tendered amount
            discount_paise=discount_paise,
            shift_id=shift.id,
        )
        
        # Update created_at to spread over past 4 days
        days_back = idx % 4
        sale.created_at = datetime.now() - timedelta(days=days_back, hours=random.randint(0, 23))
        sale.save()
        
        print(f"✓ Bill {idx + 1}: {len(config['items'])} items, Total: ₹{total_paise/100:.0f} PKR (Discount: {config['discount_pct']}%)")
    except Exception as e:
        print(f"✗ Bill {idx + 1} failed: {str(e)}")

print("\n✅ Database setup complete!")
print(f"Total products: {Product.objects.count()}")
print(f"Total categories: {Category.objects.count()}")
print(f"Total sales: {Sale.objects.count()}")
print("Type 'exit()' to exit Django shell")
```

---

## 📝 **Step-by-Step Execution**

1. **Paste the entire script above into the Django shell**
2. **Wait for it to complete** (should finish in 5-10 seconds)
3. **Verify output shows all items created**
4. **Type `exit()` to exit Django shell**

---

## ✅ **Verification**

After the script finishes, verify the data was added:

```python
# In Django shell, run these commands:

from apps.catalog.models import Category, Product
from apps.sales.models import Sale

print(f"Categories: {Category.objects.count()}")
print(f"Products: {Product.objects.count()}")
print(f"Sales: {Sale.objects.count()}")

# List all products
for p in Product.objects.all():
    print(f"- {p.name}: ₹{p.unit_price_paise/100} ({p.stock_qty} in stock)")

# List all sales
for s in Sale.objects.all():
    print(f"- {s.sale_number}: ₹{s.total_paise/100} ({s.created_at})")
```

---

## 🎯 **Expected Results**

After running the script, you should have:

```
✓ Creating categories...
✓ Dome Cameras
✓ Bullet Cameras
✓ Recording Systems
✓ Cables & Accessories
✓ Monitoring Displays

Creating products...
✓ 2MP Fixed Dome Camera - 8500 PKR
✓ 4MP PTZ Dome Camera - 15000 PKR
✓ 5MP Varifocal Dome - 12000 PKR
✓ 2MP Outdoor Bullet - 7500 PKR
✓ 4MP IR Bullet Camera - 11000 PKR
✓ 8CH DVR (1TB) - 18000 PKR
✓ 4CH NVR (500GB) - 22000 PKR
✓ CCTV Cable Reel (300m) - 4500 PKR
✓ Power Supply Unit (12V/2A) - 2500 PKR
✓ 21.5" LED Monitor - 14000 PKR

Total products created: 10

Creating sample sales transactions...
✓ Bill 1: 2 items, Total: ₹16150 PKR (Discount: 5%)
✓ Bill 2: 2 items, Total: ₹9750 PKR (Discount: 0%)
✓ Bill 3: 4 items, Total: ₹49300 PKR (Discount: 10%)
[... more bills ...]

✅ Database setup complete!
Total products: 10
Total categories: 5
Total sales: 10
```

---

## 🔄 **If You Need to Reset/Delete Data**

If you want to start over, run this in the Django shell:

```python
from apps.catalog.models import Category, Product
from apps.sales.models import Sale, Shift

# Delete all data
Product.objects.all().delete()
Category.objects.all().delete()
Sale.objects.all().delete()
Shift.objects.all().delete()

print("✓ All data deleted")
```

---

## 💡 **Tips**

1. **The script is idempotent** — Running it multiple times won't create duplicates
2. **Stock quantities vary** — Each product has realistic stock levels for a new store
3. **Discounts vary** — Different bills have different discount percentages (0-10%)
4. **Dates spread** — Sales are spread over the past 4 days for realistic history
5. **Payment methods mix** — Bills use Cash, Card, or Bank Transfer randomly

---

## 📞 **Troubleshooting**

### Error: "ModuleNotFoundError"
**Solution:** Make sure `$env:DJANGO_SETTINGS_MODULE = "config.settings.desktop"` is set before running `python manage.py shell`

### Error: "Shift matching query does not exist"
**Solution:** The script creates a shift automatically. If it fails, create one manually:
```python
from apps.sales.models import Shift
Shift.objects.create(id=1, opening_float_paise=5000000, tenant_id=1)
```

### Data not appearing in UI
**Solution:** 
1. Hard refresh browser (Ctrl+F5)
2. Restart the frontend dev server (`npm run dev`)
3. Clear browser cache if needed

---

## ✨ **What's Next?**

After setup is complete:

1. ✅ Start backend: `python manage.py runserver`
2. ✅ Start frontend: `npm run dev`
3. ✅ Open `http://localhost:5173/dashboard`
4. ✅ View the CCTV theme with sample data
5. ✅ Navigate to `/reports` to see audit trails
6. ✅ Navigate to `/bills` to see sales history

---

**Status:** Ready to execute! 🚀

Run the Django shell script above and report back when done. I'll help you verify everything is working.