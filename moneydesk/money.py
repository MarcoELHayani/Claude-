"""Money maths. Everything goes through Decimal; never float, never mental arithmetic."""
from collections import defaultdict
from decimal import Decimal, ROUND_HALF_UP

CENT = Decimal("0.01")

# Months per billing cycle, used to normalise every subscription to a monthly cost.
CYCLE_MONTHS = {
    "Monthly": Decimal(1),
    "Yearly": Decimal(12),
    "Weekly": Decimal(12) / Decimal(52),
}


def dec(value) -> Decimal:
    """Parse '£1,090.50', '1.090,50' is NOT supported on purpose: amounts must be normalised first."""
    if isinstance(value, Decimal):
        return value
    if isinstance(value, float):
        value = repr(value)
    text = str(value).strip().replace(",", "")
    for symbol in "£€$ ":
        text = text.replace(symbol, "")
    return Decimal(text)


def money(value) -> Decimal:
    return dec(value).quantize(CENT, rounding=ROUND_HALF_UP)


def monthly_cost(amount, cycle: str):
    """Monthly equivalent of a recurring charge. Usage-billed services return None (no fixed cost)."""
    months = CYCLE_MONTHS.get(cycle)
    if months is None:
        return None
    return money(dec(amount) / months)


def totals_by_currency(rows, amount_key="amount", currency_key="currency") -> dict:
    """Sum per currency. Currencies are never converted or mixed."""
    totals = defaultdict(Decimal)
    for row in rows:
        if row.get(amount_key) in (None, ""):
            continue
        totals[row[currency_key]] += dec(row[amount_key])
    return {cur: money(total) for cur, total in sorted(totals.items())}


SYMBOLS = {"GBP": "£", "EUR": "€", "USD": "$"}


def fmt(amount, currency: str) -> str:
    return f"{SYMBOLS.get(currency, currency + ' ')}{money(amount):,}"


def fmt_totals(totals: dict) -> str:
    return " + ".join(fmt(v, c) for c, v in totals.items()) or "nothing"
