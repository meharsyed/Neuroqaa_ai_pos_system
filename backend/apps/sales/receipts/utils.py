"""
Utility functions for receipt generation
"""

from decimal import Decimal


def format_qty(qty) -> str:
    """Convert Decimal quantity to formatted string without trailing zeros.

    Examples:
        Decimal('4.000') → '4'
        Decimal('2.500') → '2.5'
        Decimal('1.0') → '1'
    """
    d = Decimal(str(qty)).normalize()
    if d == d.to_integral_value():
        d = d.quantize(Decimal(1))
    return format(d, "f")


def num_to_words_pkr(paise: int) -> str:
    """
    Convert paise to words in Pakistani Rupees format.

    Args:
        paise: Amount in paise (100 paise = 1 rupee)

    Returns:
        Formatted text like "One hundred forty-seven thousand nine hundred eleven rupees and forty paise only"

    Examples:
        >>> num_to_words_pkr(0)
        'Zero paise only'
        >>> num_to_words_pkr(100)
        'One rupee only'
        >>> num_to_words_pkr(147911_40)
        'One hundred forty-seven thousand nine hundred eleven rupees and forty paise only'
    """

    if paise == 0:
        return "Zero paise only"

    # Split into rupees and paise
    rupees = paise // 100
    remaining_paise = paise % 100

    ones = [
        "", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine"
    ]
    teens = [
        "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen",
        "sixteen", "seventeen", "eighteen", "nineteen"
    ]
    tens = [
        "", "", "twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety"
    ]

    def _words_under_thousand(num: int) -> str:
        """Convert number < 1000 to words"""
        if num == 0:
            return ""
        elif num < 10:
            return ones[num]
        elif num < 20:
            return teens[num - 10]
        elif num < 100:
            return tens[num // 10] + (" " + ones[num % 10] if num % 10 else "")
        else:  # 100-999
            hundred_part = ones[num // 100] + " hundred"
            remainder = num % 100
            if remainder == 0:
                return hundred_part
            return hundred_part + " " + _words_under_thousand(remainder)

    def _words_from_rupees(num: int) -> str:
        """Convert rupees amount to words, handling thousands and lakhs"""
        if num == 0:
            return ""
        elif num < 1000:
            return _words_under_thousand(num)
        elif num < 100_000:  # 1,000 to 99,999
            thousands = num // 1000
            remainder = num % 1000
            thousands_part = _words_under_thousand(thousands) + " thousand"
            if remainder == 0:
                return thousands_part
            return thousands_part + " " + _words_under_thousand(remainder)
        else:  # 100,000+ (lakhs)
            lakhs = num // 100_000
            remainder = num % 100_000
            lakhs_part = _words_under_thousand(lakhs) + " lakh"
            if remainder == 0:
                return lakhs_part
            return lakhs_part + " " + _words_from_rupees(remainder)

    # Build final string
    parts = []

    if rupees > 0:
        rupees_text = _words_from_rupees(rupees)
        rupees_text = rupees_text.capitalize()
        rupee_word = "rupee" if rupees == 1 else "rupees"
        parts.append(f"{rupees_text} {rupee_word}")

    if remaining_paise > 0:
        if rupees > 0:
            parts.append("and")
        paise_text = _words_under_thousand(remaining_paise)
        paise_text = paise_text.capitalize() if not parts else paise_text
        paise_word = "paisa" if remaining_paise == 1 else "paise"
        parts.append(f"{paise_text} {paise_word}")

    result = " ".join(parts)
    return result + " only"


def format_money(paise: int, include_symbol: bool = True) -> str:
    """Format paise as rupees with proper grouping and decimals."""
    rupees = paise / 100
    formatted = f"{rupees:,.2f}"
    if include_symbol:
        return f"Rs {formatted}"
    return formatted


def format_money_simple(paise: int) -> str:
    """Format paise without symbol (for use in tables where symbol appears separately)."""
    rupees = paise / 100
    return f"{rupees:,.2f}"