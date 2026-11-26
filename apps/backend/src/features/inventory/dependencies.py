# src/features/inventory/dependencies.py
import importlib

from fastapi import Depends

from apps.backend.src.core.config import settings
from apps.backend.src.core.databases import get_db
from apps.backend.src.features.auth.application.services import AuthService
from apps.backend.src.features.auth.dependencies import get_auth_service, get_current_user
from apps.backend.src.features.inventory.application.plant_service import PlantService
from apps.backend.src.features.inventory.application.services import Actor, InventoryService

repo_module_path = f"src.features.inventory.infrastructure.{settings.DB_ENGINE}.repositories"

try:
    repos = importlib.import_module(repo_module_path)
except ImportError:
    raise NotImplementedError(f"Repositorios no implementados para el motor: {settings.DB_ENGINE}")


def get_inventory_service(db=Depends(get_db)) -> InventoryService:
    return InventoryService(
        plot_repo=repos.PlotRepository(db),
        harvest_repo=repos.HarvestRepository(db),
        cost_repo=repos.CostRepository(db),
    )


def get_plant_service(
    inventory: InventoryService = Depends(get_inventory_service),
    db=Depends(get_db),
) -> PlantService:
    return PlantService(
        inventory=inventory,
        plant_repo=repos.PlantRepository(db),
        observation_repo=repos.ObservationRepository(db),
    )


def get_actor(
    user=Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service),
) -> Actor:
    """Usuario autenticado traducido a Actor (el servicio no conoce el módulo auth)."""
    return Actor(id=user.id, is_admin=auth_service.is_admin(user))
