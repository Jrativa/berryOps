# ADR-002: Alembic migrations (expand/contract), no `create_all`, dev DB protection

- Status: Accepted
- Implementation status: partly. Implemented: Alembic in `apps/backend/migrations/`, revision `0001_baseline` (the 8
  existing tables), no `create_all` or `init_db` at startup (asserted by `tests/test_wiring.py`), upgrade/downgrade
  and model-drift tests (`tests/test_migrations.py`), the `*_test` guard (`tests/pg_guard.py`), the runbook
  ([../operations/migrations.md](../operations/migrations.md)). `report-varieties` (a read-only CLI report of `plots.variety`) exists. Not implemented: later revisions (tenancy,
  stock, sales) and the reviewed variety-map step that uses the report.

## Context

Until now the schema came from `Base.metadata.create_all` at startup. Besides making changes untracked, it hid a
bug: two `Base` objects existed (different import paths), so `create_all` created nothing for some models. The
development database holds real data that must not be lost, while the next steps (multi-tenancy, stock) change
many tables, including the data of existing rows.

## Decision

- The application never changes the schema. Every change is an Alembic revision, run by a person or CI, never at
  startup. There is one `Base`.
- Changes that touch data use **expand / backfill / contract** in separate revisions: add the new structure,
  copy data, remove the old structure only in a later revision. Each step is idempotent (safe to re-run after a
  crash).
- Every revision has a tested `downgrade`; tests run `upgrade -> downgrade -> upgrade` plus a "no drift between
  models and migrations" check on a dedicated database.
- Dev DB protection: tests refuse any database whose name does not end in `_test` or that equals the `.env`
  database; the dev database is adopted once with `alembic stamp 0001_baseline` after a verified `pg_dump -Fc`
  backup and explicit approval. A plain `upgrade head` on it fails on purpose ("relation already exists").
- Ambiguous free-text data (planned: `plots.variety` -> varieties) is migrated from a reviewed CSV; the migration
  aborts if ambiguity remains and no map is supplied.

## Alternatives considered

- **Keep `create_all`.** Pros: zero setup. Cons: cannot alter existing tables, no history, no rollback, and it
  silently did nothing here. Rejected.
- **Hand-written SQL scripts.** Pros: full control. Cons: no ordering/versioning tool, no autogenerate diff, no
  drift test. Rejected.
- **Autogenerate and apply blindly.** Pros: fast. Cons: autogenerate cannot express data backfills and can drop
  columns. Rejected: output is a draft that is reviewed and named explicitly.
- **Single big revision for the whole plan.** Pros: fewer files. Cons: one failure rolls back everything and
  nothing is verifiable in small units. Rejected: one revision per concern.

## Consequences

- A new environment needs `alembic upgrade head` before the API works; forgetting it gives an "undefined table"
  error rather than silent creation.
- Contract steps (dropping `plots.variety`, `roles`, ...) are deliberately postponed, so old and new code can coexist.
- Writing a revision costs more than editing a model, but every change is reproducible and reviewable.
- The guard protects against mistakes, not against someone who edits the guard; the backup remains the real safety net.
