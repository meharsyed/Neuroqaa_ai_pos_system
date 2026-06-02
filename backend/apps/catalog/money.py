from decimal import Decimal


class Money:
    """
    Wraps an integer paise value (1 Rs = 100 paise).
    All price fields in the DB are BigIntegerField paise — never float.
    Use this class for formatting and arithmetic only; persist the raw .paise int.
    """

    SYMBOL = "Rs."

    def __init__(self, paise: int):
        self._paise = int(paise)

    @classmethod
    def from_rupees(cls, rupees) -> "Money":
        """Safe conversion from str/int/float/Decimal rupees to paise."""
        return cls(round(Decimal(str(rupees)) * 100))

    @property
    def paise(self) -> int:
        return self._paise

    @property
    def rupees(self) -> Decimal:
        return Decimal(self._paise) / 100

    def __str__(self) -> str:
        return f"{self.SYMBOL} {self.rupees:,.2f}"

    def __repr__(self) -> str:
        return f"Money({self._paise})"

    def __add__(self, other: "Money") -> "Money":
        return Money(self._paise + other._paise)

    def __sub__(self, other: "Money") -> "Money":
        return Money(self._paise - other._paise)

    def __mul__(self, factor) -> "Money":
        return Money(round(self._paise * factor))

    def __eq__(self, other) -> bool:
        return isinstance(other, Money) and self._paise == other._paise

    def __lt__(self, other: "Money") -> bool:
        return self._paise < other._paise

    def __le__(self, other: "Money") -> bool:
        return self._paise <= other._paise

    def __gt__(self, other: "Money") -> bool:
        return self._paise > other._paise

    def __ge__(self, other: "Money") -> bool:
        return self._paise >= other._paise

    def __bool__(self) -> bool:
        return self._paise != 0

    def __hash__(self) -> int:
        return hash(self._paise)
