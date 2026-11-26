# src/features/inventory/domain/plant_schemas.py
from datetime import date, datetime
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

PlantStatus = Literal["healthy", "attention", "sick", "dead"]
PLANT_STATUSES: tuple[str, ...] = ("healthy", "attention", "sick", "dead")

MAX_GRID_SIDE = 500
MAX_PLANTS_PER_PLOT = 50000
MAX_BULK = 1000


class GridGenerate(BaseModel):
    rows: int = Field(ge=1, le=MAX_GRID_SIDE)
    columns: int = Field(ge=1, le=MAX_GRID_SIDE)

    @model_validator(mode="after")
    def _limit_total(self):
        if self.rows * self.columns > MAX_PLANTS_PER_PLOT:
            raise ValueError(f"Un lote admite como máximo {MAX_PLANTS_PER_PLOT} plantas")
        return self


class PlantCreate(BaseModel):
    row: int = Field(ge=1, le=1000)
    col: int = Field(ge=1, le=1000)


class PlantBrief(BaseModel):
    """Versión ligera para dibujar el mapa del lote."""
    id: UUID
    row: int
    col: int
    status: PlantStatus
    model_config = ConfigDict(from_attributes=True)


class ObservationCreate(BaseModel):
    status: PlantStatus
    notes: Optional[str] = Field(default=None, max_length=500)
    observed_on: Optional[date] = None  # por defecto, hoy


class BulkObservationCreate(ObservationCreate):
    plant_ids: list[UUID] = Field(min_length=1, max_length=MAX_BULK)


class ObservationResponse(BaseModel):
    id: UUID
    plant_id: UUID
    status: PlantStatus
    notes: Optional[str] = None
    observed_on: date
    recorded_by: UUID
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class PlantResponse(PlantBrief):
    plot_id: UUID
    created_at: datetime


class PlantDetail(PlantResponse):
    observations: list[ObservationResponse]


class PlantsSummary(BaseModel):
    rows: int
    columns: int
    total: int
    counts: dict[PlantStatus, int]
    mortality_rate: float  # % de plantas muertas sobre el total


class GenerateResult(BaseModel):
    created: int
    total: int


class BulkResult(BaseModel):
    updated: int
