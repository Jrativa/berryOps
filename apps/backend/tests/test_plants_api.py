import uuid
from datetime import date, timedelta

import pytest
from fastapi import FastAPI, Header
from fastapi.testclient import TestClient

from apps.backend.src.features.inventory.application.plant_service import PlantService
from apps.backend.src.features.inventory.application.services import Actor, InventoryService
from apps.backend.src.features.inventory.dependencies import get_actor, get_inventory_service, get_plant_service
from apps.backend.src.features.inventory.presentation.routes import router
from apps.backend.tests.fakes_inventory import FakeCostRepository, FakeHarvestRepository, FakePlotRepository
from apps.backend.tests.fakes_plants import FakeObservationRepository, FakePlantRepository

USERS = {
    "ana": Actor(id=uuid.uuid4()),
    "beto": Actor(id=uuid.uuid4()),
    "admin": Actor(id=uuid.uuid4(), is_admin=True),
}


def _actor_from_header(x_user: str = Header()):
    return USERS[x_user]


def as_user(name):
    return {"X-User": name}


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


def new_plot(client, user="ana", name="Norte"):
    r = client.post("/inventory/plots", headers=as_user(user),
                    json={"name": name, "variety": "Biloxi", "area_ha": 1})
    assert r.status_code == 201, r.text
    return r.json()["id"]


def generate(client, plot_id, rows=3, columns=4, user="ana"):
    return client.post(f"/inventory/plots/{plot_id}/plants/generate", headers=as_user(user),
                       json={"rows": rows, "columns": columns})


def test_requires_authentication():
    app = FastAPI()
    app.include_router(router, prefix="/inventory")
    c = TestClient(app)
    pid = uuid.uuid4()
    assert c.get(f"/inventory/plots/{pid}/plants").status_code == 401
    assert c.post(f"/inventory/plots/{pid}/plants/generate", json={"rows": 1, "columns": 1}).status_code == 401
    assert c.get(f"/inventory/plants/{pid}").status_code == 401


def test_generate_list_and_summary(client):
    pid = new_plot(client)
    r = generate(client, pid)
    assert r.status_code == 200 and r.json() == {"created": 12, "total": 12}
    assert generate(client, pid).json() == {"created": 0, "total": 12}  # idempotente

    plants = client.get(f"/inventory/plots/{pid}/plants", headers=as_user("ana")).json()
    assert len(plants) == 12 and {p["status"] for p in plants} == {"healthy"}
    assert set(plants[0]) == {"id", "row", "col", "status"}  # versión ligera para el mapa

    s = client.get(f"/inventory/plots/{pid}/plants/summary", headers=as_user("ana")).json()
    assert s == {"rows": 3, "columns": 4, "total": 12,
                 "counts": {"healthy": 12, "attention": 0, "sick": 0, "dead": 0}, "mortality_rate": 0.0}
    # el contador del lote queda sincronizado
    assert client.get(f"/inventory/plots/{pid}", headers=as_user("ana")).json()["plant_count"] == 12


def test_lookup_by_position_and_observation_flow(client):
    pid = new_plot(client)
    generate(client, pid)
    plant = client.get(f"/inventory/plots/{pid}/plants/by-position?row=2&col=3", headers=as_user("ana")).json()
    assert (plant["row"], plant["col"]) == (2, 3)

    r = client.post(f"/inventory/plants/{plant['id']}/observations", headers=as_user("ana"),
                    json={"status": "sick", "notes": "Mancha en hojas"})
    assert r.status_code == 201 and r.json()["status"] == "sick"

    detail = client.get(f"/inventory/plants/{plant['id']}", headers=as_user("ana")).json()
    assert detail["status"] == "sick" and detail["row"] == 2
    assert [o["notes"] for o in detail["observations"]] == ["Mancha en hojas"]
    assert client.get(f"/inventory/plots/{pid}/plants?status=sick", headers=as_user("ana")).json()[0]["id"] == plant["id"]
    assert client.get(f"/inventory/plots/{pid}/plants/by-position?row=9&col=9", headers=as_user("ana")).status_code == 404


