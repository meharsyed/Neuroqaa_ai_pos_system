"""
Receipt theme and styling - Speed Tech Solutions brand colors
All colours use HSL/hex pairs from the UI_UX_REVAMP_SPEC
"""

from reportlab.lib import colors

class Theme:
    """Brand colour palette for receipts"""

    # Brand green (chrome) - from logo
    GREEN_950 = colors.HexColor("#0C1A12")
    GREEN_900 = colors.HexColor("#12281C")
    GREEN_800 = colors.HexColor("#1A3A28")
    GREEN_700 = colors.HexColor("#234B34")
    GREEN_600 = colors.HexColor("#2E5F42")
    GREEN_500 = colors.HexColor("#3C7854")

    # Brand teal (accent) - from letterhead
    TEAL_900 = colors.HexColor("#0B3B40")
    TEAL_800 = colors.HexColor("#0E5257")
    TEAL_700 = colors.HexColor("#0F6E70")
    TEAL_600 = colors.HexColor("#12898A")
    TEAL_500 = colors.HexColor("#17A8A3")
    TEAL_400 = colors.HexColor("#3DC2BC")
    TEAL_100 = colors.HexColor("#D6F2F0")
    TEAL_50 = colors.HexColor("#EEFAF9")

    # Neutral ramp (canvas)
    NEUTRAL_0 = colors.HexColor("#FFFFFF")
    NEUTRAL_50 = colors.HexColor("#F7FAFA")
    NEUTRAL_100 = colors.HexColor("#EFF3F4")
    NEUTRAL_200 = colors.HexColor("#DFE6E8")
    NEUTRAL_300 = colors.HexColor("#C3CDD1")
    NEUTRAL_400 = colors.HexColor("#92A1A7")
    NEUTRAL_500 = colors.HexColor("#64757D")
    NEUTRAL_600 = colors.HexColor("#47585F")
    NEUTRAL_700 = colors.HexColor("#2C3A41")
    NEUTRAL_800 = colors.HexColor("#1D272C")
    NEUTRAL_900 = colors.HexColor("#131B1F")

    # Semantic
    SUCCESS = colors.HexColor("#1F9D57")
    WARNING = colors.HexColor("#B45309")
    DANGER = colors.HexColor("#B42318")
    INFO = TEAL_600

    # Shortcuts for common uses
    PRIMARY_HEADER = GREEN_800
    PRIMARY_HIGHLIGHT = GREEN_600
    ACCENT_RULE = TEAL_600
    ACCENT_SOFT_BG = TEAL_50

    INK = NEUTRAL_800
    INK_MUTED = NEUTRAL_500
    RULE = NEUTRAL_200
    ZEBRA_BG = TEAL_50


THEME = Theme()