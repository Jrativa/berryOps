"""Money rounding. Amounts are Decimals rounded ROUND_HALF_UP to the
organization's currency_scale (COP = 0, EUR = 2), rounded once at the end of
a computation. Column bounds (NUMERIC(16,2)) are enforced by schemas.

Return-credit remainder logic belongs to the sales domain (T3.1), not here.
"""
from decimal import ROUND_HALF_UP, Decimal

from apps.backend.src.core.decimal_input import require_decimal
from apps.backend.src.core.units import WeightUnit, kg_per_unit

MAX_CURRENCY_SCALE = 3  # matches CHECK scale 0..3


def _step(currency_scale: int) -> Decimal:
    valid = (
        isinstance(currency_scale, int)
        and not isinstance(currency_scale, bool)
        and 0 <= currency_scale <= MAX_CURRENCY_SCALE
    )
    if not valid:
        raise ValueError(f"currency_scale must be an int in 0..{MAX_CURRENCY_SCALE}")
    return Decimal(1).scaleb(-currency_scale)


def quantize_money(amount: Decimal, currency_scale: int) -> Decimal:
    value = require_decimal(amount, "amount")
    rounded = value.quantize(_step(currency_scale), rounding=ROUND_HALF_UP)
    return require_decimal(rounded, "amount")  # normalises negative zero


def line_total(quantity: Decimal, unit_price: Decimal, currency_scale: int) -> Decimal:
    """round(quantity x unit_price). quantity and unit_price are in the line's
    ENTERED unit (price is per that unit), so no conversion is involved."""
    qty = require_decimal(quantity, "quantity")
    price = require_decimal(unit_price, "unit_price")
    if qty < 0 or price < 0:
        raise ValueError("quantity and unit_price must not be negative")
    return quantize_money(qty * price, currency_scale)


def price_per_unit(price_per_kg: Decimal, unit: WeightUnit | str, currency_scale: int) -> Decimal:
    """Report a per-kg price (e.g. average price) per kg or per lb."""
    price = require_decimal(price_per_kg, "price_per_kg")
    return quantize_money(price * kg_per_unit(unit), currency_scale)
