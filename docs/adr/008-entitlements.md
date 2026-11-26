# ADR-008: Entitlements as a documented extension point

- Status: Accepted (documented only; no code is planned yet)
- Implementation status: not implemented, by design.

## Context

A future commercial model may sell features per organization (billing). Permissions (what a role may do) and
entitlements (what an organization has bought or been granted) are different questions, and mixing them in the
role matrix would make every pricing change a code change.

## Decision

- Keep them separate. If needed, add an `organization_entitlements` table and check it in
  `require(permission, feature=...)` for **member actors only**. Platform actors are never limited by entitlements.
- Billing, when it exists, writes only entitlements. The family organization gets a permanent row, not a code branch.
- Nothing is built now: the point of this ADR is that the permission layer (ADR-006) has one place to extend.

## Alternatives considered

- **Feature flags in code or environment variables.** Pros: trivial. Cons: global, not per organization.
- **Entitlement columns on `organizations`.** Pros: no new table. Cons: schema change per feature.
- **Build it now.** Cons: no requirement exists (YAGNI).

## Consequences

- No cost today. The risk is forgetting the seam exists; `require()` is the only place to touch.
