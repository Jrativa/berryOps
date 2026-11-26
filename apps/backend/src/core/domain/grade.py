"""Quality grade: a first-class dimension of stock and sales.
Values match the DB CHECK and inventory schemas exactly."""
from enum import Enum


class Grade(str, Enum):
    PREMIUM = "premium"
    STANDARD = "standard"
    PROCESSING = "processing"


def parse_grade(value: object) -> Grade:
    try:
        return Grade(value)
    except ValueError:
        raise ValueError(f"unknown grade: {value!r}") from None
