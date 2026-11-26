# Architecture Decision Records

An ADR records one decision: why it was taken, what else was possible, and what it costs. Detailed designs (tables,
endpoints, task order) live in [../plan/foundations-inventory-sales.md](../plan/foundations-inventory-sales.md);
an ADR does not repeat them.

## Index

| ADR | Decision | Status | Implementation status |
|---|---|---|---|
| [001](001-modular-monolith-hexagonal.md) | Modular monolith, hexagonal features, stock public facade | Accepted | Partly: hexagonal features and ports exist; stock module, facade and architecture test do not |
| [002](002-alembic-migrations.md) | Alembic expand/contract, no `create_all`, dev DB protection | Accepted | Baseline implemented; later revisions and the reviewed variety map not yet (`report-varieties` report exists) |
| [003](003-unit-of-work.md) | One transaction per command (unit of work) | Accepted | Implemented (tenant context, audit and idempotency hooks are not) |
| [004](004-multi-tenancy.md) | Shared schema, composite FKs, header-selected organization verified by membership | Accepted | Not implemented |
| [005](005-row-level-security.md) | PostgreSQL RLS as defense in depth | Accepted | Not implemented |
| [006](006-roles-financial-access-superuser.md) | Static roles, `financial_access` flag, read-only platform superuser | Accepted | Partly: anonymous bootstrap removed (admin-only endpoints, first admin by CLI `bootstrap`); `financial_access`, memberships, superuser and `grant-superuser` not yet (today: global roles + `ADMIN_ROLE_NAMES`) |
| [007](007-stock-ledger-projection.md) | Stock ledger plus lot projection, row locks, FIFO within variety + grade | Accepted | Not implemented |
| [008](008-entitlements.md) | Entitlements extension point | Accepted (documented only) | Not implemented, by design |
| [009](009-idempotency-keys.md) | Idempotency keys inside the business transaction | Accepted | Not implemented |
| [010](010-sales-lifecycle.md) | Sales lifecycle ("cargamento" = dispatched sale), reservations, payments, returns | Accepted | Not implemented |
| [011](011-decimal-money-and-units.md) | Decimal for money and quantities, one rounding policy, kg canonical, COP scale | Accepted | Partly: core modules and legacy inventory done; sales, stock and decimal-string API not yet |

The plan's list also names ADR-012 (variety catalog, grade enum) and ADR-013 (units: entered-unit pricing, per-user
preference). They are not written yet; they will be added when their code lands (T1.4 and the stock and sales work).
ADR-011 already holds the weight conversion and rounding rule.

Status values: Proposed, Accepted, Superseded by ADR-NNN. "Accepted" means the decision is taken, not that it is
built: the **Implementation status** line says what exists. Update that line when the code changes; do not rewrite
history in Context or Decision (supersede instead).

## Template

```markdown
# ADR-NNN: Title

- Status: Proposed | Accepted | Superseded by ADR-NNN
- Implementation status: not implemented | partly (what) | implemented (where)

## Context
The forces: requirements, constraints, what is wrong today.

## Decision
What we do, stated so that it can be checked in code.

## Alternatives considered
- Option A: pros / cons, why not.
- Option B: pros / cons, why not.

## Consequences
What gets easier, what gets harder, risks, what must be tested.
```
