# ADR-006: Static roles, `financial_access` flag and a read-only platform superuser

- Status: Accepted
- Implementation status: partly. Implemented (T0.7): the anonymous bootstrap is removed, so `POST /auth/roles/` and
  `POST /auth/users/` always need an authenticated administrator (`require_admin`), and the first admin is created
  only by the CLI `python -m apps.backend.src.cli bootstrap`. Not implemented: the static role matrix,
  `financial_access`, memberships, the platform superuser and `grant-superuser`, and the removal of
  `ADMIN_ROLE_NAMES`. Today: a global `roles` table where role names listed in `ADMIN_ROLE_NAMES` count as
  administrators (`AuthService.is_admin`). Remaining work: T1.1, T1.3, T1.7.

## Context

Requirements from the owner: operators may register costs, harvests and sales but must not see financial data;
only members the owner chooses may; one maintainer needs support access across organizations; and the current
"role name matched against an environment variable" admin model plus the anonymous bootstrap endpoint are weak.

## Decision

- **Static role matrix** (owner, admin, operator, viewer) in pure code (`tenancy/domain/permissions.py`), plus one
  per-membership flag `financial_access`, settable only by an owner. `financials.read` = owner, or a member with the
  flag. Everything money-related (cost reads/edits/deletes, totals, `cost_per_kg`, reports) needs it.
- **Operators write costs but cannot read them.** A cost POST without `financials.read` returns only
  `{id, status}`; financial fields are **absent**, never zeroed, so absence cannot be read as "0 cost".
  Audit metadata is redacted for the same callers.
- **Platform superuser** is a boolean on `users`, granted only through a CLI (`grant-superuser`, database-owner
  credentials); no endpoint, email or role name grants it. It is a separate maintainer account. Its default access
  is **read-only support** to the one organization named in the header; writes answer 403 `READ_ONLY_SUPPORT`.
  Writing needs a **break-glass membership** (an explicit Admin membership, audited and removable by the Owner).
  Every superuser request writes a `platform.access` audit event. RLS stays intact (ADR-005).
- To be removed (still present today): `ADMIN_ROLE_NAMES`, `POST /auth/roles` and `POST /auth/users`; first users are
  created by CLI or by owners through the members API. The anonymous bootstrap is already removed.

## Alternatives considered

- **Roles only, no flag.** Pros: simpler matrix. Cons: "this operator, but not that one, may see money" would need
  a new role per combination. Rejected.
- **Full permission editor (per-user grants).** Pros: flexible. Cons: UI and testing cost, hard to audit. YAGNI.
- **Operators echo their own cost amount.** Pros: operators can verify what they typed. Cons: leaks the figure to
  anyone allowed to type. Rejected; the cost is that only financial users correct typos.
- **Superuser with full admin or impersonation.** Pros: can fix anything. Cons: a stolen token can corrupt every
  tenant; impersonation misattributes actions. Rejected.
- **Superuser by hardcoded email or env role name (the old model).** Rejected: privilege from configuration text.

## Consequences

- Behavior of existing endpoints changes for non-financial callers (summary and plot responses lose cost fields);
  this is documented and tested with a response-key scan of the financial-field registry.
- A stolen superuser token can still read every tenant. Mitigations: CLI-only provisioning, short TTL, audit.
  MFA and IP allowlisting are deferred (see [../tech-debt.md](../tech-debt.md)).
- Entitlements never apply to platform actors (ADR-008).
