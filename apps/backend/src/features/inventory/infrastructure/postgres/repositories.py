# src/features/inventory/infrastructure/postgres/repositories.py
from datetime import date
from typing import Optional, Sequence
from uuid import UUID

from sqlalchemy import func, insert
from sqlalchemy.orm import Session

from apps.backend.src.features.inventory.domain import plant_ports
from apps.backend.src.features.inventory.domain import repository_ports
from apps.backend.src.features.inventory.infrastructure.postgres import models


class PlotRepository(repository_ports.PlotRepository):
    def __init__(self, db: Session):
        self.db = db

    def create(self, owner_id: UUID, data: dict):
        plot = models.Plot(owner_id=owner_id, **data)
        self.db.add(plot)
        self.db.flush()
        self.db.refresh(plot)
        return plot

    def get(self, plot_id: UUID):
        return self.db.get(models.Plot, plot_id)

    def get_by_name(self, owner_id: UUID, name: str):
        return (
            self.db.query(models.Plot)
            .filter(models.Plot.owner_id == owner_id, models.Plot.name == name)
            .first()
        )

    def list(self, owner_id: Optional[UUID], include_inactive: bool = False) -> Sequence:
        q = self.db.query(models.Plot)
        if owner_id is not None:
            q = q.filter(models.Plot.owner_id == owner_id)
        if not include_inactive:
            q = q.filter(models.Plot.is_active.is_(True))
        return q.order_by(models.Plot.name).all()

    def update(self, plot, fields: dict):
        for key, value in fields.items():
            setattr(plot, key, value)
        self.db.flush()
        self.db.refresh(plot)
        return plot

    def has_harvests(self, plot_id: UUID) -> bool:
        return (
            self.db.query(models.Harvest.id).filter(models.Harvest.plot_id == plot_id).first()
            is not None
        )

    def delete(self, plot) -> None:
        self.db.delete(plot)
        self.db.flush()


class HarvestRepository(repository_ports.HarvestRepository):
    def __init__(self, db: Session):
        self.db = db

    def create(self, plot_id: UUID, data: dict):
        harvest = models.Harvest(plot_id=plot_id, **data)
        self.db.add(harvest)
        self.db.flush()
        self.db.refresh(harvest)
        return harvest

    def get(self, harvest_id: UUID):
        return self.db.get(models.Harvest, harvest_id)

    def list_for_plot(self, plot_id: UUID) -> Sequence:
        return (
            self.db.query(models.Harvest)
            .filter(models.Harvest.plot_id == plot_id)
            .order_by(models.Harvest.harvested_on.desc(), models.Harvest.created_at.desc())
            .all()
        )

    def list_for_plots(
        self, plot_ids: Sequence[UUID], date_from: Optional[date], date_to: Optional[date]
    ) -> Sequence:
        if not plot_ids:
            return []
        q = self.db.query(models.Harvest).filter(models.Harvest.plot_id.in_(plot_ids))
        if date_from:
            q = q.filter(models.Harvest.harvested_on >= date_from)
        if date_to:
            q = q.filter(models.Harvest.harvested_on <= date_to)
        return q.all()

    def update(self, harvest, fields: dict):
        for key, value in fields.items():
            setattr(harvest, key, value)
        self.db.flush()
        self.db.refresh(harvest)
        return harvest

    def delete(self, harvest) -> None:
        self.db.delete(harvest)
        self.db.flush()


class CostRepository(repository_ports.CostRepository):
    def __init__(self, db: Session):
        self.db = db

    def create(self, plot_id: UUID, data: dict):
        cost = models.PlotCost(plot_id=plot_id, **data)
        self.db.add(cost)
        self.db.flush()
        self.db.refresh(cost)
        return cost

    def get(self, cost_id: UUID):
        return self.db.get(models.PlotCost, cost_id)

    def list_for_plot(self, plot_id: UUID) -> Sequence:
        return (
            self.db.query(models.PlotCost)
            .filter(models.PlotCost.plot_id == plot_id)
            .order_by(models.PlotCost.incurred_on.desc(), models.PlotCost.created_at.desc())
            .all()
        )

    def list_for_plots(
        self, plot_ids: Sequence[UUID], date_from: Optional[date], date_to: Optional[date]
    ) -> Sequence:
        if not plot_ids:
            return []
        q = self.db.query(models.PlotCost).filter(models.PlotCost.plot_id.in_(plot_ids))
        if date_from:
            q = q.filter(models.PlotCost.incurred_on >= date_from)
        if date_to:
            q = q.filter(models.PlotCost.incurred_on <= date_to)
        return q.order_by(models.PlotCost.incurred_on).all()

    def exists_for_plot(self, plot_id: UUID) -> bool:
        return (
            self.db.query(models.PlotCost.id).filter(models.PlotCost.plot_id == plot_id).first()
            is not None
        )

    def update(self, cost, fields: dict):
        for key, value in fields.items():
            setattr(cost, key, value)
        self.db.flush()
        self.db.refresh(cost)
        return cost

    def delete(self, cost) -> None:
        self.db.delete(cost)
        self.db.flush()


