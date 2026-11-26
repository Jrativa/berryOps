import uuid
from datetime import date, timedelta

import pytest
from fastapi import FastAPI, Header
from fastapi.testclient import TestClient

from apps.backend.src.features.inventory.application.plant_service import PlantService
from apps.backend.src.features.inventory.application.services import Actor, InventoryService
from apps.backend.src.features.inventory.dependencies import get_actor, get_inventory_service, get_plant_service
from apps.backend.src.features.inventory.presentation.csv_export import safe_cell
from apps.backend.src.features.inventory.presentation.routes import router
from apps.backend.tests.fakes_inventory import FakeCostRepository, FakeHarvestRepository, FakePlotRepository
from apps.backend.tests.fakes_plants import FakeObservationRepository, FakePlantRepository

USERS = {
    "ana": Actor(id=uuid.uuid4()),
    "beto": Actor(id=uuid.uuid4()),
    "admin": Actor(id=uuid.uuid4(), is_admin=True),
}
TODAY = date.today().isoformat()


def as_user(name):
    return {"X-User": name}


def _actor_from_header(x_user: str = Header()):
    return USERS[x_user]


@pytest.fixture
def client():
    harvests = FakeHarvestRepository()
    inventory = InventoryService(FakePlotRepository(harvests), harvests, FakeCostRepository())
    plant_repo = FakePlantRepository()
    plants = PlantService(inventory, plant_repo, FakeObservationRepository(plant_repo))
    app = FastAPI()
    app.include_router(router, prefix="/inventory")
    app.dependency_overrides[get_inventory_service] = lambda: inventory
    app.dependency_overrides[get_plant_service] = lambda: plants
    app.dependency_overrides[get_actor] = _actor_from_header
    return TestClient(app)


def new_plot(client, user="ana", name="Norte", area=2.0):
    r = client.post("/inventory/plots", headers=as_user(user),
                    json={"name": name, "variety": "Biloxi", "area_ha": area})
    assert r.status_code == 201, r.text
    return r.json()["id"]


def add_cost(client, plot, amount=100, category="labor", user="ana", day=TODAY, notes=None):
    return client.post(f"/inventory/plots/{plot}/costs", headers=as_user(user),
                       json={"incurred_on": day, "category": category, "amount": amount, "notes": notes})


def add_harvest(client, plot, kg, user="ana", day=TODAY):
    r = client.post(f"/inventory/plots/{plot}/harvests", headers=as_user(user),
                    json={"harvested_on": day, "quantity_kg": kg})
    assert r.status_code == 201, r.text


def csv_lines(response):
    return response.content.decode("utf-8").lstrip("﻿").strip().split("\r\n")


# ---------- costos ----------
def test_cost_crud_and_validation(client):
    plot = new_plot(client)
    r = add_cost(client, plot, 250.5, "fertilizer")
    assert r.status_code == 201 and r.json()["amount"] == 250.5
    cost_id = r.json()["id"]

    listed = client.get(f"/inventory/plots/{plot}/costs", headers=as_user("ana")).json()
    assert [c["id"] for c in listed] == [cost_id]
    r = client.patch(f"/inventory/costs/{cost_id}", headers=as_user("ana"), json={"amount": 300})
    assert r.json()["amount"] == 300

    assert add_cost(client, plot, 0).status_code == 422
    assert add_cost(client, plot, 10, "magia").status_code == 422
    future = (date.today() + timedelta(days=1)).isoformat()
    assert add_cost(client, plot, 10, day=future).status_code == 400
    assert client.patch(f"/inventory/costs/{cost_id}", headers=as_user("ana"),
                        json={"amount": None}).status_code == 400

    assert client.delete(f"/inventory/costs/{cost_id}", headers=as_user("ana")).status_code == 204
    assert client.get(f"/inventory/plots/{plot}/costs", headers=as_user("ana")).json() == []


def test_costs_are_private_and_admin_is_read_only(client):
    plot = new_plot(client)
    cost_id = add_cost(client, plot).json()["id"]

    assert client.get(f"/inventory/plots/{plot}/costs", headers=as_user("beto")).status_code == 404
    assert add_cost(client, plot, user="beto").status_code == 404
    assert client.delete(f"/inventory/costs/{cost_id}", headers=as_user("beto")).status_code == 404

    assert client.get(f"/inventory/plots/{plot}/costs", headers=as_user("admin")).status_code == 200
    assert add_cost(client, plot, user="admin").status_code == 404
    assert client.delete(f"/inventory/costs/{cost_id}", headers=as_user("admin")).status_code == 404


def test_plot_with_costs_is_archived_not_deleted(client):
    plot = new_plot(client)
    add_cost(client, plot)
    assert client.delete(f"/inventory/plots/{plot}", headers=as_user("ana")).status_code == 204
    r = client.get(f"/inventory/plots/{plot}", headers=as_user("ana"))
    assert r.status_code == 200 and r.json()["is_active"] is False
    assert add_cost(client, plot).status_code == 400  # archivado: no admite más costos


