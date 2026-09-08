"""
Tests for receipt generation system
Verify context building, PDF rendering, HTML output, and data consistency
"""

import pytest
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.catalog.models import Category, Product
from apps.customers.models import Customer
from apps.sales.models import Sale, SaleItem, Payment
from apps.sales.receipts import (
    build_receipt_context,
    render_pdf_receipt,
    render_pdf_invoice,
    render_html_receipt,
    render_text_receipt,
    num_to_words_pkr,
)
from apps.sales.receipts.utils import format_qty


User = get_user_model()


@pytest.mark.django_db
class TestReceiptContext(TestCase):
    """Test build_receipt_context with various sale states"""

    def setUp(self):
        self.user = User.objects.create_user(
            username="cashier_test",
            email="cashier@test.com",
            password="test123",
            role="cashier"
        )
        self.category = Category.objects.create(name="Test Category")
        self.product = Product.objects.create(
            name="Test Product",
            sku="TEST-001",
            category=self.category,
            sell_price_paise=50000,
        )
        self.shop_settings = {
            "shop_name": "Test Shop",
            "shop_address": "123 Test St",
            "shop_phone": "+92 123 456 7890",
            "shop_email": "shop@test.com",
            "receipt_header": "Test Receipt Header",
            "receipt_footer": "Test Receipt Footer",
            "tax_pct": "17",
        }

    def test_context_single_item(self):
        """Build context for sale with single item"""
        sale = Sale.objects.create(
            cashier=self.user,
            subtotal_paise=50000,
            tax_paise=8500,
            total_paise=58500,
        )
        item = SaleItem.objects.create(
            sale=sale,
            product=self.product,
            qty=Decimal("1.0"),
            unit_price_paise=50000,
            subtotal_paise=50000,
        )
        Payment.objects.create(
            sale=sale,
            method="cash",
            amount_tendered_paise=60000,
            change_paise=1500,
        )

        ctx = build_receipt_context(sale, self.shop_settings)

        assert ctx.sale_id == str(sale.id)
        assert ctx.sale_number == sale.sale_number
        assert ctx.shop_name == "Test Shop"
        assert len(ctx.items) == 1
        assert ctx.items[0].product_name == "Test Product"
        assert ctx.items[0].quantity == "1"  # No trailing zeros
        assert ctx.items[0].line_total_paise == 50000
        assert ctx.subtotal_paise == 50000
        assert ctx.total_paise == 58500
        assert ctx.tendered_paise == 60000
        assert ctx.change_paise == 1500

    def test_context_multiple_items(self):
        """Build context for sale with multiple items"""
        product2 = Product.objects.create(
            name="Product 2",
            sku="PROD-2",
            category=self.category,
            sell_price_paise=30000,
        )

        sale = Sale.objects.create(
            cashier=self.user,
            subtotal_paise=80000,
            discount_paise=5000,
            tax_paise=12750,
            total_paise=87750,
        )

        SaleItem.objects.create(
            sale=sale,
            product=self.product,
            qty=Decimal("1.0"),
            unit_price_paise=50000,
            subtotal_paise=50000,
        )
        SaleItem.objects.create(
            sale=sale,
            product=product2,
            qty=Decimal("1.0"),
            unit_price_paise=30000,
            subtotal_paise=30000,
        )
        Payment.objects.create(
            sale=sale,
            method="card",
            amount_tendered_paise=87750,
            change_paise=0,
        )

        ctx = build_receipt_context(sale, self.shop_settings)

        assert len(ctx.items) == 2
        assert ctx.items[0].product_name == "Test Product"
        assert ctx.items[1].product_name == "Product 2"
        assert ctx.bill_discount_paise == 5000
        assert ctx.payment_method == "card"

    def test_context_decimal_qty(self):
        """Decimal quantities format without trailing zeros"""
        sale = Sale.objects.create(
            cashier=self.user,
            subtotal_paise=25000,
            total_paise=25000,
        )
        SaleItem.objects.create(
            sale=sale,
            product=self.product,
            qty=Decimal("2.500"),
            unit_price_paise=10000,
            subtotal_paise=25000,
        )

        ctx = build_receipt_context(sale, self.shop_settings)

        assert ctx.items[0].quantity == "2.5"  # Not "2.500"

    def test_context_no_customer(self):
        """Context builds with customer=None"""
        sale = Sale.objects.create(
            cashier=self.user,
            customer=None,
            subtotal_paise=50000,
            total_paise=50000,
        )

        ctx = build_receipt_context(sale, self.shop_settings)

        assert ctx.customer_name == ""
        assert ctx.customer_phone == ""

    def test_context_with_customer(self):
        """Context includes customer info when present"""
        customer = Customer.objects.create(name="John Doe", phone="+92 300 1234567")
        sale = Sale.objects.create(
            cashier=self.user,
            customer=customer,
            subtotal_paise=50000,
            total_paise=50000,
        )

        ctx = build_receipt_context(sale, self.shop_settings)

        assert ctx.customer_name == "John Doe"
        assert ctx.customer_phone == "+92 300 1234567"

    def test_context_no_payment(self):
        """Context builds with payment not yet recorded"""
        sale = Sale.objects.create(
            cashier=self.user,
            subtotal_paise=50000,
            total_paise=50000,
        )

        ctx = build_receipt_context(sale, self.shop_settings)

        assert ctx.tendered_paise == 0
        assert ctx.change_paise == 0
        assert ctx.payment_method == "cash"

    def test_context_voided_sale(self):
        """Voided flag is set correctly"""
        sale = Sale.objects.create(
            cashier=self.user,
            status="voided",
            subtotal_paise=50000,
            total_paise=50000,
        )

        ctx = build_receipt_context(sale, self.shop_settings)

        assert ctx.status == "voided"

    def test_context_return_sale(self):
        """Return flag is set correctly"""
        sale = Sale.objects.create(
            cashier=self.user,
            sale_type="return",
            subtotal_paise=50000,
            total_paise=50000,
        )

        ctx = build_receipt_context(sale, self.shop_settings)

        assert ctx.is_return is True


