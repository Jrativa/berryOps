import uuid
from datetime import date, timedelta

import pytest

from apps.backend.src.features.inventory.application.services import Actor, InventoryService
from apps.backend.src.features.inventory.domain import schemas
from apps.backend.tests.fakes_inventory import FakeCostRepository, FakeHarvestRepository, FakePlotRepository

ANA = Actor(id=uuid.uuid4())
BETO = Actor(id=uuid.uuid4())
ADMIN = Actor(id=uuid.uuid4(), is_admin=True)
TODAY = date.today()


@pytest.fixture
def service():
    harvests = FakeHarvestRepository()
    return InventoryService(FakePlotRepository(harvests), harvests, FakeCostRepository())


def plot_data(name="Lote Norte", area=2.0, planting=None, variety="Biloxi"):
    return schemas.PlotCreate(name=name, variety=variety, area_ha=area, planting_date=planting)


def harvest_data(kg=100.0, on=None, grade="standard"):
    return schemas.HarvestCreate(harvested_on=on or TODAY, quantity_kg=kg, grade=grade)


# ---------- lotes ----------
def test_create_plot_and_duplicate_name_per_owner(service):
    service.create_plot(ANA, plot_data())
    with pytest.raises(ValueError, match="nombre"):
        service.create_plot(ANA, plot_data())
    service.create_plot(BETO, plot_data())  # otro usuario sí puede repetir nombre


def test_plot_planting_date_cannot_be_future(service):
    with pytest.raises(ValueError, match="siembra"):
        service.create_plot(ANA, plot_data(planting=TODAY + timedelta(days=1)))


def test_users_only_see_their_plots(service):
    mine = service.create_plot(ANA, plot_data("A"))
    service.create_plot(BETO, plot_data("B"))
    assert [p.id for p in service.list_plots(ANA)] == [mine.id]
    # pedir los de otro usuario no funciona para un usuario normal
    assert [p.id for p in service.list_plots(ANA, owner_id=BETO.id)] == [mine.id]


def test_other_users_plot_is_not_found(service):
    plot = service.create_plot(ANA, plot_data())
    with pytest.raises(LookupError):
        service.get_plot(BETO, plot.id)
    with pytest.raises(LookupError):
        service.update_plot(BETO, plot.id, schemas.PlotUpdate(name="x"))
    with pytest.raises(LookupError):
        service.delete_plot(BETO, plot.id)
    with pytest.raises(LookupError):
        service.add_harvest(BETO, plot.id, harvest_data())


def test_admin_can_read_everything_but_not_modify(service):
    plot = service.create_plot(ANA, plot_data())
    harvest = service.add_harvest(ANA, plot.id, harvest_data())
    assert service.get_plot(ADMIN, plot.id).id == plot.id
    assert len(service.list_harvests(ADMIN, plot.id)) == 1
    assert len(service.list_plots(ADMIN)) == 1  # sin filtro: todos
    with pytest.raises(LookupError):
        service.update_plot(ADMIN, plot.id, schemas.PlotUpdate(name="x"))
    with pytest.raises(LookupError):
        service.delete_harvest(ADMIN, harvest.id)


def test_update_plot_rejects_duplicate_name_and_nulls(service):
    service.create_plot(ANA, plot_data("A"))
    b = service.create_plot(ANA, plot_data("B"))
    with pytest.raises(ValueError, match="nombre"):
        service.update_plot(ANA, b.id, schemas.PlotUpdate(name="A"))
    with pytest.raises(ValueError):
        service.update_plot(ANA, b.id, schemas.PlotUpdate(name=None))
    assert service.update_plot(ANA, b.id, schemas.PlotUpdate(variety="Duke")).variety == "Duke"


def test_delete_plot_without_harvests_removes_it(service):
    plot = service.create_plot(ANA, plot_data())
    service.delete_plot(ANA, plot.id)
    assert service.list_plots(ANA, include_inactive=True) == []


def test_delete_plot_with_harvests_archives_it(service):
    plot = service.create_plot(ANA, plot_data())
    service.add_harvest(ANA, plot.id, harvest_data())
    service.delete_plot(ANA, plot.id)
    assert service.list_plots(ANA) == []
    assert len(service.list_plots(ANA, include_inactive=True)) == 1
    with pytest.raises(ValueError, match="archivado"):
        service.add_harvest(ANA, plot.id, harvest_data())


