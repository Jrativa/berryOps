# ADR-005: PostgreSQL row-level security as defense in depth

- Status: Accepted
- Implementation status: not implemented. Planned as revision `0007_rls_and_grants` (task T1.8, isolated so it can
  slip). Depends on ADR-004. Today there is a single database role and no RLS.

## Context

Application-level filtering (ADR-004) is the primary isolation mechanism, but one missing `WHERE organization_id`
in any future query would leak data. We want the database to refuse such a query.

## Decision

- Two roles: `arandanos_owner` (schema owner, used by Alembic and the CLI) and `arandanos_app` (NOSUPERUSER,
  NOBYPASSRLS, not an owner, no UPDATE/DELETE on ledger and audit tables). The API connects as `arandanos_app`.
- `ENABLE` and `FORCE ROW LEVEL SECURITY` on every tenant table with the policy
  `organization_id = current_setting('app.org_id', true)::uuid`. If the setting is missing the comparison is NULL,
  so the policy **fails closed**.
- The context is set at the start of the unit of work (ADR-003) with `set_config('app.org_id', ..., true)`, i.e.
  **transaction-local**, so it cannot leak between requests that reuse a pooled connection.
- No RLS on `users`, `user_sessions`, `organizations`; `memberships` allows `org = app.org_id OR user_id = app.user_id`
  (needed to resolve membership before the organization is known).
- The platform superuser uses the same role and the same mechanism: it sees one organization per transaction (ADR-006).

## Alternatives considered

- **Application filtering only.** Pros: no database setup. Cons: any bug is a data leak. Kept as primary, not sole.
- **Session-level `SET` instead of `set_config(..., true)`.** Pros: set once per connection. Cons: leaks to the next
  request on a pooled connection. Rejected.
- **Superuser or table-owner connection for the app.** Pros: no grants to manage. Cons: owners and superusers bypass
  RLS unless forced; the app would run with schema-altering rights. Rejected.
- **Views per tenant.** Pros: no policy syntax. Cons: view explosion, awkward writes. Rejected.

## Consequences

- Needs a second connection role and a password supplied outside the repository; tests must run as the app role
  to be meaningful.
- Policies add a small cost to every query and make failures more confusing ("0 rows" instead of an error); tests
  must cover "no context -> nothing visible" and "cross-tenant insert -> rejected".
- Migrations and the CLI use the owner role, so RLS never blocks a schema change.