def test_summary_includes_cost_per_kg(client):
    a = new_plot(client, name="A", area=1)
    b = new_plot(client, name="B", area=1)
    c = new_plot(client, name="C", area=1)
    add_harvest(client, a, 100)
    add_cost(client, a, 200, "labor")
    add_cost(client, a, 50, "fertilizer")
    add_cost(client, b, 80, "labor")  # solo costos, sin cosecha
    add_harvest(client, c, 40)        # solo cosecha, sin costos

    s = client.get("/inventory/summary", headers=as_user("ana")).json()
    assert s["total_cost"] == 330 and s["total_kg"] == 140
    assert s["cost_per_kg"] == round(330 / 140, 2)
    assert s["by_category"] == [{"category": "labor", "total": 280}, {"category": "fertilizer", "total": 50}]
    rows = {r["plot_name"]: r for r in s["by_plot"]}
    assert rows["A"]["cost_per_kg"] == 2.5 and rows["A"]["total_cost"] == 250
    assert rows["B"]["total_cost"] == 80 and rows["B"]["cost_per_kg"] is None
    assert rows["C"]["total_cost"] == 0 and rows["C"]["cost_per_kg"] == 0


def test_summary_cost_per_kg_is_none_without_harvests(client):
    plot = new_plot(client)
    add_cost(client, plot, 90)
    s = client.get("/inventory/summary", headers=as_user("ana")).json()
    assert s["total_cost"] == 90 and s["cost_per_kg"] is None


def test_summary_cost_respects_date_range(client):
    plot = new_plot(client)
    old = (date.today() - timedelta(days=60)).isoformat()
    add_cost(client, plot, 500, day=old)
    add_cost(client, plot, 20)
    frm = (date.today() - timedelta(days=30)).isoformat()
    s = client.get(f"/inventory/summary?from={frm}", headers=as_user("ana")).json()
    assert s["total_cost"] == 20


# ---------- CSV ----------
def test_safe_cell_neutralizes_formulas():
    assert safe_cell("=1+1") == "'=1+1"
    assert safe_cell("+cmd") == "'+cmd"
    assert safe_cell("@x") == "'@x"
    assert safe_cell("-1") == "'-1"
    assert safe_cell("normal") == "normal"
    assert safe_cell(None) == ""


def test_harvest_export_csv(client):
    plot = new_plot(client, name="Campo Ñandú")
    client.post(f"/inventory/plots/{plot}/harvests", headers=as_user("ana"),
                json={"harvested_on": TODAY, "quantity_kg": 12.5, "grade": "premium",
                      "notes": '=HYPERLINK("x")'})
    add_harvest(client, new_plot(client, user="beto", name="Otro"), 999, user="beto")

    r = client.get("/inventory/export/harvests", headers=as_user("ana"))
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/csv")
    assert "attachment" in r.headers["content-disposition"]
    assert r.content.decode("utf-8").startswith("﻿")
    lines = csv_lines(r)
    assert lines[0] == "fecha,lote,variedad,cantidad_kg,calidad,notas"
    assert len(lines) == 2  # solo lo de Ana
    assert "Campo Ñandú" in lines[1] and "12.50" in lines[1] and "premium" in lines[1]
    assert "'=HYPERLINK" in lines[1]  # fórmula neutralizada


def test_export_is_scoped_and_validates(client):
    plot = new_plot(client)
    add_harvest(client, plot, 5)
    assert client.get(f"/inventory/export/harvests?plot={plot}", headers=as_user("beto")).status_code == 404
    assert client.get(f"/inventory/export/harvests?plot={plot}", headers=as_user("admin")).status_code == 200
    assert client.get("/inventory/export/harvests?from=2026-02-01&to=2026-01-01",
                      headers=as_user("ana")).status_code == 400


def test_cost_export_csv(client):
    plot = new_plot(client)
    add_cost(client, plot, 1234.5, "irrigation", notes="Riego")
    lines = csv_lines(client.get("/inventory/export/costs", headers=as_user("ana")))
    assert lines[0] == "fecha,lote,categoria,monto,notas"
    assert lines[1].endswith("irrigation,1234.50,Riego")


def test_plants_export_csv(client):
    plot = new_plot(client)
    client.post(f"/inventory/plots/{plot}/plants/generate", headers=as_user("ana"),
                json={"rows": 2, "columns": 2})
    pid = client.get(f"/inventory/plots/{plot}/plants/by-position?row=2&col=1",
                     headers=as_user("ana")).json()["id"]
    client.post(f"/inventory/plants/{pid}/observations", headers=as_user("ana"),
                json={"status": "sick", "notes": "Hongo, hojas"})
    r = client.get(f"/inventory/plots/{plot}/plants/export", headers=as_user("ana"))
    assert r.status_code == 200
    lines = csv_lines(r)
    assert lines[0] == "fila,columna,estado,observaciones,ultima_observacion,ultimas_notas"
    assert len(lines) == 5
    assert lines[1] == "1,1,healthy,0,,"
    assert lines[3] == f'2,1,sick,1,{TODAY},"Hongo, hojas"'  # la coma del texto queda entrecomillada
    assert client.get(f"/inventory/plots/{plot}/plants/export", headers=as_user("beto")).status_code == 404