# ---------- cosechas ----------
def test_harvest_validations(service):
    plot = service.create_plot(ANA, plot_data(planting=TODAY - timedelta(days=30)))
    with pytest.raises(ValueError, match="futura"):
        service.add_harvest(ANA, plot.id, harvest_data(on=TODAY + timedelta(days=1)))
    with pytest.raises(ValueError, match="anterior a la siembra"):
        service.add_harvest(ANA, plot.id, harvest_data(on=TODAY - timedelta(days=31)))
    with pytest.raises(Exception):  # kg <= 0 lo rechaza el esquema
        harvest_data(kg=0)
    with pytest.raises(Exception):
        harvest_data(grade="otra")


def test_update_and_delete_harvest(service):
    plot = service.create_plot(ANA, plot_data())
    h = service.add_harvest(ANA, plot.id, harvest_data(kg=50))
    upd = service.update_harvest(ANA, h.id, schemas.HarvestUpdate(quantity_kg=80, grade="premium"))
    assert float(upd.quantity_kg) == 80 and upd.grade == "premium"
    with pytest.raises(ValueError):
        service.update_harvest(ANA, h.id, schemas.HarvestUpdate(quantity_kg=None))
    with pytest.raises(LookupError):
        service.update_harvest(BETO, h.id, schemas.HarvestUpdate(quantity_kg=1))
    service.delete_harvest(ANA, h.id)
    assert service.list_harvests(ANA, plot.id) == []
    with pytest.raises(LookupError):
        service.delete_harvest(ANA, h.id)


def test_list_harvests_newest_first(service):
    plot = service.create_plot(ANA, plot_data())
    old = service.add_harvest(ANA, plot.id, harvest_data(on=TODAY - timedelta(days=5)))
    new = service.add_harvest(ANA, plot.id, harvest_data(on=TODAY))
    assert [h.id for h in service.list_harvests(ANA, plot.id)] == [new.id, old.id]


# ---------- resumen ----------
def test_summary_aggregates(service):
    north = service.create_plot(ANA, plot_data("Norte", area=2.0))
    south = service.create_plot(ANA, plot_data("Sur", area=4.0))
    service.create_plot(ANA, plot_data("Sin cosecha", area=10.0))  # no cuenta en el rendimiento
    service.add_harvest(ANA, north.id, harvest_data(100, date(2026, 1, 10), "premium"))
    service.add_harvest(ANA, north.id, harvest_data(50, date(2026, 2, 3), "standard"))
    service.add_harvest(ANA, south.id, harvest_data(150, date(2026, 2, 20), "premium"))

    s = service.summary(ANA)
    assert s.total_kg == 300 and s.harvest_count == 3
    assert s.yield_kg_per_ha == 50.0  # 300 kg / (2 + 4) ha
    assert s.last_harvest_on == date(2026, 2, 20)
    assert {p.plot_name: (p.total_kg, p.yield_kg_per_ha) for p in s.by_plot} == {
        "Norte": (150.0, 75.0), "Sur": (150.0, 37.5)}
    assert [(m.month, m.total_kg) for m in s.by_month] == [("2026-01", 100.0), ("2026-02", 200.0)]
    assert {g.grade: g.total_kg for g in s.by_grade} == {"premium": 250.0, "standard": 50.0}


def test_summary_date_filter_and_isolation(service):
    plot = service.create_plot(ANA, plot_data())
    other = service.create_plot(BETO, plot_data())
    service.add_harvest(ANA, plot.id, harvest_data(100, date(2026, 1, 10)))
    service.add_harvest(ANA, plot.id, harvest_data(40, date(2026, 3, 1)))
    service.add_harvest(BETO, other.id, harvest_data(999, date(2026, 1, 15)))

    assert service.summary(ANA).total_kg == 140
    assert service.summary(ANA, date_from=date(2026, 2, 1)).total_kg == 40
    assert service.summary(ANA, date_to=date(2026, 1, 31)).total_kg == 100
    assert service.summary(ADMIN).total_kg == 1139
    assert service.summary(ADMIN, owner_id=BETO.id).total_kg == 999
    with pytest.raises(ValueError):
        service.summary(ANA, date_from=date(2026, 5, 1), date_to=date(2026, 1, 1))


def test_summary_empty(service):
    s = service.summary(ANA)
    assert s.total_kg == 0 and s.yield_kg_per_ha == 0 and s.last_harvest_on is None
    assert s.by_plot == [] and s.by_month == []
