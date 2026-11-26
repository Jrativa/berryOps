# src/features/inventory/domain/schemas.py
from datetime import date, datetime
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

Grade = Literal["premium", "standard", "processing"]


# -------------------------
# Lotes
# -------------------------
class PlotBase(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    variety: str = Field(min_length=1, max_length=100)
    area_ha: float = Field(gt=0, le=100000)
    planting_date: Optional[date] = None
    plant_count: Optional[int] = Field(default=None, ge=0)
    notes: Optional[str] = Field(default=None, max_length=500)


class PlotCreate(PlotBase):
    pass


class PlotUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    variety: Optional[str] = Field(default=None, min_length=1, max_length=100)
    area_ha: Optional[float] = Field(default=None, gt=0, le=100000)
    planting_date: Optional[date] = None
    plant_count: Optional[int] = Field(default=None, ge=0)
    notes: Optional[str] = Field(default=None, max_length=500)


class PlotResponse(PlotBase):
    id: UUID
    owner_id: UUID
    is_active: bool
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


# -------------------------
# Cosechas
# -------------------------
class HarvestBase(BaseModel):
    harvested_on: date
    quantity_kg: float = Field(gt=0, le=1000000)
    grade: Grade = "standard"
    notes: Optional[str] = Field(default=None, max_length=500)


class HarvestCreate(HarvestBase):
    pass


class HarvestUpdate(BaseModel):
    harvested_on: Optional[date] = None
    quantity_kg: Optional[float] = Field(default=None, gt=0, le=1000000)
    grade: Optional[Grade] = None
    notes: Optional[str] = Field(default=None, max_length=500)


class HarvestResponse(HarvestBase):
    id: UUID
    plot_id: UUID
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


# -------------------------
# Costos
# -------------------------
CostCategory = Literal["fertilizer", "pesticide", "irrigation", "labor", "other"]
COST_CATEGORIES = ("fertilizer", "pesticide", "irrigation", "labor", "other")


class CostBase(BaseModel):
    incurred_on: date
    category: CostCategory = "other"
    amount: float = Field(gt=0, le=1000000000)
    notes: Optional[str] = Field(default=None, max_length=500)


class CostCreate(CostBase):
    pass


class CostUpdate(BaseModel):
    incurred_on: Optional[date] = None
    category: Optional[CostCategory] = None
    amount: Optional[float] = Field(default=None, gt=0, le=1000000000)
    notes: Optional[str] = Field(default=None, max_length=500)


class CostResponse(CostBase):
    id: UUID
    plot_id: UUID
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


# -------------------------
# Resumen
# -------------------------
class PlotSummary(BaseModel):
    plot_id: UUID
    plot_name: str
    total_kg: float
    yield_kg_per_ha: float
    total_cost: float = 0.0
    cost_per_kg: Optional[float] = None  # None si el lote no produjo en el periodo


class MonthSummary(BaseModel):
    month: str  # YYYY-MM
    total_kg: float


class GradeSummary(BaseModel):
    grade: Grade
    total_kg: float


class CategorySummary(BaseModel):
    category: CostCategory
    total: float


class SummaryResponse(BaseModel):
    total_kg: float
    harvest_count: int
    yield_kg_per_ha: float
    last_harvest_on: Optional[date] = None
    by_plot: list[PlotSummary]
    by_month: list[MonthSummary]
    by_grade: list[GradeSummary]
    total_cost: float = 0.0
    cost_per_kg: Optional[float] = None  # None si no hubo producción en el periodo
    by_category: list[CategorySummary] = []
