"""NUMERIC(12,2)/(14,2) contra PostgreSQL: el resumen sale exacto de extremo a extremo."""
import json
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from apps.backend.src.features.auth.infrastructure.postgres.models import Role, User
from apps.backend.src.features.inventory.application.services import Actor, InventoryService
from apps.backend.src.features.inventory.domain import schemas
from apps.backend.src.features.inventory.infrastructure.postgres import repositories as repos
from datetime import date


@pytest.fixture
def service_and_actor(pg_engine):
    session = Session(pg_engine)
    role = Role(name="operario")
    session.add(role)
    session.flush()
    user = User(role_id=role.id, username="ana", email="ana@x.com", password_hash="h", full_name="Ana")
    session.add(user)
    session.flush()
    svc = InventoryService(repos.PlotRepository(session), repos.HarvestRepository(session), repos.CostRepository(session))
    yield svc, Actor(id=user.id)
    session.rollback()
    session.close()


def test_summary_is_exact_after_postgres_round_trip(service_and_actor):
    svc, actor = service_and_actor
    plot = svc.create_plot(actor, schemas.PlotCreate(name="Norte", variety="Biloxi", area_ha=3.0))
    for kg in (0.1, 0.2, 0.3, 1000000):
        svc.add_harvest(actor, plot.id, schemas.HarvestCreate(harvested_on=date.today(), quantity_kg=kg))
    for amount in (0.10, 0.20, 999999999.99):
        svc.add_cost(actor, plot.id, schemas.CostCreate(incurred_on=date.today(), category="labor", amount=amount))
    s = svc.summary(actor)
    assert s.total_kg == Decimal("1000000.60")
    assert s.total_cost == Decimal("1000000000.29")
    assert s.by_category[0].total == Decimal("1000000000.29")
    body = json.loads(s.model_dump_json())
    assert body["total_kg"] == 1000000.6
    assert body["yield_kg_per_ha"] == 333333.53
