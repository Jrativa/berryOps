# ADR-007: Stock ledger with a lot projection, row locks, FIFO within variety + grade

- Status: Accepted
- Implementation status: not implemented. No stock tables, lots or ledger exist; today a harvest is only a
  record of weight. Planned in tasks T2.1-T2.8 (revision `0005_stock`). Pure allocation logic is the first piece.

## Context

Availability must be exact under concurrency: two sales must not both reserve the last 400 lb, and negative stock
must be impossible. Errors must be correctable without rewriting history. Price depends on variety and grade, so
stock is never fungible across them.

## Decision

- **Ledger plus projection.** `stock_movements` is append-only and is the truth (signed `quantity_kg`, source
  reference, reason where required). Each `stock_lots` row carries `on_hand_kg` and `reserved_kg`, updated in the
  same transaction as each movement. Invariant: `on_hand_kg = sum(movements)`, verified by a `verify-stock`
  command and a test.
- **Constraints as the last guard:** `CHECK on_hand >= 0`, `reserved >= 0`, `reserved <= on_hand`; a trigger and
  grants reject UPDATE/DELETE on the ledger.
- **Concurrency:** READ COMMITTED, `SELECT ... FOR UPDATE` on the aggregate root first (sale, count) and then on
  lots **ordered by id** (no deadlocks from inconsistent order), `lock_timeout` 5 s -> 503 `RETRY_LATER`. A unique
  key on (source, line, lot, movement type) prevents double deduction.
- **Compensation, never mutation:** mistakes are fixed by `correction` movements or approved `adjustment`s.
- **Allocation** (pure function): candidates are available lots of the line's farm + variety + grade, FIFO by
  harvest date, then receipt date, then code. A user may list preferred lots; the list is strict (no silent
  fallback; 409 `INSUFFICIENT_STOCK_IN_SELECTED_LOTS`), and any difference from FIFO is audited. FEFO is not used
  (no expiry data).
- **Lot identity** = farm + variety + grade + harvest date (+ plot); a lot never changes variety or grade.
- Weights are `NUMERIC(14,3)` kg; lb is an input/display unit only (conversion and rounding rule: [ADR-011](011-decimal-money-and-units.md); ADR-013 not yet written).

## Alternatives considered

- **Quantity column only (no ledger).** Pros: simplest. Cons: no history, no audit, errors overwrite truth. Rejected.
- **Ledger only, compute availability by `SUM`.** Pros: one source of truth, no drift. Cons: availability is O(n)
  and there is no single row to lock. Rejected for locking and speed; the projection plus the verifier gets both.
- **SERIALIZABLE isolation with retries.** Pros: no explicit locks. Cons: retry loops in every command. Rejected.
- **Optimistic version column on lots.** Pros: no waiting. Cons: contention on hot lots turns into client retries.
  Rejected for the expected low volume; pessimistic locks are simpler to reason about.
- **Mixing grades in one lot.** Rejected: prices differ per variety and grade.

## Consequences

- Two representations must agree; the invariant test and trigger are not optional.
- Harvest edit/delete semantics change: quantity edits post corrections; identity edits are allowed only on unused
  lots; DELETE becomes a void (`HARVEST_LOCKED`, `INSUFFICIENT_STOCK`).
- Stock fragments across variety x grade buckets (expected; the availability matrix keeps it readable).
- Reclassifying stock after harvest (regrade) and transfers between farms are deferred.
