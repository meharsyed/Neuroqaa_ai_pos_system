"""
Professional Receipt Generation System
Consolidated thermal and document renderers sharing unified data context.
"""

from .context import build_receipt_context, ReceiptContext
from .theme import THEME
from .utils import num_to_words_pkr


def render_text_receipt(sale) -> str:
    """Render plaintext ESC/POS-compatible thermal receipt."""
    from apps.config.utils import get_all_settings
    shop_settings = get_all_settings()
    ctx = build_receipt_context(sale, shop_settings)
    from .thermal import render_thermal_text
    return render_thermal_text(ctx, width_mm=80)


def render_pdf_receipt(sale) -> bytes:
    """Render 80mm thermal-format PDF (default for POS)."""
    from apps.config.utils import get_all_settings
    shop_settings = get_all_settings()
    ctx = build_receipt_context(sale, shop_settings)
    from . import thermal_pdf
    return thermal_pdf.render(ctx, width_mm=80)


def render_pdf_invoice(sale) -> bytes:
    """Render full-page A4 professional invoice."""
    from apps.config.utils import get_all_settings
    shop_settings = get_all_settings()
    ctx = build_receipt_context(sale, shop_settings)
    from . import document
    return document.render(ctx, pagesize="a4")


def render_html_receipt(sale, format_name: str = "a4") -> str:
    """Render HTML receipt for browser printing."""
    from apps.config.utils import get_all_settings
    shop_settings = get_all_settings()
    ctx = build_receipt_context(sale, shop_settings)
    from . import html
    return html.render(ctx, format_name=format_name)


def print_receipt_network(sale) -> bool:
    """Send receipt to network thermal printer via ESC/POS."""
    try:
        from escpos.network import Network
        from apps.config.utils import get_setting

        printer_ip = get_setting("thermal_printer_ip", "")
        printer_port = int(get_setting("thermal_printer_port", "9100"))

        if not printer_ip:
            raise ValueError("Printer IP not configured")

        printer = Network(printer_ip, port=printer_port)

        # Get thermal text and send
        text = render_text_receipt(sale)
        printer.text(text)
        printer.cut()
        printer.close()
        return True
    except ImportError:
        # python-escpos not installed
        raise ImportError("python-escpos is not installed. Install with: pip install python-escpos")
    except Exception as e:
        raise Exception(f"Printer error: {str(e)}")


__all__ = [
    "build_receipt_context",
    "ReceiptContext",
    "THEME",
    "render_text_receipt",
    "render_pdf_receipt",
    "render_pdf_invoice",
    "render_html_receipt",
    "print_receipt_network",
    "num_to_words_pkr",
]