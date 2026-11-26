"""
Ejecuta los repositorios SQL reales (SQLAlchemy) sobre SQLite en memoria.
No sustituye una prueba con PostgreSQL, pero valida consultas, restricciones y cascadas
sin necesitar una base de datos externa.
"""
import uuid
from datetime import date

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from apps.backend.src.core.databases.postgres_db import Base
from apps.backend.src.features.auth.infrastructure.postgres import models as auth_models
from apps.backend.src.features.inventory.application.plant_service import PlantService
from apps.backend.src.features.inventory.application.services import Actor, InventoryService
from apps.backend.src.features.inventory.domain import plant_schemas as ps
from apps.backend.src.features.inventory.domain import schemas
from apps.backend.src.features.inventory.infrastructure.postgres import models
from apps.backend.src.features.inventory.infrastructure.postgres import repositories as repos


@pytest.fixture
def db():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)

    @event.listens_for(engine, "connect")
    def _fk_on(dbapi_conn, _):  # SQLite no aplica claves foráneas por defecto
        dbapi_conn.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()


@pytest.fixture
def actor(db):
    role = auth_models.Role(name="operario")
    db.add(role)
    db.flush()
    user = auth_models.User(role_id=role.id, username="ana", email="ana@finca.com",
                            password_hash="x", full_name="Ana")
    db.add(user)
    db.commit()
    return Actor(id=user.id)


@pytest.fixture
def svc(db):
    inventory = InventoryService(repos.PlotRepository(db), repos.HarvestRepository(db), repos.CostRepository(db))
    plants = PlantService(inventory, repos.PlantRepository(db), repos.ObservationRepository(db))
    return inventory, plants


def test_full_plant_flow_on_real_repositories(db, actor, svc):
    inventory, plants = svc
    plot = inventory.create_plot(actor, schemas.PlotCreate(name="Norte", variety="Biloxi", area_ha=2))

    # 25 x 30 = 750 plantas: atraviesa la inserción por bloques
    result = plants.generate_grid(actor, plot.id, ps.GridGenerate(rows=25, columns=30))
    assert (result.created, result.total) == (750, 750)
    assert plants.generate_grid(actor, plot.id, ps.GridGenerate(rows=25, columns=30)).created == 0
    assert inventory.get_plot(actor, plot.id).plant_count == 750

    plant = plants.get_by_position(actor, plot.id, 12, 7)
    plants.observe(actor, plant.id, ps.ObservationCreate(status="sick", notes="Hongo"))
    plants.observe(actor, plant.id, ps.ObservationCreate(status="healthy", notes="Recuperada"))
    detail, history = plants.get_detail(actor, plant.id)
    assert detail.status == "healthy" and [o.notes for o in history] == ["Recuperada", "Hongo"]

    row_ids = [p.id for p in plants.list_plants(actor, plot.id) if p.row == 1]
    assert plants.observe_many(actor, plot.id, ps.BulkObservationCreate(
        plant_ids=row_ids, status="dead")).updated == 30

    s = plants.summary(actor, plot.id)
    assert (s.rows, s.columns, s.total) == (25, 30, 750)
    assert s.counts == {"healthy": 720, "attention": 0, "sick": 0, "dead": 30}
    assert s.mortality_rate == 4.0
    assert len(plants.list_plants(actor, plot.id, "dead")) == 30


def test_unique_position_is_enforced_by_database(db, actor, svc):
    inventory, plants = svc
    plot = inventory.create_plot(actor, schemas.PlotCreate(name="Norte", variety="B", area_ha=1))
    plants.add_plant(actor, plot.id, ps.PlantCreate(row=1, col=1))
    with pytest.raises(IntegrityError):  # aunque el servicio lo evita, la BD es la última defensa
        repos.PlantRepository(db).create(plot.id, 1, 1)
    db.rollback()


