# # src/core/databases/__init__.py
# from src.core.config import settings

# engines = {
#     "postgres": "src.core.databases.postgres_db",
#     "mongo": "src.core.databases.mongo_db"
# }

# def get_db():
#     engine_module = engines.get(settings.DB_ENGINE)
#     if not engine_module:
#         raise ValueError(f"Motor de base de datos no soportado: {settings.DB_ENGINE}")
    
#     module = __import__(engine_module, fromlist=["get_db"])
#     return module.get_db()

# __all__ = ["get_db"]



# src/core/databases/__init__.py
import importlib
from apps.backend.src.core.config import settings

engines = {
    "postgres": "src.core.databases.postgres_db",
    "mongo": "src.core.databases.mongo_db"
}

engine_module_name = engines.get(settings.DB_ENGINE)

if not engine_module_name:
    raise ValueError(f"Motor de base de datos no soportado: {settings.DB_ENGINE}")

# Cargamos el módulo dinámicamente
module = importlib.import_module(engine_module_name)

get_db = module.get_db
init_db = getattr(module, "init_db", lambda: None)

__all__ = ["get_db", "init_db"]