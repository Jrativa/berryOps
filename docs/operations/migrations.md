# Database migrations (Alembic)

The application **never changes the schema**: there is no `create_all` at startup. Every schema change is an Alembic
revision in `apps/backend/migrations/versions/`. Revision `0001_baseline` reproduces the 8 tables that already exist
in the development database.

All commands run **from the repository root** with the backend virtualenv active:

```bash
alembic -c apps/backend/alembic.ini current      # which revision the DB is at
alembic -c apps/backend/alembic.ini history
alembic -c apps/backend/alembic.ini upgrade head
alembic -c apps/backend/alembic.ini downgrade <revision>
alembic -c apps/backend/alembic.ini revision --autogenerate -m "short description"   # then REVIEW by hand
```

The database URL comes from one place, `apps/backend/migrations/env.py`: a URL set programmatically on the Alembic
`Config` (`config.attributes["sqlalchemy_url"]`, used by the tests) wins; otherwise `Settings.DATABASE_URL`
(`apps/backend/.env`). So **a plain `alembic` command targets the database in `.env`**.

## Running Alembic safely

- A bare `alembic` command (no URL set programmatically) reads `apps/backend/.env` and therefore **targets the
  development database**. Check `current` and the target before `upgrade`, `downgrade` or `stamp`.
- Alembic loads the application `Settings`, so the same validation applies: a `SECRET_KEY` shorter than 32
  characters (or any other invalid setting) stops Alembic before it connects, with a message that never shows the
  value.
- Tests migrate only the guarded test database (`TEST_DATABASE_URL`, name ending in `_test`, checked by
  `apps/backend/tests/pg_guard.py`): they pass that URL to the Alembic `Config` programmatically and never
  migrate the `.env` database.

## 1. New (empty) database

1. Create the empty database (e.g. `createdb`, or `python -m apps.backend.scripts.create_test_db` for the test one).
2. Point `apps/backend/.env` at it and run `alembic -c apps/backend/alembic.ini upgrade head`.

## 2. Existing development database (one-time adoption)

The dev database already has the tables but no `alembic_version` table. Running `upgrade head` on it will try to
`CREATE TABLE` tables that exist and **fail** (`relation "roles" already exists`). That failure is intentional: it
protects the data. Do not work around it; adopt the database with `stamp` instead, which only records the revision
and changes no table.

The schema produced by `0001_baseline` was compared with the dev database through the catalogs (tables, columns,
types, defaults, constraints, indexes) and is identical, so stamping is correct.

Procedure (do it only after the user explicitly approves each step; never skip the backup):

1. **Backup** (custom format, includes data):
   ```powershell
   & "C:\Program Files\PostgreSQL\18\bin\pg_dump.exe" -Fc -h <host> -p <port> -U <user> -d arandanos -f arandanos_<date>.dump
   ```
   Keep the file outside the repository (it contains real data).
2. **Verify the backup** by restoring it into a scratch database and comparing row counts:
   ```powershell
   & "C:\Program Files\PostgreSQL\18\bin\createdb.exe" -h <host> -p <port> -U <user> arandanos_restore_check
   & "C:\Program Files\PostgreSQL\18\bin\pg_restore.exe" -h <host> -p <port> -U <user> -d arandanos_restore_check arandanos_<date>.dump
   ```
   For each of the 8 tables run `SELECT count(*) FROM <table>` on `arandanos` and on `arandanos_restore_check`;
   all counts must match. Then drop the scratch database (`dropdb arandanos_restore_check`).
3. **Stamp** (writes only the `alembic_version` table):
   `alembic -c apps/backend/alembic.ini stamp 0001_baseline`, then check with `current` (`0001_baseline (head)`).

**Adoption record (2026-11-26).** Performed with the user's explicit approval: backup
`arandanos_db-20261126-044454.dump` (24,891 bytes, stored outside the repository in `Arandanos-backups/`), restored into
`arandanos_restore_check` with identical row counts in all 8 tables (harvests 4, plant_observations 8, plants 240,
plot_costs 2, plots 1, roles 1, user_sessions 20, users 1), then `stamp 0001_baseline`. Afterwards `current` reports
`0001_baseline (head)`, row counts are unchanged and the catalog comparison against the migrated schema is empty.
The scratch database `arandanos_restore_check` was left in place and can be dropped.

## 3. Rollback and recovery

- Undo a revision: `alembic -c apps/backend/alembic.ini downgrade <revision>` (`-1` for the previous one).
  Downgrades that drop columns or tables destroy data: take a backup first.
- Full recovery from the backup: restore with `pg_restore --clean --if-exists -d arandanos arandanos_<date>.dump`
  (this replaces the objects with the backup's state), then re-adopt with `alembic stamp <revision at backup time>`.

## 4. Rules for writing migrations

- Schema changes that touch data use **expand / backfill / contract** in separate revisions: add the new structure,
  copy data, and only later remove the old one.
- Each step must be **idempotent**: running it twice, or re-running after a crash halfway, ends in the same state
  (`IF NOT EXISTS`-style guards, `WHERE` clauses that only touch rows still to migrate).
- Test every revision with `upgrade` -> `downgrade` -> `upgrade` on `arandanos_test`
  (see `apps/backend/tests/test_migrations.py`, which also asserts there is no drift between models and migrations).
- Autogenerate output is a draft: review it, and keep constraint/index names explicit.
- **Never run migrations against the dev database without a verified backup and explicit approval.** Tests run
  migrations only against `*_test` databases, enforced by `apps/backend/tests/pg_guard.py`.
