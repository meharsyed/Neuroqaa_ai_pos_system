"""
Urdu on a PDF.

Three things have to happen before Urdu is legible in a ReportLab document,
and skipping any one of them produces something worse than English:

  1. A font with Arabic glyphs. Helvetica has none, so the text comes out as
     empty boxes. Noto Naskh Arabic is bundled beside this file. (Nastaliq is
     the more beautiful Urdu style, but it needs contextual positioning that
     ReportLab cannot do; Naskh is the honest choice here.)
  2. Letter joining. Arabic letters change shape depending on their neighbours.
     Without `arabic_reshaper` every letter is rendered in isolated form —
     readable to nobody.
  3. Direction. The runs have to be reordered right-to-left with `python-bidi`,
     or the words appear backwards.

Everything degrades to None rather than raising: a missing font or an
uninstalled dependency must never take a receipt down with it.
"""

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

ASSETS = Path(__file__).resolve().parent / "assets"
URDU_FONT = "NotoNaskhArabic"
URDU_FONT_BOLD = "NotoNaskhArabic-Bold"

_registered: bool | None = None


def urdu_font_available() -> bool:
    """Register the Urdu faces once, and report whether Urdu can be drawn."""
    global _registered
    if _registered is not None:
        return _registered

    try:
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont

        regular = ASSETS / "NotoNaskhArabic-Regular.ttf"
        bold = ASSETS / "NotoNaskhArabic-Bold.ttf"
        if not regular.exists():
            logger.warning("Urdu font missing at %s — Urdu text will be skipped", regular)
            _registered = False
            return False

        pdfmetrics.registerFont(TTFont(URDU_FONT, str(regular)))
        if bold.exists():
            pdfmetrics.registerFont(TTFont(URDU_FONT_BOLD, str(bold)))
        _registered = True
    except Exception:
        logger.exception("Could not register the Urdu font")
        _registered = False
    return _registered


def shape_urdu(text: str) -> str | None:
    """
    Join the letters and put them in visual right-to-left order.

    Returns None when the text cannot be shaped — the caller should then print
    nothing rather than a line of disconnected, backwards letters.
    """
    if not text or not text.strip():
        return None
    try:
        import arabic_reshaper
        from bidi.algorithm import get_display

        return get_display(arabic_reshaper.reshape(text))
    except ImportError:
        logger.warning(
            "arabic-reshaper / python-bidi are not installed — Urdu text skipped. "
            "pip install -r requirements/base.txt"
        )
        return None
    except Exception:
        logger.exception("Could not shape Urdu text")
        return None


def urdu_ready(text: str) -> str | None:
    """Shaped Urdu for a single line, or None if anything at all is missing."""
    if not urdu_font_available():
        return None
    return shape_urdu(text)


def urdu_lines(text: str, *, font_size: float, max_width: float) -> list[str] | None:
    """
    Break Urdu into display-ready lines, in reading order.

    This exists because of a bug that is easy to ship and hard to spot: shaping
    a whole paragraph and handing it to a renderer to wrap produces lines that
    are individually correct but stacked in the wrong order — the opening
    clause ends up at the bottom of the box. `get_display` reverses the run,
    and the renderer then wraps that reversed run from the top.

    So the wrap has to happen first, in logical order, and each line is
    reordered on its own. Returns None if Urdu cannot be drawn at all.
    """
    if not urdu_font_available():
        return None
    if not text or not text.strip():
        return None

    try:
        import arabic_reshaper
        from bidi.algorithm import get_display
        from reportlab.pdfbase.pdfmetrics import stringWidth
    except ImportError:
        logger.warning(
            "arabic-reshaper / python-bidi are not installed — Urdu text skipped."
        )
        return None

    try:
        # Join the letters first: shaping is contextual within a word, and
        # wrapping only ever happens at spaces, so this is safe to do up front.
        reshaped = arabic_reshaper.reshape(text)

        lines: list[str] = []
        current = ""
        for word in reshaped.split():
            trial = f"{current} {word}".strip()
            if current and stringWidth(trial, URDU_FONT, font_size) > max_width:
                lines.append(current)
                current = word
            else:
                current = trial
        if current:
            lines.append(current)

        # Each line reordered on its own; the list itself stays in reading order.
        return [get_display(line) for line in lines]
    except Exception:
        logger.exception("Could not lay out Urdu text")
        return None