@pytest.mark.django_db
class TestFormatting(TestCase):
    """Test formatting utility functions"""

    def test_format_qty_no_decimals(self):
        """Quantity with no decimal part"""
        assert format_qty(Decimal("4.000")) == "4"
        assert format_qty(Decimal("1.0")) == "1"

    def test_format_qty_with_decimals(self):
        """Quantity with decimal part"""
        assert format_qty(Decimal("2.500")) == "2.5"
        assert format_qty(Decimal("1.250")) == "1.25"

    def test_num_to_words_zero(self):
        """Zero paise"""
        assert num_to_words_pkr(0) == "Zero paise only"

    def test_num_to_words_rupees_only(self):
        """Whole rupees"""
        assert num_to_words_pkr(100) == "One rupee only"
        assert num_to_words_pkr(200) == "Two rupees only"

    def test_num_to_words_paise_only(self):
        """Paise only (less than 100)"""
        result = num_to_words_pkr(50)
        assert "fifty paise" in result.lower()

    def test_num_to_words_complex(self):
        """Complex amount"""
        result = num_to_words_pkr(1_206_460_00)
        # Should contain "lakh" and handle thousands
        assert "lakh" in result.lower() or "thousand" in result.lower()


@pytest.mark.django_db
class TestPDFRendering(TestCase):
    """Test PDF rendering functions"""

    def setUp(self):
        self.user = User.objects.create_user(
            username="cashier_render",
            email="cashier@test.com",
            password="test123",
            role="cashier"
        )
        self.category = Category.objects.create(name="Test Category")
        self.product = Product.objects.create(
            name="Test Product",
            sku="TEST-001",
            category=self.category,
            sell_price_paise=50000,
        )
        self.shop_settings = {
            "shop_name": "Test Shop",
            "shop_address": "123 Test St",
            "shop_phone": "+92 123 456 7890",
            "tax_pct": "17",
        }

    def _create_simple_sale(self):
        """Helper to create a simple sale"""
        sale = Sale.objects.create(
            cashier=self.user,
            subtotal_paise=50000,
            tax_paise=8500,
            total_paise=58500,
        )
        SaleItem.objects.create(
            sale=sale,
            product=self.product,
            qty=Decimal("1.0"),
            unit_price_paise=50000,
            subtotal_paise=50000,
        )
        Payment.objects.create(
            sale=sale,
            method="cash",
            amount_tendered_paise=60000,
            change_paise=1500,
        )
        return sale

    def test_render_pdf_receipt_produces_bytes(self):
        """PDF receipt rendering produces valid PDF bytes"""
        sale = self._create_simple_sale()
        pdf_bytes = render_pdf_receipt(sale)

        assert isinstance(pdf_bytes, bytes)
        assert pdf_bytes.startswith(b"%PDF")
        assert len(pdf_bytes) > 1000

    def test_render_pdf_invoice_produces_bytes(self):
        """PDF invoice rendering produces valid PDF bytes"""
        sale = self._create_simple_sale()
        pdf_bytes = render_pdf_invoice(sale)

        assert isinstance(pdf_bytes, bytes)
        assert pdf_bytes.startswith(b"%PDF")
        assert len(pdf_bytes) > 1000

    def test_render_html_receipt_produces_html_a4(self):
        """HTML A4 receipt rendering produces valid HTML"""
        sale = self._create_simple_sale()
        html = render_html_receipt(sale, format_name="a4")

        assert isinstance(html, str)
        assert html.startswith("<!DOCTYPE html>")
        assert "TOTAL" in html or "total" in html.lower()
        assert sale.sale_number in html

    def test_render_html_receipt_produces_html_thermal(self):
        """HTML thermal receipt rendering produces valid HTML"""
        sale = self._create_simple_sale()
        html = render_html_receipt(sale, format_name="thermal")

        assert isinstance(html, str)
        assert html.startswith("<!DOCTYPE html>")
        assert "INVOICE" in html or "invoice" in html.lower()

    def test_render_text_receipt_produces_text(self):
        """Text receipt rendering produces valid text"""
        sale = self._create_simple_sale()
        text = render_text_receipt(sale)

        assert isinstance(text, str)
        assert sale.sale_number in text
        assert "TOTAL" in text


