import uuid
from datetime import date, timedelta

import pytest

from apps.backend.src.features.inventory.application.plant_service import PlantService
from apps.backend.src.features.inventory.application.services import Actor, InventoryService
from apps.backend.src.features.inventory.domain import plant_schemas as ps
from apps.backend.src.features.inventory.domain import schemas
from apps.backend.tests.fakes_inventory import FakeCostRepository, FakeHarvestRepository, FakePlotRepository
from apps.backend.tests.fakes_plants import FakeObservationRepository, FakePlantRepository

ANA = Actor(id=uuid.uuid4())
BETO = Actor(id=uuid.uuid4())
ADMIN = Actor(id=uuid.uuid4(), is_admin=True)


@pytest.fixture
def env():
    harvests = FakeHarvestRepository()
    inventory = InventoryService(FakePlotRepository(harvests), harvests, FakeCostRepository())
    plant_repo = FakePlantRepository()
    service = PlantService(inventory, plant_repo, FakeObservationRepository(plant_repo))
    plot = inventory.create_plot(ANA, schemas.PlotCreate(name="Norte", variety="Biloxi", area_ha=1))
    return service, inventory, plot


def grid(rows, columns):
    return ps.GridGenerate(rows=rows, columns=columns)


# ---------- generar cuadrícula ----------
def test_generate_grid_creates_all_healthy(env):
    service, inventory, plot = env
    result = service.generate_grid(ANA, plot.id, grid(3, 4))
    assert (result.created, result.total) == (12, 12)
    plants = service.list_plants(ANA, plot.id)
    assert len(plants) == 12 and all(p.status == "healthy" for p in plants)
    assert (plants[0].row, plants[0].col) == (1, 1) and (plants[-1].row, plants[-1].col) == (3, 4)
    assert inventory.get_plot(ANA, plot.id).plant_count == 12  # se sincroniza el contador del lote


def test_generate_grid_is_idempotent_and_extends(env):
    service, _, plot = env
    service.generate_grid(ANA, plot.id, grid(2, 2))
    again = service.generate_grid(ANA, plot.id, grid(2, 2))
    assert (again.created, again.total) == (0, 4)
    bigger = service.generate_grid(ANA, plot.id, grid(3, 3))
    assert (bigger.created, bigger.total) == (5, 9)


def test_generate_keeps_existing_status(env):
    service, _, plot = env
    service.generate_grid(ANA, plot.id, grid(2, 2))
    plant = service.get_by_position(ANA, plot.id, 1, 1)
    service.observe(ANA, plant.id, ps.ObservationCreate(status="sick"))
    service.generate_grid(ANA, plot.id, grid(3, 3))
    assert service.get_by_position(ANA, plot.id, 1, 1).status == "sick"


def test_grid_limits():
    with pytest.raises(Exception):
        grid(0, 5)
    with pytest.raises(Exception):
        grid(501, 5)
    with pytest.raises(Exception):  # 400 x 400 = 160000 > 50000
        grid(400, 400)


def test_generate_rejects_archived_plot(env):
    service, inventory, plot = env
    service.generate_grid(ANA, plot.id, grid(1, 1))
    inventory.add_harvest(ANA, plot.id, schemas.HarvestCreate(harvested_on=date.today(), quantity_kg=5))
    inventory.delete_plot(ANA, plot.id)  # con cosechas: se archiva
    with pytest.raises(ValueError, match="archivado"):
        service.generate_grid(ANA, plot.id, grid(2, 2))


# ---------- plantas sueltas ----------
def test_add_plant_and_duplicate_position(env):
    service, _, plot = env
    plant = service.add_plant(ANA, plot.id, ps.PlantCreate(row=7, col=9))
    assert (plant.row, plant.col, plant.status) == (7, 9, "healthy")
    with pytest.raises(ValueError, match="posición"):
        service.add_plant(ANA, plot.id, ps.PlantCreate(row=7, col=9))
    assert service.summary(ANA, plot.id).rows == 7


def test_delete_plant_updates_count(env):
    service, inventory, plot = env
    service.generate_grid(ANA, plot.id, grid(2, 2))
    plant = service.get_by_position(ANA, plot.id, 2, 2)
    service.delete_plant(ANA, plant.id)
    assert service.summary(ANA, plot.id).total == 3
    assert inventory.get_plot(ANA, plot.id).plant_count == 3
    with pytest.raises(LookupError):
        service.get_by_position(ANA, plot.id, 2, 2)


# ---------- observaciones ----------
def test_observe_updates_status_and_keeps_history(env):
    service, _, plot = env
    service.generate_grid(ANA, plot.id, grid(1, 1))
    plant = service.get_by_position(ANA, plot.id, 1, 1)
    service.observe(ANA, plant.id, ps.ObservationCreate(
        status="attention", notes="Hojas amarillas", observed_on=date.today() - timedelta(days=10)))
    service.observe(ANA, plant.id, ps.ObservationCreate(status="sick", notes="Hongo confirmado"))
    service.observe(ANA, plant.id, ps.ObservationCreate(status="healthy", notes="Tratada y recuperada"))

    detail, history = service.get_detail(ANA, plant.id)
    assert detail.status == "healthy"
    assert [o.status for o in history] == ["healthy", "sick", "attention"]  # más reciente primero
    assert all(o.recorded_by == ANA.id for o in history)


