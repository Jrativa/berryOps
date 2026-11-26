import uuid
from datetime import date, timedelta

import pytest
from fastapi import FastAPI, Header
from fastapi.testclient import TestClient

from apps.backend.src.features.inventory.application.services import Actor, InventoryService
from apps.backend.src.features.inventory.dependencies import get_actor, get_inventory_service
from apps.backend.src.features.inventory.presentation.routes import router
from apps.backend.tests.fakes_inventory import FakeCostRepository, FakeHarvestRepository, FakePlotRepository

USERS = {
    "ana": Actor(id=uuid.uuid4()),
    "beto": Actor(id=uuid.uuid4()),
    "admin": Actor(id=uuid.uuid4(), is_admin=True),
}
TODAY = date.today().isoformat()


def _actor_from_header(x_user: str = Header()):
    """Sustituye al usuario autenticado: la cabecera X-User elige quién actúa."""
    return USERS[x_user]


def as_user(name):
    return {"X-User": name}


@pytest.fixture
def client():
    harvests = FakeHarvestRepository()
    service = InventoryService(FakePlotRepository(harvests), harvests, FakeCostRepository())
    app = FastAPI()
    app.include_router(router, prefix="/inventory")
    app.dependency_overrides[get_inventory_service] = lambda: service
    app.dependency_overrides[get_actor] = _actor_from_header
    return TestClient(app)


def new_plot(client, user="ana", name="Norte", area=2.0):
    r = client.post("/inventory/plots", headers=as_user(user),
                    json={"name": name, "variety": "Biloxi", "area_ha": area})
    assert r.status_code == 201, r.text
    return r.json()


def test_requires_authentication():
    app = FastAPI()
    app.include_router(router, prefix="/inventory")
    c = TestClient(app)
    assert c.get("/inventory/plots").status_code == 401
    assert c.get("/inventory/summary").status_code == 401


def test_plot_crud_flow(client):
    plot = new_plot(client)
    assert plot["is_active"] is True and plot["owner_id"] == str(USERS["ana"].id)
    assert client.get(f"/inventory/plots/{plot['id']}", headers=as_user("ana")).status_code == 200
    r = client.patch(f"/inventory/plots/{plot['id']}", headers=as_user("ana"), json={"variety": "Duke"})
    assert r.status_code == 200 and r.json()["variety"] == "Duke"
    assert client.delete(f"/inventory/plots/{plot['id']}", headers=as_user("ana")).status_code == 204
    assert client.get(f"/inventory/plots/{plot['id']}", headers=as_user("ana")).status_code == 404


def test_validation_errors(client):
    r = client.post("/inventory/plots", headers=as_user("ana"),
                    json={"name": "X", "variety": "B", "area_ha": 0})
    assert r.status_code == 422
    new_plot(client)
    dup = client.post("/inventory/plots", headers=as_user("ana"),
                      json={"name": "Norte", "variety": "B", "area_ha": 1})
    assert dup.status_code == 400 and "nombre" in dup.json()["detail"]


def test_other_user_gets_404_not_403(client):
    plot = new_plot(client)
    for method, url, body in [
        ("get", f"/inventory/plots/{plot['id']}", None),
        ("patch", f"/inventory/plots/{plot['id']}", {"name": "x"}),
        ("delete", f"/inventory/plots/{plot['id']}", None),
        ("get", f"/inventory/plots/{plot['id']}/harvests", None),
        ("post", f"/inventory/plots/{plot['id']}/harvests",
         {"harvested_on": TODAY, "quantity_kg": 5}),
    ]:
        r = getattr(client, method)(url, headers=as_user("beto"), **({"json": body} if body else {}))
        assert r.status_code == 404, (method, url, r.text)
    assert client.get("/inventory/plots", headers=as_user("beto")).json() == []


def test_harvest_flow_and_summary(client):
    plot = new_plot(client, area=2.0)
    pid = plot["id"]
    r = client.post(f"/inventory/plots/{pid}/harvests", headers=as_user("ana"),
                    json={"harvested_on": TODAY, "quantity_kg": 120.5, "grade": "premium"})
    assert r.status_code == 201
    hid = r.json()["id"]
    assert client.patch(f"/inventory/harvests/{hid}", headers=as_user("ana"),
                        json={"quantity_kg": 200}).json()["quantity_kg"] == 200
    assert len(client.get(f"/inventory/plots/{pid}/harvests", headers=as_user("ana")).json()) == 1

    s = client.get("/inventory/summary", headers=as_user("ana")).json()
    assert s["total_kg"] == 200 and s["yield_kg_per_ha"] == 100 and s["harvest_count"] == 1
    assert s["by_grade"] == [{"grade": "premium", "total_kg": 200.0}]

    assert client.delete(f"/inventory/harvests/{hid}", headers=as_user("beto")).status_code == 404
    assert client.delete(f"/inventory/harvests/{hid}", headers=as_user("ana")).status_code == 204
    assert client.get("/inventory/summary", headers=as_user("ana")).json()["total_kg"] == 0


def test_harvest_rejects_bad_input(client):
    pid = new_plot(client)["id"]
    url = f"/inventory/plots/{pid}/harvests"
    future = (date.today() + timedelta(days=2)).isoformat()
    assert client.post(url, headers=as_user("ana"),
                       json={"harvested_on": future, "quantity_kg": 5}).status_code == 400
    assert client.post(url, headers=as_user("ana"),
                       json={"harvested_on": TODAY, "quantity_kg": -1}).status_code == 422
    assert client.post(url, headers=as_user("ana"),
                       json={"harvested_on": TODAY, "quantity_kg": 5, "grade": "x"}).status_code == 422


def test_summary_filters_and_admin_scope(client):
    a, b = new_plot(client, "ana", "A")["id"], new_plot(client, "beto", "B")["id"]
    client.post(f"/inventory/plots/{a}/harvests", headers=as_user("ana"),
                json={"harvested_on": TODAY, "quantity_kg": 10})
    client.post(f"/inventory/plots/{b}/harvests", headers=as_user("beto"),
                json={"harvested_on": TODAY, "quantity_kg": 90})
    assert client.get("/inventory/summary", headers=as_user("ana")).json()["total_kg"] == 10
    assert client.get("/inventory/summary", headers=as_user("admin")).json()["total_kg"] == 100
    owner = str(USERS["beto"].id)
    assert client.get(f"/inventory/summary?owner={owner}", headers=as_user("admin")).json()["total_kg"] == 90
    # un usuario normal no puede ver a otro con ?owner=
    assert client.get(f"/inventory/summary?owner={owner}", headers=as_user("ana")).json()["total_kg"] == 10
    bad = client.get("/inventory/summary?from=2026-05-01&to=2026-01-01", headers=as_user("ana"))
    assert bad.status_code == 400
    assert client.get("/inventory/summary?from=2999-01-01", headers=as_user("ana")).json()["total_kg"] == 0
