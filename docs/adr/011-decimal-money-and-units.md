# ADR-011: Decimal for money and quantities, one rounding policy, kg canonical

- Status: Accepted
- Implementation status: partly. Implemented: the pure core modules `core/decimal_input.py`, `core/units.py`,
  `core/money.py`, `core/domain/grade.py` (T0.5, tested in `tests/test_core_units_money_grade.py`, not yet used by
  routes or input schemas); legacy inventory computes in `Decimal` and serializes through the single
  `JsonDecimal` type in `features/inventory/domain/schemas.py` (T0.6, `tests/test_inventory_decimal.py`).
  Not implemented: stock and sales using the core, decimal-string fields in the API, `NUMERIC(14,3)` kg columns
  (inventory columns are still `Numeric(10,2)`, `(12,2)`, `(14,2)`), the per-organization `currency_scale` column,
  the per-user unit preference.

## Context

The business sells fruit by weight in kg or lb and prices it per entered unit, often in COP (no minor units).
Totals, averages and per-kg costs must be reproducible to the last digit: two screens or a CSV and a report must
not disagree by a unit. Binary floats cannot represent 0.1 or a pound exactly, and the legacy inventory code used
floats end to end. A lb to kg conversion also rounds, so without one policy each module would round at a
different step and the errors would accumulate.

## Decision

- **Decimal everywhere** for money and quantities inside the backend. The pure helpers accept only finite
  `Decimal` (`require_decimal`): `float`, `int` and `str` are rejected with `TypeError`, so a float cannot reach
  the arithmetic by accident. Parsing external input (JSON) happens once, at the boundary.
- **Rounding policy.** Convert or multiply once with the exact constant, then quantize once with
  `ROUND_HALF_UP`. Results are never converted in chains (lb -> kg -> lb); always convert from the value as
  entered. Intermediate values stay exact.
- **kg is the canonical stored unit**, 3 decimals (`to_kg`, maximum error 0.5 g). lb is an input and display
  unit only: 1 lb = 0.45359237 kg exactly, display default is 1 decimal for lb and 3 for kg (`from_kg`, display
  only, never stored). Negative weights are rejected.
- **Money scale** is the organization's `currency_scale`, an integer 0..3 (COP = 0, EUR = 2); `quantize_money`,
  `line_total` (quantity x unit price in the line's entered unit, so no conversion) and `price_per_unit` round
  once to that scale. Column bounds (`NUMERIC(14,3)` weights, `NUMERIC(16,2)` money) are enforced by the input
  schemas, not by the helpers.
- **Wire format.** Legacy inventory endpoints keep **JSON numbers** and their existing shape: `JsonDecimal`
  turns an incoming float into `Decimal(str(x))` (never `Decimal(0.1)`) and serializes back to a JSON number.
  The summary ratios are rounded `ROUND_HALF_UP` to 2 decimals at the output only. CSV exports are unchanged.
  New endpoints (stock, sales) will use **decimal strings**.
- **Grade** (`premium`, `standard`, `processing`) is a fixed enum in `core/domain/grade.py` whose values match the
  DB CHECK and the inventory schemas.

## Alternatives considered

- **Keep float.** Pros: no change, matches the current JSON. Cons: representation error (0.1 + 0.2), totals that
  differ between layers, no defined rounding. Rejected.
- **Integer minor units (cents, grams).** Pros: exact and fast, no rounding type to misuse. Cons: the scale
  differs per currency (COP 0, EUR 2), lb conversion to integer grams still needs a rounding rule, prices per kg
  with fractions need a second scale, and every API and UI value needs conversion. Rejected: the same rounding
  policy is still needed, with more conversion code.
- **String-only API, including legacy endpoints.** Pros: no precision loss on the wire. Cons: breaks the
  existing frontend contract for no stock benefit. Deferred for legacy endpoints (see
  [../tech-debt.md](../tech-debt.md)); adopted for new ones.

## Consequences

- Inputs to the core must be built as `Decimal` by the boundary; passing a float is an error, not a coercion.
- Mixing legacy JSON numbers and new decimal strings means two serializations until the legacy endpoints change.
- Because rounding is applied once at the end, tests must pin half-up cases (for example 0.005 and the lb
  boundary values) and assert that no chain conversion happens.
- Storing kg with 3 decimals needs a column widening migration (expand/contract, ADR-002) when stock lands.
- This ADR covers the weight conversion rule of the plan's ADR-013 (units). The entered-unit pricing and the
  per-user unit preference remain for ADR-013.