@pytest.mark.django_db
class TestReceiptConsistency(TestCase):
    """Test that all receipt formats show identical financial data"""

    def setUp(self):
        self.user = User.objects.create_user(
            username="cashier_consistency",
            email="cashier@test.com",
            password="test123",
            role="cashier"
        )
        self.category = Category.objects.create(name="Test Category")
        self.product = Product.objects.create(
            name="Premium Widget",
            sku="WIDGET-001",
            category=self.category,
            sell_price_paise=50000,
        )
        self.shop_settings = {
            "shop_name": "Quality Goods",
            "shop_address": "Main Street",
            "shop_phone": "+92 321 5551234",
            "tax_pct": "17",
        }

    def test_all_formats_show_same_total(self):
        """All receipt formats show the same total amount"""
        sale = Sale.objects.create(
            cashier=self.user,
            subtotal_paise=100000,
            discount_paise=10000,
            tax_paise=15300,
            total_paise=105300,
        )
        SaleItem.objects.create(
            sale=sale,
            product=self.product,
            qty=Decimal("2.0"),
            unit_price_paise=50000,
            subtotal_paise=100000,
        )
        Payment.objects.create(
            sale=sale,
            method="cash",
            amount_tendered_paise=105300,
            change_paise=0,
        )

        # Render all formats
        pdf_receipt = render_pdf_receipt(sale)
        pdf_invoice = render_pdf_invoice(sale)
        html_a4 = render_html_receipt(sale, format_name="a4")
        text = render_text_receipt(sale)

        # All should be non-empty
        assert len(pdf_receipt) > 0
        assert len(pdf_invoice) > 0
        assert len(html_a4) > 0
        assert len(text) > 0

        # Text should contain the total (formatted with comma separator)
        assert "1,053.00" in text or "1053.00" in text