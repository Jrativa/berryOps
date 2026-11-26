"""Pruebas mínimas que demuestran que el arnés funciona sobre PostgreSQL real (no SQLite)."""
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from apps.backend.src.features.auth.infrastructure.postgres.models import Role, User
from apps.backend.src.features.inventory.infrastructure.postgres.models import Harvest, Plant, Plot
from apps.backend.tests.pg_support import run_concurrently

pytestmark = pytest.mark.pg


def make_user(session: Session, username: str = "ana") -> User:
    role = Role(name=f"rol-{username}")
    session.add(role)
    session.flush()
    user = User(role_id=role.id, username=username, email=f"{username}@x.com", password_hash="h", full_name=username)
    session.add(user)
    session.flush()
    return user


def make_plot(session: Session, owner: User, name: str = "Lote A") -> Plot:
    plot = Plot(owner_id=owner.id, name=name, variety="Biloxi", area_ha=Decimal("1.50"))
    session.add(plot)
    session.flush()
    return plot


def test_runs_on_postgres(pg_engine):
    with pg_engine.connect() as conn:
        assert conn.execute(text("SHOW server_version")).scalar()
        assert pg_engine.dialect.name == "postgresql"


def test_harvest_uuid_pk_and_numeric_roundtrip_is_exact(pg_engine):
    with Session(pg_engine) as s:
        plot = make_plot(s, make_user(s))
        harvest = Harvest(plot_id=plot.id, harvested_on=date(2026, 1, 5), quantity_kg=Decimal("1234567890.12"))
        s.add(harvest)
        s.commit()
        harvest_id = harvest.id
    with Session(pg_engine) as s:
        loaded = s.get(Harvest, harvest_id)
        assert loaded.quantity_kg == Decimal("1234567890.12")
        assert isinstance(loaded.quantity_kg, Decimal)
        assert loaded.id == harvest_id


def test_duplicate_plot_name_per_owner_violates_unique_constraint(pg_engine):
    with Session(pg_engine) as s:
        owner = make_user(s)
        make_plot(s, owner, "Lote A")
        with pytest.raises(IntegrityError, match="uq_plots_owner_name"):
            make_plot(s, owner, "Lote A")


def test_deleting_plot_cascades_to_plants_in_the_database(pg_engine):
    with Session(pg_engine) as s:
        plot = make_plot(s, make_user(s))
        s.add(Plant(plot_id=plot.id, row=1, col=1))
        s.commit()
        plot_id = plot.id
    with pg_engine.begin() as conn:  # SQL directo: lo que cae es el ON DELETE CASCADE de la BD
        conn.execute(text("DELETE FROM plots WHERE id = :id"), {"id": plot_id})
        assert conn.execute(text("SELECT count(*) FROM plants")).scalar() == 0


def test_plant_without_existing_plot_violates_foreign_key(pg_engine):
    import uuid
    with Session(pg_engine) as s:
        s.add(Plant(plot_id=uuid.uuid4(), row=1, col=1))
        with pytest.raises(IntegrityError):
            s.flush()


def test_state_is_cleaned_between_tests(pg_engine):
    with Session(pg_engine) as s:
        assert s.scalar(select(func.count()).select_from(User)) == 0
        make_user(s)
        s.commit()


def test_two_connections_run_concurrently_and_both_commit(pg_engine):
    with Session(pg_engine) as s:
        make_user(s, "base")
        s.commit()

    def insert_role(name: str):
        def task():
            with pg_engine.begin() as conn:
                pid = conn.execute(text("SELECT pg_backend_pid()")).scalar()
                conn.execute(text("INSERT INTO roles (id, name) VALUES (gen_random_uuid(), :n)"), {"n": name})
                conn.execute(text("SELECT pg_sleep(0.2)"))  # obliga a solapar las transacciones
                return pid
        return task

    pids = run_concurrently([insert_role("r1"), insert_role("r2")])
    assert pids[0] != pids[1]
    with pg_engine.connect() as conn:
        names = set(conn.execute(text("SELECT name FROM roles")).scalars())
    assert {"r1", "r2"} <= names
