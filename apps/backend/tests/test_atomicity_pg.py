"""Atomicidad de los servicios sobre PostgreSQL real.

Un fallo a mitad de una operación no debe dejar nada persistido: el llamador (la unidad de trabajo de la
petición) hace rollback y los repositorios nunca confirman por su cuenta. El estado se comprueba desde
una conexión distinta, que solo ve lo confirmado.
"""
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from apps.backend.src.features.auth.infrastructure.postgres.models import Role, User
from apps.backend.src.features.inventory.application.plant_service import PlantService
from apps.backend.src.features.inventory.application.services import Actor, InventoryService
from apps.backend.src.features.inventory.domain import plant_schemas as ps
from apps.backend.src.features.inventory.infrastructure.postgres import repositories as repos
from apps.backend.src.features.inventory.infrastructure.postgres.models import (
    Plant, PlantObservation, Plot,
)

pytestmark = pytest.mark.pg


class Boom(RuntimeError):
    pass


def _raise(*args, **kwargs):
    raise Boom("fallo forzado")


@pytest.fixture
def seeded(pg_engine):
    """Usuario, lote y planta sana, ya confirmados."""
    with Session(pg_engine) as s:
        role = Role(name="operario")
        s.add(role)
        s.flush()
        user = User(role_id=role.id, username="ana", email="ana@x.com", password_hash="h", full_name="Ana")
        s.add(user)
        s.flush()
        plot = Plot(owner_id=user.id, name="Norte", variety="Biloxi", area_ha=Decimal("1.00"))
        s.add(plot)
        s.flush()
        plant = Plant(plot_id=plot.id, row=1, col=1, status="healthy")
        s.add(plant)
        s.commit()
        return {"actor": Actor(id=user.id), "plot_id": plot.id, "plant_id": plant.id}


@pytest.fixture
def work(pg_engine):
    """Sesión de trabajo + servicios; al salir se hace rollback como lo haría la unidad de trabajo."""
    session = Session(pg_engine)
    inventory = InventoryService(
        repos.PlotRepository(session), repos.HarvestRepository(session), repos.CostRepository(session))
    plants = PlantService(inventory, repos.PlantRepository(session), repos.ObservationRepository(session))
    yield session, inventory, plants
    session.rollback()
    session.close()


def committed(pg_engine, statement):
    with Session(pg_engine) as other:  # conexión distinta: solo ve lo confirmado
        return other.scalar(statement)


def test_failure_after_observation_insert_persists_nothing(pg_engine, seeded, work, monkeypatch):
    session, _, plants = work
    monkeypatch.setattr(plants.plants, "set_status", _raise)  # tras insertar la observación, antes del estado
    with pytest.raises(Boom):
        plants.observe(seeded["actor"], seeded["plant_id"], ps.ObservationCreate(status="dead"))
    session.rollback()
    assert committed(pg_engine, select(func.count()).select_from(PlantObservation)) == 0
    assert committed(pg_engine, select(Plant.status).where(Plant.id == seeded["plant_id"])) == "healthy"


def test_failure_after_bulk_observation_insert_persists_nothing(pg_engine, seeded, work, monkeypatch):
    session, _, plants = work
    monkeypatch.setattr(plants.plants, "set_status", _raise)
    with pytest.raises(Boom):
        plants.observe_many(seeded["actor"], seeded["plot_id"],
                            ps.BulkObservationCreate(plant_ids=[seeded["plant_id"]], status="sick"))
    session.rollback()
    assert committed(pg_engine, select(func.count()).select_from(PlantObservation)) == 0
    assert committed(pg_engine, select(Plant.status).where(Plant.id == seeded["plant_id"])) == "healthy"


def test_failure_in_plant_count_sync_after_grid_generation_persists_nothing(pg_engine, seeded, work, monkeypatch):
    session, inventory, plants = work
    monkeypatch.setattr(inventory.plot_repo, "update", _raise)  # tras crear las plantas, antes de plant_count
    with pytest.raises(Boom):
        plants.generate_grid(seeded["actor"], seeded["plot_id"], ps.GridGenerate(rows=2, columns=3))
    session.rollback()
    assert committed(pg_engine, select(func.count()).select_from(Plant)) == 1  # solo la sembrada
    assert committed(pg_engine, select(Plot.plant_count).where(Plot.id == seeded["plot_id"])) is None


def test_failure_in_plant_count_sync_after_add_plant_persists_nothing(pg_engine, seeded, work, monkeypatch):
    session, inventory, plants = work
    monkeypatch.setattr(inventory.plot_repo, "update", _raise)
    with pytest.raises(Boom):
        plants.add_plant(seeded["actor"], seeded["plot_id"], ps.PlantCreate(row=2, col=2))
    session.rollback()
    assert committed(pg_engine, select(func.count()).select_from(Plant)) == 1


def test_bulk_observations_are_all_returned_consistently(pg_engine, seeded, work):
    """create_many devuelve objetos completos (id y created_at del servidor/Python) para todos, no solo el primero."""
    session, _, plants = work
    plants.plants.create_many(seeded["plot_id"], [(1, 2), (1, 3)])
    ids = [p.id for p in plants.plants.list_for_plot(seeded["plot_id"])]
    created = plants.observations.create_many([
        {"plant_id": pid, "status": "sick", "notes": None, "observed_on": date.today(),
         "recorded_by": seeded["actor"].id}
        for pid in ids
    ])
    assert len(created) == 3
    assert all(o.id is not None and o.created_at is not None for o in created)
    session.rollback()
