# src/features/inventory/presentation/plant_routes.py
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response

from apps.backend.src.core.errors import http_error as _http_error

from apps.backend.src.features.inventory.application.plant_service import PlantService
from apps.backend.src.features.inventory.application.services import Actor
from apps.backend.src.features.inventory.dependencies import get_actor, get_plant_service
from apps.backend.src.features.inventory.domain import plant_schemas as ps

from apps.backend.src.features.inventory.presentation.csv_export import csv_response, safe_cell

router = APIRouter()


@router.post("/plots/{plot_id}/plants/generate", response_model=ps.GenerateResult)
def generate_grid(
    plot_id: UUID,
    data: ps.GridGenerate,
    actor: Actor = Depends(get_actor),
    service: PlantService = Depends(get_plant_service),
):
    try:
        return service.generate_grid(actor, plot_id, data)
    except (ValueError, LookupError) as e:
        raise _http_error(e)


@router.get("/plots/{plot_id}/plants", response_model=list[ps.PlantBrief])
def list_plants(
    plot_id: UUID,
    status: Optional[str] = Query(None),
    actor: Actor = Depends(get_actor),
    service: PlantService = Depends(get_plant_service),
):
    try:
        return service.list_plants(actor, plot_id, status)
    except (ValueError, LookupError) as e:
        raise _http_error(e)


@router.get("/plots/{plot_id}/plants/summary", response_model=ps.PlantsSummary)
def plants_summary(
    plot_id: UUID,
    actor: Actor = Depends(get_actor),
    service: PlantService = Depends(get_plant_service),
):
    try:
        return service.summary(actor, plot_id)
    except (ValueError, LookupError) as e:
        raise _http_error(e)


@router.get("/plots/{plot_id}/plants/export")
def export_plants(
    plot_id: UUID,
    actor: Actor = Depends(get_actor),
    service: PlantService = Depends(get_plant_service),
):
    try:
        rows = service.export_rows(actor, plot_id)
    except (ValueError, LookupError) as e:
        raise _http_error(e)
    return csv_response(
        f"plantas_{plot_id}.csv",
        ["fila", "columna", "estado", "observaciones", "ultima_observacion", "ultimas_notas"],
        ([r["row"], r["col"], r["status"], r["observations"],
          r["last_observed_on"].isoformat() if r["last_observed_on"] else "",
          safe_cell(r["last_notes"])] for r in rows),
    )


@router.get("/plots/{plot_id}/plants/by-position", response_model=ps.PlantResponse)
def plant_by_position(
    plot_id: UUID,
    row: int = Query(ge=1),
    col: int = Query(ge=1),
    actor: Actor = Depends(get_actor),
    service: PlantService = Depends(get_plant_service),
):
    try:
        return service.get_by_position(actor, plot_id, row, col)
    except (ValueError, LookupError) as e:
        raise _http_error(e)


@router.post("/plots/{plot_id}/plants", response_model=ps.PlantResponse, status_code=201)
def add_plant(
    plot_id: UUID,
    data: ps.PlantCreate,
    actor: Actor = Depends(get_actor),
    service: PlantService = Depends(get_plant_service),
):
    try:
        return service.add_plant(actor, plot_id, data)
    except (ValueError, LookupError) as e:
        raise _http_error(e)


@router.post("/plots/{plot_id}/plants/observations", response_model=ps.BulkResult)
def observe_many(
    plot_id: UUID,
    data: ps.BulkObservationCreate,
    actor: Actor = Depends(get_actor),
    service: PlantService = Depends(get_plant_service),
):
    try:
        return service.observe_many(actor, plot_id, data)
    except (ValueError, LookupError) as e:
        raise _http_error(e)


@router.get("/plants/{plant_id}", response_model=ps.PlantDetail)
def get_plant(
    plant_id: UUID,
    actor: Actor = Depends(get_actor),
    service: PlantService = Depends(get_plant_service),
):
    try:
        plant, observations = service.get_detail(actor, plant_id)
    except (ValueError, LookupError) as e:
        raise _http_error(e)
    return ps.PlantDetail(
        id=plant.id, plot_id=plant.plot_id, row=plant.row, col=plant.col,
        status=plant.status, created_at=plant.created_at,
        observations=[ps.ObservationResponse.model_validate(o) for o in observations],
    )


@router.post("/plants/{plant_id}/observations", response_model=ps.ObservationResponse, status_code=201)
def observe(
    plant_id: UUID,
    data: ps.ObservationCreate,
    actor: Actor = Depends(get_actor),
    service: PlantService = Depends(get_plant_service),
):
    try:
        return service.observe(actor, plant_id, data)
    except (ValueError, LookupError) as e:
        raise _http_error(e)


@router.delete("/plants/{plant_id}", status_code=204)
def delete_plant(
    plant_id: UUID,
    actor: Actor = Depends(get_actor),
    service: PlantService = Depends(get_plant_service),
):
    try:
        service.delete_plant(actor, plant_id)
    except (ValueError, LookupError) as e:
        raise _http_error(e)
    return Response(status_code=204)
