# src/features/inventory/presentation/routes.py
from datetime import date
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response

from apps.backend.src.features.inventory.application.services import Actor, InventoryService
from apps.backend.src.features.inventory.dependencies import get_actor, get_inventory_service
from apps.backend.src.features.inventory.domain import schemas
from apps.backend.src.features.inventory.presentation.csv_export import csv_response, export_filename, safe_cell
from apps.backend.src.features.inventory.presentation.plant_routes import router as plant_router

router = APIRouter()
router.include_router(plant_router)


def _http_error(e: Exception) -> HTTPException:
    # LookupError → recurso inexistente (o ajeno); ValueError → regla de negocio
    status = 404 if isinstance(e, LookupError) else 400
    return HTTPException(status_code=status, detail=str(e.args[0]) if e.args else str(e))


# ---------- lotes ----------
@router.get("/plots", response_model=list[schemas.PlotResponse])
def list_plots(
    include_inactive: bool = False,
    owner: Optional[UUID] = Query(None, description="Solo admin"),
    actor: Actor = Depends(get_actor),
    service: InventoryService = Depends(get_inventory_service),
):
    return service.list_plots(actor, owner, include_inactive)


@router.post("/plots", response_model=schemas.PlotResponse, status_code=201)
def create_plot(
    data: schemas.PlotCreate,
    actor: Actor = Depends(get_actor),
    service: InventoryService = Depends(get_inventory_service),
):
    try:
        return service.create_plot(actor, data)
    except (ValueError, LookupError) as e:
        raise _http_error(e)


@router.get("/plots/{plot_id}", response_model=schemas.PlotResponse)
def get_plot(
    plot_id: UUID,
    actor: Actor = Depends(get_actor),
    service: InventoryService = Depends(get_inventory_service),
):
    try:
        return service.get_plot(actor, plot_id)
    except (ValueError, LookupError) as e:
        raise _http_error(e)


@router.patch("/plots/{plot_id}", response_model=schemas.PlotResponse)
def update_plot(
    plot_id: UUID,
    data: schemas.PlotUpdate,
    actor: Actor = Depends(get_actor),
    service: InventoryService = Depends(get_inventory_service),
):
    try:
        return service.update_plot(actor, plot_id, data)
    except (ValueError, LookupError) as e:
        raise _http_error(e)


@router.delete("/plots/{plot_id}", status_code=204)
def delete_plot(
    plot_id: UUID,
    actor: Actor = Depends(get_actor),
    service: InventoryService = Depends(get_inventory_service),
):
    try:
        service.delete_plot(actor, plot_id)
    except (ValueError, LookupError) as e:
        raise _http_error(e)
    return Response(status_code=204)


# ---------- cosechas ----------
@router.get("/plots/{plot_id}/harvests", response_model=list[schemas.HarvestResponse])
def list_harvests(
    plot_id: UUID,
    actor: Actor = Depends(get_actor),
    service: InventoryService = Depends(get_inventory_service),
):
    try:
        return service.list_harvests(actor, plot_id)
    except (ValueError, LookupError) as e:
        raise _http_error(e)


@router.post("/plots/{plot_id}/harvests", response_model=schemas.HarvestResponse, status_code=201)
def add_harvest(
    plot_id: UUID,
    data: schemas.HarvestCreate,
    actor: Actor = Depends(get_actor),
    service: InventoryService = Depends(get_inventory_service),
):
    try:
        return service.add_harvest(actor, plot_id, data)
    except (ValueError, LookupError) as e:
        raise _http_error(e)


@router.patch("/harvests/{harvest_id}", response_model=schemas.HarvestResponse)
def update_harvest(
    harvest_id: UUID,
    data: schemas.HarvestUpdate,
    actor: Actor = Depends(get_actor),
    service: InventoryService = Depends(get_inventory_service),
):
    try:
        return service.update_harvest(actor, harvest_id, data)
    except (ValueError, LookupError) as e:
        raise _http_error(e)


@router.delete("/harvests/{harvest_id}", status_code=204)
def delete_harvest(
    harvest_id: UUID,
    actor: Actor = Depends(get_actor),
    service: InventoryService = Depends(get_inventory_service),
):
    try:
        service.delete_harvest(actor, harvest_id)
    except (ValueError, LookupError) as e:
        raise _http_error(e)
    return Response(status_code=204)


