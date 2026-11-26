# Technical debt

Deferred work and known oddities. Each item says why it is not done now. Items fixed by the foundation work are
not listed; the legacy list in [DESARROLLO.md](DESARROLLO.md) tracks the older findings until it is replaced.

## Deferred on purpose (from the plan, section 11)

| Item | Why deferred |
|---|---|
| Login rate limiting | Needs a store and a policy; security hardening (T0.7) covers the cheaper fixes first |
| MFA and IP allowlisting for the platform superuser | Superuser does not exist yet; CLI provisioning, read-only access, short TTL and audit are the first mitigations (ADR-006) |
| Decimal strings in legacy endpoints | Legacy inventory computes in `Decimal` but still emits JSON numbers (`JsonDecimal`, ADR-011); new endpoints will use strings. Changing the legacy shape breaks the frontend contract for no stock benefit |
| Rename `inventory` -> `production` | Pure churn across backend, routes and frontend; do it when the stock module makes the name misleading in practice (ADR-001) |
| Unused frontend dependencies; tracked `apps/frontend/.removed/`; unanchored/wrong `.gitignore` pattern | Cleanup, no behavior change; see "Found since" for the details |
| TypeScript strict mode | Needs a sweep of existing code; not a prerequisite for stock or sales |
| Dark mode | Design work, no requirement yet |
| Idempotency key cleanup job | Table does not exist yet (ADR-009); volume is low |
| Partial dispatch | More states and allocation rules; full dispatch covers the stated need (ADR-010) |
| Reservation expiry | Needs a timer or job; the reservation age is displayed instead |
| Transfers between farms; regrade (reclassify grade after harvest) | No requirement yet; workaround for a misgraded lot is discard plus opening balance, audited |
| Refunds | Money movements outside the system by decision (Q8) |
| Farm-scoped memberships | Memberships cover the whole organization (O3) |
| Variety merge tool | Near-duplicates are reported, not merged; revisit if the catalog gets messy |
| Optional variety on plants | Out of scope (O2) |
| CI | The local PostgreSQL test DB is enough for now (Q15); the `pg` tests skip with a warning without a database, which CI must turn into a failure |
| Refresh `graphify-out` | Regenerable artifact, ignored by git |
| Tokens in `sessionStorage` | Reachable by XSS; the alternative (httpOnly cookies) changes the auth flow and CORS. Mitigated by short access tokens and refresh rotation with reuse detection. Related: when the token refresh fails the client clears `sessionStorage` and redirects, but the zustand `authStore` is not updated (the full page load resets it) |
| Translate or replace the legacy Spanish docs | Replaced area by area (see [README.md](README.md)) |

## Found since

| Item | Detail | Why not fixed here |
|---|---|---|
| `apps/backend/requirements.txt` is UTF-16 | Git reports it as a binary file (`Bin ... bytes` in diffs) and text tools struggle with it. `requirements-dev.txt` is plain text | Dependency files are outside the docs task; convert in a separate, reviewed change |
| `.gitignore` oddities | `frontend/.removed/`, `backend/bin/`, `backend/lib/`, `backend/include/` are anchored to the repository root, but the folders live under `apps/`, so they do not match (`apps/frontend/.removed/` is tracked, 60+ files). `.claude` ignores the whole folder, including project skills. `.env.*` also ignores `.env.test`, which is intended | The file is out of scope for the docs task |
| Virtual environment recreated | `apps/backend/venv` was recreated (`pyvenv.cfg` is git-ignored); the venv is local, so a stale one should be recreated from `requirements.txt` | One-off; keep the setup steps in DESARROLLO.md current |
| Placeholder files | `apps/backend/vscode.config.json` is empty; `features/sales/` and `features/expenses/` contain only empty files (`expenses` is to be deleted, `sales` built) | Removed with their feature work |
| Free-text `plots.variety` | Ambiguous values; migrated through a reviewed CSV (ADR-002) | Part of task T1.4 |
| `plots.plant_count` is client-writable | `PlotCreate`/`PlotUpdate` accept `plant_count`, while the plant grid keeps the counter in sync (`plants/generate`); the two can disagree | Needs a decision on whether the counter becomes derived; not part of the numeric work |
| Frontend lint scans `apps/frontend/.removed/` | `pnpm lint` reports errors only under that unused-code folder; the ESLint config should ignore `.removed` (or the folder be deleted) | Config change outside the docs task |
| Near-duplicate noise in `report-varieties` | The edit-distance threshold (<= 2) can pair distinct short names, so the "possible duplicates" list needs human review | Acceptable for a report that feeds a reviewed CSV (T1.4) |
| Numeric core not wired | `core/units.py`, `core/money.py` and `core/domain/grade.py` (T0.5) are covered by tests but not used by routes or schemas; inventory columns are still `Numeric(10,2)`, `(12,2)` and `(14,2)` rather than the planned `NUMERIC(14,3)` kg | Arrives with stock and sales (ADR-011) |
| Bootstrap CLI is interim | `bootstrap` creates only the admin role and user; organization, farm and membership creation and `grant-superuser` do not exist | Need the tenancy tables (T1.x, ADR-006) |