def test_observe_rejects_future_date(env):
    service, _, plot = env
    service.generate_grid(ANA, plot.id, grid(1, 1))
    plant = service.get_by_position(ANA, plot.id, 1, 1)
    with pytest.raises(ValueError, match="futura"):
        service.observe(ANA, plant.id, ps.ObservationCreate(
            status="dead", observed_on=date.today() + timedelta(days=1)))


def test_observe_many(env):
    service, _, plot = env
    service.generate_grid(ANA, plot.id, grid(3, 3))
    row_two = [p.id for p in service.list_plants(ANA, plot.id) if p.row == 2]
    result = service.observe_many(ANA, plot.id, ps.BulkObservationCreate(
        plant_ids=row_two, status="attention", notes="Riego irregular en la fila 2"))
    assert result.updated == 3
    assert {(p.row) for p in service.list_plants(ANA, plot.id, "attention")} == {2}
    # cada planta tiene su propia observación
    assert all(len(service.get_detail(ANA, pid)[1]) == 1 for pid in row_two)


def test_observe_many_rejects_foreign_or_unknown_plants(env):
    service, inventory, plot = env
    service.generate_grid(ANA, plot.id, grid(1, 2))
    other = inventory.create_plot(ANA, schemas.PlotCreate(name="Sur", variety="Duke", area_ha=1))
    service.generate_grid(ANA, other.id, grid(1, 1))
    foreign = service.list_plants(ANA, other.id)[0].id  # existe, pero en otro lote
    mine = service.list_plants(ANA, plot.id)[0].id
    with pytest.raises(LookupError):
        service.observe_many(ANA, plot.id, ps.BulkObservationCreate(plant_ids=[mine, foreign], status="dead"))
    with pytest.raises(LookupError):
        service.observe_many(ANA, plot.id, ps.BulkObservationCreate(plant_ids=[uuid.uuid4()], status="dead"))
    assert service.get_by_position(ANA, plot.id, 1, 1).status == "healthy"  # nada se modificó


def test_bulk_ids_are_deduplicated(env):
    service, _, plot = env
    service.generate_grid(ANA, plot.id, grid(1, 1))
    pid = service.list_plants(ANA, plot.id)[0].id
    result = service.observe_many(ANA, plot.id, ps.BulkObservationCreate(plant_ids=[pid, pid], status="sick"))
    assert result.updated == 1 and len(service.get_detail(ANA, pid)[1]) == 1


def test_bulk_limit():
    with pytest.raises(Exception):
        ps.BulkObservationCreate(plant_ids=[uuid.uuid4() for _ in range(ps.MAX_BULK + 1)], status="dead")
    with pytest.raises(Exception):
        ps.BulkObservationCreate(plant_ids=[], status="dead")


# ---------- resumen ----------
def test_summary_counts_and_mortality(env):
    service, _, plot = env
    service.generate_grid(ANA, plot.id, grid(2, 5))  # 10 plantas
    ids = [p.id for p in service.list_plants(ANA, plot.id)]
    service.observe_many(ANA, plot.id, ps.BulkObservationCreate(plant_ids=ids[:1], status="dead"))
    service.observe_many(ANA, plot.id, ps.BulkObservationCreate(plant_ids=ids[1:3], status="sick"))
    s = service.summary(ANA, plot.id)
    assert (s.rows, s.columns, s.total) == (2, 5, 10)
    assert s.counts == {"healthy": 7, "attention": 0, "sick": 2, "dead": 1}
    assert s.mortality_rate == 10.0


def test_summary_empty(env):
    service, _, plot = env
    s = service.summary(ANA, plot.id)
    assert (s.rows, s.columns, s.total, s.mortality_rate) == (0, 0, 0, 0.0)


def test_list_filter_and_invalid_status(env):
    service, _, plot = env
    service.generate_grid(ANA, plot.id, grid(1, 3))
    first = service.list_plants(ANA, plot.id)[0]
    service.observe(ANA, first.id, ps.ObservationCreate(status="dead"))
    assert [p.id for p in service.list_plants(ANA, plot.id, "dead")] == [first.id]
    with pytest.raises(ValueError):
        service.list_plants(ANA, plot.id, "otra")


# ---------- propiedad ----------
def test_other_user_cannot_touch_plants(env):
    service, _, plot = env
    service.generate_grid(ANA, plot.id, grid(1, 1))
    plant = service.list_plants(ANA, plot.id)[0]
    for call in (
        lambda: service.list_plants(BETO, plot.id),
        lambda: service.summary(BETO, plot.id),
        lambda: service.generate_grid(BETO, plot.id, grid(2, 2)),
        lambda: service.add_plant(BETO, plot.id, ps.PlantCreate(row=1, col=2)),
        lambda: service.get_detail(BETO, plant.id),
        lambda: service.observe(BETO, plant.id, ps.ObservationCreate(status="dead")),
        lambda: service.delete_plant(BETO, plant.id),
        lambda: service.get_by_position(BETO, plot.id, 1, 1),
    ):
        with pytest.raises(LookupError):
            call()


def test_admin_reads_but_cannot_write(env):
    service, _, plot = env
    service.generate_grid(ANA, plot.id, grid(1, 1))
    plant = service.list_plants(ANA, plot.id)[0]
    assert len(service.list_plants(ADMIN, plot.id)) == 1
    assert service.summary(ADMIN, plot.id).total == 1
    assert service.get_detail(ADMIN, plant.id)[0].id == plant.id
    with pytest.raises(LookupError):
        service.observe(ADMIN, plant.id, ps.ObservationCreate(status="dead"))
    with pytest.raises(LookupError):
        service.generate_grid(ADMIN, plot.id, grid(2, 2))
