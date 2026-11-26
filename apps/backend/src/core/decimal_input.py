"""Shared boundary check for the pure numeric core modules."""
from decimal import Decimal


def require_decimal(value: object, name: str) -> Decimal:
    """Accept only finite Decimals. float/int/str are rejected on purpose:
    binary floats cannot represent money or weights exactly.
    Negative zero is normalised to zero."""
    if not isinstance(value, Decimal):
        raise TypeError(f"{name} must be a Decimal, got {type(value).__name__}")
    if not value.is_finite():
        raise ValueError(f"{name} must be finite")
    return value.copy_abs() if value == 0 else value