def test_bulk_observation(client):
    pid = new_plot(client)
    generate(client, pid)
    plants = client.get(f"/inventory/plots/{pid}/plants", headers=as_user("ana")).json()
    ids = [p["id"] for p in plants if p["row"] == 1]
    r = client.post(f"/inventory/plots/{pid}/plants/observations", headers=as_user("ana"),
                    json={"plant_ids": ids, "status": "attention", "notes": "Fila 1 con poco riego"})
    assert r.status_code == 200 and r.json() == {"updated": 4}
    s = client.get(f"/inventory/plots/{pid}/plants/summary", headers=as_user("ana")).json()
    assert s["counts"]["attention"] == 4 and s["counts"]["healthy"] == 8


def test_validation_errors(client):
    pid = new_plot(client)
    assert generate(client, pid, 0, 5).status_code == 422
    assert generate(client, pid, 400, 400).status_code == 422
    generate(client, pid, 1, 1)
    plant = client.get(f"/inventory/plots/{pid}/plants", headers=as_user("ana")).json()[0]["id"]
    assert client.post(f"/inventory/plants/{plant}/observations", headers=as_user("ana"),
                       json={"status": "zombie"}).status_code == 422
    future = (date.today() + timedelta(days=1)).isoformat()
    bad = client.post(f"/inventory/plants/{plant}/observations", headers=as_user("ana"),
                      json={"status": "dead", "observed_on": future})
    assert bad.status_code == 400
    assert client.post(f"/inventory/plots/{pid}/plants/observations", headers=as_user("ana"),
                       json={"plant_ids": [], "status": "dead"}).status_code == 422
    assert client.get(f"/inventory/plots/{pid}/plants?status=otra", headers=as_user("ana")).status_code == 400


def test_add_and_delete_single_plant(client):
    pid = new_plot(client)
    r = client.post(f"/inventory/plots/{pid}/plants", headers=as_user("ana"), json={"row": 5, "col": 6})
    assert r.status_code == 201 and (r.json()["row"], r.json()["col"]) == (5, 6)
    dup = client.post(f"/inventory/plots/{pid}/plants", headers=as_user("ana"), json={"row": 5, "col": 6})
    assert dup.status_code == 400
    assert client.delete(f"/inventory/plants/{r.json()['id']}", headers=as_user("ana")).status_code == 204
    assert client.get(f"/inventory/plants/{r.json()['id']}", headers=as_user("ana")).status_code == 404


def test_other_user_gets_404_and_admin_reads_only(client):
    pid = new_plot(client)
    generate(client, pid, 1, 1)
    plant = client.get(f"/inventory/plots/{pid}/plants", headers=as_user("ana")).json()[0]["id"]

    for method, url, body in [
        ("get", f"/inventory/plots/{pid}/plants", None),
        ("get", f"/inventory/plots/{pid}/plants/summary", None),
        ("post", f"/inventory/plots/{pid}/plants/generate", {"rows": 2, "columns": 2}),
        ("get", f"/inventory/plants/{plant}", None),
        ("post", f"/inventory/plants/{plant}/observations", {"status": "dead"}),
        ("delete", f"/inventory/plants/{plant}", None),
    ]:
        kwargs = {"json": body} if body else {}
        assert getattr(client, method)(url, headers=as_user("beto"), **kwargs).status_code == 404, (method, url)

    assert client.get(f"/inventory/plots/{pid}/plants", headers=as_user("admin")).status_code == 200
    assert client.get(f"/inventory/plants/{plant}", headers=as_user("admin")).status_code == 200
    assert client.post(f"/inventory/plants/{plant}/observations", headers=as_user("admin"),
                       json={"status": "dead"}).status_code == 404
