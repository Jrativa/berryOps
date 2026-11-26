# ADR-004: Multi-tenancy with a shared schema, composite foreign keys and a verified organization header

- Status: Accepted
- Implementation status: not implemented. Today every plot has an `owner_id` and the service filters by it;
  there are no organizations, farms or memberships. Planned in revisions `0002`-`0004` and tasks T1.1-T1.6.

## Context

The product starts as one family's business but must host several organizations without any of them seeing the
others' data. Each organization has farms; users may belong to more than one organization.

## Decision

- **Shared schema, one database.** Every tenant table has `organization_id NOT NULL` and `UNIQUE(organization_id, id)`.
- **Composite foreign keys** `(organization_id, parent_id)` for children, so a row pointing at another tenant's
  parent cannot be stored at all. The database enforces tenancy even if application code forgets.
- **Tenant selection by header.** The client sends `X-Organization-Id`; it is only a selector. The server looks
  up an active membership for (token subject, header) and answers 404 `ORGANIZATION_NOT_FOUND` if there is none.
  With no header and exactly one membership, that organization is used. The JWT stays identity-only.
- Cross-tenant access answers **404**, not 403, so existence is not revealed.
- Authorization is a `TenantContext(user_id, organization_id, actor_kind, role, permissions)` built by
  `require(Permission.X)` (ADR-006). Row-level security is a second layer (ADR-005).

## Alternatives considered

- **Database (or schema) per tenant.** Pros: strongest isolation, simple backups per tenant. Cons: migrations run
  N times, connection management, cross-tenant platform reports are hard. Disproportionate for a few tenants.
- **`organization_id` plain column, filter in code only.** Pros: simplest. Cons: one forgotten filter leaks data,
  and nothing in the database prevents cross-tenant references. Rejected as the only defense.
- **Organization in the JWT.** Pros: no header. Cons: switching organization needs a new token, and a role or
  financial-access change would not apply until the token expires. Rejected.
- **Trusting the header.** Pros: nothing to look up. Cons: any user could name any organization. Rejected:
  membership is always verified.

## Consequences

- Every query, uniqueness rule and index is per organization; composite keys make migrations larger.
- Memberships cover the whole organization; farm-scoped memberships are deferred.
- A membership lookup on every request (cheap, indexed).
- Isolation needs a parametrized cross-tenant test suite (T5.2); until RLS exists the composite FKs and the
  filters are the only barriers.
