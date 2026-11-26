"""Aritmética exacta (Decimal) del inventario: sumas, promedios y redondeo del resumen."""
import json
import uuid
from datetime import date
from decimal import Decimal

import pytest

from apps.backend.src.features.inventory.application.services import Actor, InventoryService
from apps.backend.src.features.inventory.domain import schemas
from apps.backend.tests.fakes_inventory import FakeCostRepository, FakeHarvestRepository, FakePlotRepository

ANA = Actor(id=uuid.uuid4())
TODAY = date.today()


@pytest.fixture
def service():
    harvests = FakeHarvestRepository()
    return InventoryService(FakePlotRepository(harvests), harvests, FakeCostRepository())


def make_plot(service, area=1.0, name="Norte"):
    return service.create_plot(ANA, schemas.PlotCreate(name=name, variety="Biloxi", area_ha=area))


def harvest(service, plot, kg, grade="standard", on=TODAY):
    service.add_harvest(ANA, plot.id, schemas.HarvestCreate(harvested_on=on, quantity_kg=kg, grade=grade))


def cost(service, plot, amount, category="other"):
    service.add_cost(ANA, plot.id, schemas.CostCreate(incurred_on=TODAY, category=category, amount=amount))


def dumped(model) -> str:
    return model.model_dump_json()


def test_input_floats_become_exact_decimals():
    data = schemas.HarvestCreate(harvested_on=TODAY, quantity_kg=0.1)
    assert data.quantity_kg == Decimal("0.1")  # Decimal(0.1) exacto no sería igual


def test_harvest_sums_are_exact(service):
    plot = make_plot(service)
    for kg in (0.1, 0.2, 0.3):
        harvest(service, plot, kg)
    s = service.summary(ANA)
    assert s.total_kg == Decimal("0.6")
    assert json.loads(dumped(s))["total_kg"] == 0.6
    assert s.by_plot[0].total_kg == Decimal("0.6")
    assert s.by_grade[0].total_kg == Decimal("0.6")
    assert s.by_month[0].total_kg == Decimal("0.6")


def test_cost_sums_are_exact(service):
    plot = make_plot(service)
    cost(service, plot, 0.10, "labor")
    cost(service, plot, 0.20, "labor")
    s = service.summary(ANA)
    assert s.total_cost == Decimal("0.3")
    assert s.by_category[0].total == Decimal("0.3")
    assert s.by_plot[0].total_cost == Decimal("0.3")


def test_many_small_rows_aggregate_exactly(service):
    plot = make_plot(service)
    for _ in range(1000):
        harvest(service, plot, 0.01)
        cost(service, plot, 0.01)
    s = service.summary(ANA)
    assert s.total_kg == Decimal("10.00")
    assert s.total_cost == Decimal("10.00")
    assert s.cost_per_kg == Decimal("1.00")


def test_ratios_round_half_up_at_output_boundary(service):
    plot = make_plot(service, area=8.0)
    harvest(service, plot, 1.0)     # 1 / 8 = 0.125 -> 0.13 (HALF_UP; round() flotante daría 0.12)
    cost(service, plot, 0.01)       # 0.01 / 1 = 0.01
    s = service.summary(ANA)
    assert s.yield_kg_per_ha == Decimal("0.13")
    assert s.by_plot[0].yield_kg_per_ha == Decimal("0.13")


def test_cost_per_kg_half_up(service):
    plot = make_plot(service)
    harvest(service, plot, 2.0)
    cost(service, plot, 0.01)       # 0.01 / 2 = 0.005 -> 0.01
    s = service.summary(ANA)
    assert s.cost_per_kg == Decimal("0.01")
    assert s.by_plot[0].cost_per_kg == Decimal("0.01")


def test_summary_json_keeps_numeric_shape(service):
    plot = make_plot(service, area=2.0)
    harvest(service, plot, 10.5)
    cost(service, plot, 3.0, "labor")
    body = json.loads(dumped(service.summary(ANA)))
    assert body["total_kg"] == 10.5 and isinstance(body["total_kg"], float)
    assert body["yield_kg_per_ha"] == 5.25
    assert body["total_cost"] == 3.0
    assert body["by_plot"][0]["cost_per_kg"] == 0.29
    assert body["by_category"][0] == {"category": "labor", "total": 3.0}


def test_empty_summary_has_zero_values(service):
    body = json.loads(dumped(service.summary(ANA)))
    assert body["total_kg"] == 0 and body["yield_kg_per_ha"] == 0
    assert body["total_cost"] == 0 and body["cost_per_kg"] is None
