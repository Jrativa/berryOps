# ADR-003: Unit of work, one transaction per command

- Status: Accepted
- Implementation status: implemented in `apps/backend/src/core/uow.py` and used by every `dependencies.py`;
  error mapping in `core/errors.py`; atomicity proven by `tests/test_uow_pg.py` and `tests/test_atomicity_pg.py`.
  Not implemented (planned hooks in the same function): tenant context (`set_config`), `lock_timeout`, audit and
  idempotency rows.

## Context

Repositories used to call `commit()` themselves, so a service that wrote twice (e.g. `PlantService.observe`, grid
generation plus `plant_count`) could fail between the writes and leave partial data. Stock work will need several
writes (movement, lot projection, reservation, audit) to succeed or fail together.

## Decision

- `get_uow` yields one SQLAlchemy `Session` per request: commit if the handler returns, rollback on any exception,
  always close. Repositories only `flush()`; services know nothing about commits.
- The unit of work is obtained **only** through the alias `UnitOfWork = Annotated[Session, Depends(get_uow,
  scope="function")]`. The default dependency scope runs the post-`yield` code (the commit) after the response
  has been sent, so a failing commit could not become an error response and the next request might not see the
  write. With `scope="function"` the commit happens before the response is sent. Tests in `tests/test_uow_pg.py`
  prove the behavior (a commit failure is an error response, never a 2xx).
- Database integrity errors map to the error envelope `{detail, code}`: unique violation -> 409, foreign key and
  check violations -> 422, without exposing database text (`core/errors.py`).
- **One deliberate exception: refresh-token reuse.** When `/auth/refresh` detects a revoked token being replayed
  (or an inactive user), the service revokes all of the user's sessions and the request answers 401. A pure
  "rollback on error" would undo the revocation and leave the stolen token family alive. So the route calls
  `uow.commit()` before raising the 401. If nothing was written, the commit is a no-op.

## Alternatives considered

- **Commit inside each repository (previous behavior).** Pros: simple. Cons: partial writes, no atomic
  stock+sale. Rejected.
- **Explicit `with uow:` in every service method.** Pros: transaction boundary visible in the use case. Cons:
  boilerplate, and a forgotten block means no transaction. Rejected: the boundary is the request, one place.
- **Outbox / event-driven consistency.** Pros: decouples side effects. Cons: unnecessary with one database.
  Rejected.
- **SERIALIZABLE isolation everywhere.** Pros: strongest guarantees. Cons: needs retry loops on every command.
  Rejected; the plan uses READ COMMITTED plus `SELECT ... FOR UPDATE` and CHECK constraints (ADR-007).
- **Fail-closed refresh (rollback, 401, keep sessions).** Pros: no exception to the rule. Cons: reuse detection
  would not work. Rejected.

## Consequences

- Any code that needs a session must use the alias; using `Depends(get_uow)` directly silently reintroduces
  commit-after-response.
- A request is a transaction: long-running work inside a handler holds locks. Keep handlers short.
- Anything that must persist despite an error (like the refresh case) has to commit explicitly and say why.
- Because the facade of ADR-001 uses the caller's session, "harvest + lot + movement" and "sale + reservations"
  become atomic without extra machinery.
