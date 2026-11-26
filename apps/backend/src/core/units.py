"""Weight units. kg is the canonical storage unit (NUMERIC(14,3)).

Rounding policy: a conversion multiplies/divides by the exact constant and
quantizes ONCE (ROUND_HALF_UP). Results are never converted in chains
(lb -> kg -> lb) because each rounding step would add error; always convert
from the originally entered value. Max error of to_kg is 0.5 g.

Bounds (NUMERIC(14,3)) are enforced by the input schemas, not here.
"""
from decimal import ROUND_HALF_UP, Decimal
from enum import Enum

from apps.backend.src.core.decimal_input import require_decimal

KG_PER_LB = Decimal("0.45359237")  # exact by definition
KG_PLACES = 3
LB_DISPLAY_PLACES = 1


class WeightUnit(str, Enum):
    KG = "kg"
    LB = "lb"


def parse_unit(value: object) -> WeightUnit:
    try:
        return WeightUnit(value)
    except ValueError:
        raise ValueError(f"unknown weight unit: {value!r}") from None


def kg_per_unit(unit: WeightUnit | str) -> Decimal:
    return KG_PER_LB if parse_unit(unit) is WeightUnit.LB else Decimal(1)


def _quantize(value: Decimal, places: int) -> Decimal:
    return value.quantize(Decimal(1).scaleb(-places), rounding=ROUND_HALF_UP)


def _require_weight(value: object, name: str) -> Decimal:
    number = require_decimal(value, name)
    if number < 0:
        raise ValueError(f"{name} must not be negative")
    return number


def to_kg(quantity: Decimal, unit: WeightUnit | str) -> Decimal:
    """Entered quantity -> canonical kg, 3 decimals, rounded once."""
    number = _require_weight(quantity, "quantity")
    return _quantize(number * kg_per_unit(unit), KG_PLACES)


def from_kg(quantity_kg: Decimal, unit: WeightUnit | str, places: int | None = None) -> Decimal:
    """Canonical kg -> display value, rounded once. Display only; never store it.
    Default places: 3 for kg, 1 for lb (plan 3.6)."""
    number = _require_weight(quantity_kg, "quantity_kg")
    is_lb = parse_unit(unit) is WeightUnit.LB
    default = LB_DISPLAY_PLACES if is_lb else KG_PLACES
    return _quantize(number / kg_per_unit(unit), default if places is None else places)
