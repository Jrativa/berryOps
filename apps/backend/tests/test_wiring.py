"""Garantiza una sola identidad de módulos: todo se importa como `apps.backend.src...`."""
import re
import sys
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parents[1] / "src"
BARE_SRC_IMPORT = re.compile(r"""^\s*(?:from|import)\s+src[.\s]|["']src\.""", re.MULTILINE)
EXPECTED_TABLES = {
    "roles", "users", "user_sessions",
    "plots", "harvests", "plot_costs", "plants", "plant_observations",
}


def test_no_module_imports_with_bare_src_prefix():
    offenders = [
        str(path.relative_to(SRC_DIR))
        for path in SRC_DIR.rglob("*.py")
        if BARE_SRC_IMPORT.search(path.read_text(encoding="utf-8"))
    ]
    assert offenders == []


def test_single_base_holds_every_model_table():
    from apps.backend.src.core import databases
    from apps.backend.src.core.databases import postgres_db
    from apps.backend.src.features.auth import dependencies as auth_deps  # noqa: F401
    from apps.backend.src.features.inventory import dependencies as inventory_deps  # noqa: F401

    # El paquete debe exponer las funciones del MISMO módulo (y por tanto del mismo Base) que usan los modelos
    assert databases.SessionLocal is postgres_db.SessionLocal
    # Alembic (env.py) importa este mismo Base: sus modelos deben registrarse en él
    from apps.backend.src.features.auth.infrastructure.postgres import models  # noqa: F401
    from apps.backend.src.features.inventory.infrastructure.postgres import models as _m  # noqa: F401
    assert set(postgres_db.Base.metadata.tables) == EXPECTED_TABLES
    assert [name for name in sys.modules if name == "src" or name.startswith("src.")] == []


def test_app_startup_never_changes_the_schema(monkeypatch):
    from fastapi.testclient import TestClient

    from apps.backend.src.core.databases import postgres_db
    from apps.backend.src.main import app

    def forbidden(*args, **kwargs):
        raise AssertionError("el arranque no debe crear tablas (usar Alembic)")

    monkeypatch.setattr(postgres_db.Base.metadata, "create_all", forbidden)
    with TestClient(app) as client:  # ejecuta el lifespan de arranque
        assert client.get("/").status_code == 200
    assert not hasattr(postgres_db, "init_db")
