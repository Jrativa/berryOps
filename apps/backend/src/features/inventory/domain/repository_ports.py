# src/features/inventory/domain/repository_ports.py
from datetime import date
from typing import Optional, Protocol, Sequence
from uuid import UUID


class PlotRepository(Protocol):
    """Puerto para lotes de cultivo"""

    def create(self, owner_id: UUID, data: dict):
        ...

    def get(self, plot_id: UUID):
        ...

    def get_by_name(self, owner_id: UUID, name: str):
        ...

    def list(self, owner_id: Optional[UUID], include_inactive: bool = False) -> Sequence:
        """owner_id=None devuelve los de todos los usuarios (solo admin)"""
        ...

    def update(self, plot, fields: dict):
        ...

    def has_harvests(self, plot_id: UUID) -> bool:
        ...

    def delete(self, plot) -> None:
        ...


class HarvestRepository(Protocol):
    """Puerto para registros de cosecha"""

    def create(self, plot_id: UUID, data: dict):
        ...

    def get(self, harvest_id: UUID):
        ...

    def list_for_plot(self, plot_id: UUID) -> Sequence:
        ...

    def list_for_plots(
        self, plot_ids: Sequence[UUID], date_from: Optional[date], date_to: Optional[date]
    ) -> Sequence:
        ...

    def update(self, harvest, fields: dict):
        ...

    def delete(self, harvest) -> None:
        ...


class CostRepository(Protocol):
    """Puerto para los costos de un lote"""

    def create(self, plot_id: UUID, data: dict):
        ...

    def get(self, cost_id: UUID):
        ...

    def list_for_plot(self, plot_id: UUID) -> Sequence:
        ...

    def list_for_plots(
        self, plot_ids: Sequence[UUID], date_from: Optional[date], date_to: Optional[date]
    ) -> Sequence:
        ...

    def exists_for_plot(self, plot_id: UUID) -> bool:
        ...

    def update(self, cost, fields: dict):
        ...

    def delete(self, cost) -> None:
        ...
