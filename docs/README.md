# Documentation map

New documents are written in English. The legacy Spanish documents are replaced one area at a time; until then
they stay in place with their stale facts corrected.

| Document | Covers | Status |
|---|---|---|
| [GLOSSARY.md](GLOSSARY.md) | Domain terms (English with the Spanish UI term), marked implemented / planned | current |
| [adr/](adr/README.md) | Architecture Decision Records: index, template, ADR-001 to ADR-011 | current |
| [operations/migrations.md](operations/migrations.md) | Alembic runbook: new DB, adopting the dev DB, rollback, rules for writing migrations | current |
| [plan/foundations-inventory-sales.md](plan/foundations-inventory-sales.md) | Revision 3 plan: tenancy, stock, sales, task breakdown. A proposal; the ADRs record the decisions | current (proposal) |
| [tech-debt.md](tech-debt.md) | Deferred work and known oddities, each with the reason it is deferred | current |
| [DESARROLLO.md](DESARROLLO.md) | Setup, environment variables, running tests, PostgreSQL test DB, tech-debt list | legacy (Spanish), partly updated |
| [ARQUITECTURA.md](ARQUITECTURA.md) | Overview of backend and frontend architecture | legacy (Spanish), to be replaced |
| [BACKEND.md](BACKEND.md) | Backend code tree and modules | legacy (Spanish), to be replaced |
| [API.md](API.md) | HTTP API reference | legacy (Spanish), to be replaced |
| [FRONTEND.md](FRONTEND.md) | Frontend design, routes, modules | legacy (Spanish), to be replaced |

Where to find a decision: the ADR index holds the "why"; the plan holds the detailed data model and API contract
for what is not built yet; the legacy documents describe what exists today. Each fact should live in one of
them, not several.