# ---------- costos ----------
@router.get("/plots/{plot_id}/costs", response_model=list[schemas.CostResponse])
def list_costs(
    plot_id: UUID,
    actor: Actor = Depends(get_actor),
    service: InventoryService = Depends(get_inventory_service),
):
    try:
        return service.list_costs(actor, plot_id)
    except (ValueError, LookupError) as e:
        raise _http_error(e)


@router.post("/plots/{plot_id}/costs", response_model=schemas.CostResponse, status_code=201)
def add_cost(
    plot_id: UUID,
    data: schemas.CostCreate,
    actor: Actor = Depends(get_actor),
    service: InventoryService = Depends(get_inventory_service),
):
    try:
        return service.add_cost(actor, plot_id, data)
    except (ValueError, LookupError) as e:
        raise _http_error(e)


@router.patch("/costs/{cost_id}", response_model=schemas.CostResponse)
def update_cost(
    cost_id: UUID,
    data: schemas.CostUpdate,
    actor: Actor = Depends(get_actor),
    service: InventoryService = Depends(get_inventory_service),
):
    try:
        return service.update_cost(actor, cost_id, data)
    except (ValueError, LookupError) as e:
        raise _http_error(e)


@router.delete("/costs/{cost_id}", status_code=204)
def delete_cost(
    cost_id: UUID,
    actor: Actor = Depends(get_actor),
    service: InventoryService = Depends(get_inventory_service),
):
    try:
        service.delete_cost(actor, cost_id)
    except (ValueError, LookupError) as e:
        raise _http_error(e)
    return Response(status_code=204)


# ---------- exportación CSV ----------
@router.get("/export/harvests")
def export_harvests(
    date_from: Optional[date] = Query(None, alias="from"),
    date_to: Optional[date] = Query(None, alias="to"),
    plot: Optional[UUID] = Query(None, description="Limitar a un lote"),
    owner: Optional[UUID] = Query(None, description="Solo admin"),
    actor: Actor = Depends(get_actor),
    service: InventoryService = Depends(get_inventory_service),
):
    try:
        rows = service.harvest_export(actor, date_from, date_to, owner, plot)
    except (ValueError, LookupError) as e:
        raise _http_error(e)
    return csv_response(
        export_filename("cosechas", date_from, date_to),
        ["fecha", "lote", "variedad", "cantidad_kg", "calidad", "notas"],
        ([h.harvested_on.isoformat(), safe_cell(p.name), safe_cell(p.variety),
          f"{float(h.quantity_kg):.2f}", h.grade, safe_cell(h.notes)] for p, h in rows),
    )


@router.get("/export/costs")
def export_costs(
    date_from: Optional[date] = Query(None, alias="from"),
    date_to: Optional[date] = Query(None, alias="to"),
    plot: Optional[UUID] = Query(None, description="Limitar a un lote"),
    owner: Optional[UUID] = Query(None, description="Solo admin"),
    actor: Actor = Depends(get_actor),
    service: InventoryService = Depends(get_inventory_service),
):
    try:
        rows = service.cost_export(actor, date_from, date_to, owner, plot)
    except (ValueError, LookupError) as e:
        raise _http_error(e)
    return csv_response(
        export_filename("costos", date_from, date_to),
        ["fecha", "lote", "categoria", "monto", "notas"],
        ([c.incurred_on.isoformat(), safe_cell(p.name), c.category,
          f"{float(c.amount):.2f}", safe_cell(c.notes)] for p, c in rows),
    )


# ---------- resumen ----------
@router.get("/summary", response_model=schemas.SummaryResponse)
def summary(
    date_from: Optional[date] = Query(None, alias="from"),
    date_to: Optional[date] = Query(None, alias="to"),
    owner: Optional[UUID] = Query(None, description="Solo admin"),
    actor: Actor = Depends(get_actor),
    service: InventoryService = Depends(get_inventory_service),
):
    try:
        return service.summary(actor, date_from, date_to, owner)
    except (ValueError, LookupError) as e:
        raise _http_error(e)
