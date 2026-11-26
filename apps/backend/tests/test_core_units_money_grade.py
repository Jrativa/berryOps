from decimal import Decimal as D

import pytest

from apps.backend.src.core.domain.grade import Grade, parse_grade
from apps.backend.src.core.money import line_total, price_per_unit, quantize_money
from apps.backend.src.core.units import KG_PER_LB, WeightUnit, from_kg, to_kg


def test_lb_constant_exact():
    assert KG_PER_LB == D("0.45359237")


def test_100_lb_is_45_359_kg():
    assert to_kg(D("100"), "lb") == D("45.359")


def test_1_lb_rounds_to_0_454_kg():
    assert to_kg(D("1"), WeightUnit.LB) == D("0.454")


def test_45_359_kg_is_100_0_lb_display():
    assert from_kg(D("45.359"), "lb") == D("100.0")


def test_1_kg_is_2_205_lb_display_with_3_places():
    assert from_kg(D("1"), "lb", places=3) == D("2.205")
    assert from_kg(D("1"), "lb") == D("2.2")


def test_kg_rounds_to_3_places():
    assert to_kg(D("12.3456"), "kg") == D("12.346")
    assert from_kg(D("12.345"), "kg") == D("12.345")


def test_round_trip_within_half_gram():
    for lb in (D("0.1"), D("7.25"), D("100"), D("999.999")):
        assert abs(to_kg(lb, "lb") - lb * KG_PER_LB) <= D("0.0005")


def test_decimal_exactness_three_times_point_one():
    assert to_kg(D("0.1") * 3, "kg") == D("0.300")
    assert line_total(D("3"), D("0.1"), 2) == D("0.30")


def test_zero_and_negative_zero():
    assert to_kg(D("0"), "kg") == 0
    assert str(to_kg(D("-0"), "lb")) == "0.000"
    assert not quantize_money(D("-0.4"), 0).is_signed()


@pytest.mark.parametrize("bad", [1.5, 1, "1", None, D("NaN"), D("Infinity"), D("-Infinity")])
def test_weight_rejects_non_decimal_and_non_finite(bad):
    with pytest.raises((TypeError, ValueError)):
        to_kg(bad, "kg")


def test_weight_rejects_negative_and_unknown_unit():
    with pytest.raises(ValueError):
        to_kg(D("-1"), "kg")
    with pytest.raises(ValueError):
        from_kg(D("-1"), "kg")
    for unit in ("oz", "", None, "KG"):
        with pytest.raises(ValueError):
            to_kg(D("1"), unit)


def test_cop_half_up_edges():
    assert quantize_money(D("1234.5"), 0) == D("1235")
    assert quantize_money(D("1234.49"), 0) == D("1234")
    assert quantize_money(D("0.5"), 0) == D("1")
    assert quantize_money(D("2.5"), 0) == D("3")  # not banker's rounding


def test_eur_half_up():
    assert quantize_money(D("0.125"), 2) == D("0.13")
    assert quantize_money(D("0.124"), 2) == D("0.12")


def test_money_rejects_float_nan_and_bad_scale():
    with pytest.raises(TypeError):
        quantize_money(1.5, 0)
    with pytest.raises(ValueError):
        quantize_money(D("NaN"), 0)
    for scale in (-1, 4, True, "0", None):
        with pytest.raises(ValueError):
            quantize_money(D("1"), scale)


def test_line_total_rounds_once_at_the_end():
    # 3 x 0.3333 = 0.9999 -> 1.00
    assert line_total(D("3"), D("0.3333"), 2) == D("1.00")
    assert line_total(D("10.5"), D("12345.6789"), 0) == D("129630")


def test_line_total_rejects_negative_and_float():
    with pytest.raises(ValueError):
        line_total(D("-1"), D("1"), 0)
    with pytest.raises(ValueError):
        line_total(D("1"), D("-1"), 0)
    with pytest.raises(TypeError):
        line_total(1.0, D("1"), 0)


def test_price_per_unit_kg_and_lb():
    assert price_per_unit(D("10000"), "kg", 0) == D("10000")
    assert price_per_unit(D("10000"), "lb", 0) == D("4536")
    assert price_per_unit(D("10"), "lb", 2) == D("4.54")


def test_large_values_within_column_bounds_are_exact():
    # bounds are enforced by schemas; the math stays exact at NUMERIC limits
    assert to_kg(D("99999999999.999"), "kg") == D("99999999999.999")
    assert line_total(D("99999999999.999"), D("1000.0001"), 2) == D("100000009999999.00")


def test_grade_values_and_parse():
    assert [g.value for g in Grade] == ["premium", "standard", "processing"]
    assert parse_grade("premium") is Grade.PREMIUM
    for bad in ("Premium", "", None, "export"):
        with pytest.raises(ValueError):
            parse_grade(bad)
