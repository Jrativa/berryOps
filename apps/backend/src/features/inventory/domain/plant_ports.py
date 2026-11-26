# src/features/inventory/domain/plant_ports.py
from typing import Optional, Protocol, Sequence
from uuid import UUID


class PlantRepository(Protocol):
    """Puerto para las plantas individuales de un lote"""

    def existing_positions(self, plot_id: UUID) -> set[tuple[int, int]]:
        ...

    def create_many(self, plot_id: UUID, positions: Sequence[tuple[int, int]]) -> None:
        ...

    def create(self, plot_id: UUID, row: int, col: int):
        ...

    def get(self, plant_id: UUID):
        ...

    def get_by_position(self, plot_id: UUID, row: int, col: int):
        ...

    def get_many(self, plot_id: UUID, plant_ids: Sequence[UUID]) -> Sequence:
        """Solo devuelve las plantas que pertenecen a ese lote"""
        ...

    def list_for_plot(self, plot_id: UUID, status: Optional[str] = None) -> Sequence:
        ...

    def counts_by_status(self, plot_id: UUID) -> dict[str, int]:
        ...

    def dimensions(self, plot_id: UUID) -> tuple[int, int]:
        """(máx. fila, máx. columna); (0, 0) si no hay plantas"""
        ...

    def set_status(self, plants: Sequence, status: str) -> None:
        ...

    def delete(self, plant) -> None:
        ...


class ObservationRepository(Protocol):
    """Puerto para el historial de observaciones de una planta"""

    def create_many(self, items: Sequence[dict]) -> Sequence:
        ...

    def list_for_plant(self, plant_id: UUID) -> Sequence:
        ...

    def list_for_plot(self, plot_id: UUID) -> Sequence:
        """Observaciones de todas las plantas del lote (para exportar)"""
        ...