def test_deleting_plant_removes_its_observations(db, actor, svc):
    inventory, plants = svc
    plot = inventory.create_plot(actor, schemas.PlotCreate(name="Norte", variety="B", area_ha=1))
    plants.generate_grid(actor, plot.id, ps.GridGenerate(rows=1, columns=2))
    plant = plants.get_by_position(actor, plot.id, 1, 1)
    plants.observe(actor, plant.id, ps.ObservationCreate(status="dead"))
    plants.delete_plant(actor, plant.id)
    assert db.query(models.PlantObservation).count() == 0
    assert db.query(models.Plant).count() == 1
    assert inventory.get_plot(actor, plot.id).plant_count == 1


def test_deleting_plot_removes_plants_and_observations(db, actor, svc):
    inventory, plants = svc
    plot = inventory.create_plot(actor, schemas.PlotCreate(name="Norte", variety="B", area_ha=1))
    plants.generate_grid(actor, plot.id, ps.GridGenerate(rows=2, columns=2))
    plants.observe(actor, plants.list_plants(actor, plot.id)[0].id, ps.ObservationCreate(status="sick"))
    inventory.delete_plot(actor, plot.id)  # sin cosechas: borrado real
    assert db.query(models.Plant).count() == 0
    assert db.query(models.PlantObservation).count() == 0


def test_get_many_only_returns_plants_of_that_plot(db, actor, svc):
    inventory, plants = svc
    a = inventory.create_plot(actor, schemas.PlotCreate(name="A", variety="B", area_ha=1))
    b = inventory.create_plot(actor, schemas.PlotCreate(name="B", variety="B", area_ha=1))
    plants.generate_grid(actor, a.id, ps.GridGenerate(rows=1, columns=2))
    plants.generate_grid(actor, b.id, ps.GridGenerate(rows=1, columns=1))
    mine = [p.id for p in plants.list_plants(actor, a.id)]
    foreign = plants.list_plants(actor, b.id)[0].id
    found = repos.PlantRepository(db).get_many(a.id, mine + [foreign, uuid.uuid4()])
    assert {p.id for p in found} == set(mine)


def test_observation_date_defaults_to_today(db, actor, svc):
    inventory, plants = svc
    plot = inventory.create_plot(actor, schemas.PlotCreate(name="Norte", variety="B", area_ha=1))
    plants.generate_grid(actor, plot.id, ps.GridGenerate(rows=1, columns=1))
    plant = plants.list_plants(actor, plot.id)[0]
    obs = plants.observe(actor, plant.id, ps.ObservationCreate(status="attention"))
    assert obs.observed_on == date.today() and obs.recorded_by == actor.id


def test_costs_and_exports_on_real_repositories(db, actor, svc):
    inventory, plants = svc
    plot = inventory.create_plot(actor, schemas.PlotCreate(name="Norte", variety="B", area_ha=2))
    inventory.add_harvest(actor, plot.id, schemas.HarvestCreate(harvested_on=date.today(), quantity_kg=50))
    inventory.add_cost(actor, plot.id, schemas.CostCreate(incurred_on=date.today(), category="labor", amount=125))

    s = inventory.summary(actor)
    assert (s.total_cost, s.cost_per_kg) == (125, 2.5)
    assert s.by_plot[0].total_cost == 125
    assert [(p.name, c.amount) for p, c in inventory.cost_export(actor)] == [("Norte", 125)]
    assert len(inventory.harvest_export(actor, plot_id=plot.id)) == 1

    plants.generate_grid(actor, plot.id, ps.GridGenerate(rows=1, columns=2))
    first = plants.get_by_position(actor, plot.id, 1, 2)
    plants.observe(actor, first.id, ps.ObservationCreate(status="sick", notes="Hongo"))
    rows = plants.export_rows(actor, plot.id)
    assert [(r["row"], r["col"], r["status"], r["observations"]) for r in rows] == [
        (1, 1, "healthy", 0), (1, 2, "sick", 1)]

    inventory.delete_plot(actor, plot.id)  # con costos y cosechas: se archiva
    assert inventory.get_plot(actor, plot.id).is_active is False