class PlantRepository(plant_ports.PlantRepository):
    CHUNK = 2000

    def __init__(self, db: Session):
        self.db = db

    def existing_positions(self, plot_id: UUID) -> set[tuple[int, int]]:
        rows = self.db.query(models.Plant.row, models.Plant.col).filter(models.Plant.plot_id == plot_id).all()
        return {(r, c) for r, c in rows}

    def create_many(self, plot_id: UUID, positions: Sequence[tuple[int, int]]) -> None:
        for i in range(0, len(positions), self.CHUNK):
            self.db.execute(
                insert(models.Plant),
                [{"plot_id": plot_id, "row": r, "col": c, "status": "healthy"}
                 for r, c in positions[i:i + self.CHUNK]],
            )
        self.db.flush()

    def create(self, plot_id: UUID, row: int, col: int):
        plant = models.Plant(plot_id=plot_id, row=row, col=col, status="healthy")
        self.db.add(plant)
        self.db.flush()
        self.db.refresh(plant)
        return plant

    def get(self, plant_id: UUID):
        return self.db.get(models.Plant, plant_id)

    def get_by_position(self, plot_id: UUID, row: int, col: int):
        return (
            self.db.query(models.Plant)
            .filter(models.Plant.plot_id == plot_id, models.Plant.row == row, models.Plant.col == col)
            .first()
        )

    def get_many(self, plot_id: UUID, plant_ids: Sequence[UUID]) -> Sequence:
        return (
            self.db.query(models.Plant)
            .filter(models.Plant.plot_id == plot_id, models.Plant.id.in_(list(plant_ids)))
            .all()
        )

    def list_for_plot(self, plot_id: UUID, status: Optional[str] = None) -> Sequence:
        q = self.db.query(models.Plant).filter(models.Plant.plot_id == plot_id)
        if status:
            q = q.filter(models.Plant.status == status)
        return q.order_by(models.Plant.row, models.Plant.col).all()

    def counts_by_status(self, plot_id: UUID) -> dict[str, int]:
        rows = (
            self.db.query(models.Plant.status, func.count(models.Plant.id))
            .filter(models.Plant.plot_id == plot_id)
            .group_by(models.Plant.status)
            .all()
        )
        return {status: n for status, n in rows}

    def dimensions(self, plot_id: UUID) -> tuple[int, int]:
        row, col = (
            self.db.query(func.max(models.Plant.row), func.max(models.Plant.col))
            .filter(models.Plant.plot_id == plot_id)
            .one()
        )
        return (row or 0, col or 0)

    def set_status(self, plants: Sequence, status: str) -> None:
        for p in plants:
            p.status = status
        self.db.flush()

    def delete(self, plant) -> None:
        self.db.delete(plant)
        self.db.flush()


class ObservationRepository(plant_ports.ObservationRepository):
    def __init__(self, db: Session):
        self.db = db

    def create_many(self, items: Sequence[dict]) -> Sequence:
        objs = [models.PlantObservation(**item) for item in items]
        self.db.add_all(objs)
        self.db.flush()  # id y created_at los asigna Python: todos los objetos quedan completos
        return objs

    def list_for_plot(self, plot_id: UUID) -> Sequence:
        return (
            self.db.query(models.PlantObservation)
            .join(models.Plant, models.Plant.id == models.PlantObservation.plant_id)
            .filter(models.Plant.plot_id == plot_id)
            .all()
        )

    def list_for_plant(self, plant_id: UUID) -> Sequence:
        return (
            self.db.query(models.PlantObservation)
            .filter(models.PlantObservation.plant_id == plant_id)
            .order_by(models.PlantObservation.observed_on.desc(), models.PlantObservation.created_at.desc())
            .all()
        )
