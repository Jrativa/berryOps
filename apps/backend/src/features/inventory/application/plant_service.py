# src/features/inventory/application/plant_service.py
from datetime import date
from typing import Optional
from uuid import UUID

from apps.backend.src.features.inventory.application.services import Actor, InventoryService
from apps.backend.src.features.inventory.domain import plant_schemas as ps
from apps.backend.src.features.inventory.domain.plant_ports import ObservationRepository, PlantRepository


class PlantService:
    """
    Plantas individuales de un lote (fila/columna) y su historial de observaciones.
    El acceso a un lote (propiedad, admin solo lectura) lo decide InventoryService.
    """

    def __init__(
        self,
        inventory: InventoryService,
        plant_repo: PlantRepository,
        observation_repo: ObservationRepository,
    ):
        self.inventory = inventory
        self.plants = plant_repo
        self.observations = observation_repo

    # ---------- acceso ----------
    def _writable_plot(self, actor: Actor, plot_id: UUID):
        plot = self.inventory.access_plot(actor, plot_id, write=True)
        if not plot.is_active:
            raise ValueError("El lote está archivado")
        return plot

    def _get_plant(self, actor: Actor, plant_id: UUID, write: bool = False):
        plant = self.plants.get(plant_id)
        if plant is None:
            raise LookupError("Planta no encontrada")
        try:
            plot = self.inventory.access_plot(actor, plant.plot_id, write=write)
        except LookupError:
            raise LookupError("Planta no encontrada")
        if write and not plot.is_active:
            raise ValueError("El lote está archivado")
        return plant, plot

    def _sync_plant_count(self, plot) -> int:
        total = sum(self.plants.counts_by_status(plot.id).values())
        self.inventory.plot_repo.update(plot, {"plant_count": total})
        return total

    @staticmethod
    def _check_date(value: Optional[date]) -> date:
        value = value or date.today()
        if value > date.today():
            raise ValueError("La fecha de observación no puede ser futura")
        return value

    # ---------- alta ----------
    def generate_grid(self, actor: Actor, plot_id: UUID, data: ps.GridGenerate) -> ps.GenerateResult:
        """Crea las plantas que falten hasta completar filas × columnas (idempotente)."""
        plot = self._writable_plot(actor, plot_id)
        existing = self.plants.existing_positions(plot.id)
        missing = [
            (r, c)
            for r in range(1, data.rows + 1)
            for c in range(1, data.columns + 1)
            if (r, c) not in existing
        ]
        if len(existing) + len(missing) > ps.MAX_PLANTS_PER_PLOT:
            raise ValueError(f"Un lote admite como máximo {ps.MAX_PLANTS_PER_PLOT} plantas")
        if missing:
            self.plants.create_many(plot.id, missing)
        return ps.GenerateResult(created=len(missing), total=self._sync_plant_count(plot))

    def add_plant(self, actor: Actor, plot_id: UUID, data: ps.PlantCreate):
        plot = self._writable_plot(actor, plot_id)
        if self.plants.get_by_position(plot.id, data.row, data.col):
            raise ValueError("Ya existe una planta en esa posición")
        if sum(self.plants.counts_by_status(plot.id).values()) >= ps.MAX_PLANTS_PER_PLOT:
            raise ValueError(f"Un lote admite como máximo {ps.MAX_PLANTS_PER_PLOT} plantas")
        plant = self.plants.create(plot.id, data.row, data.col)
        self._sync_plant_count(plot)
        return plant

    def delete_plant(self, actor: Actor, plant_id: UUID) -> None:
        plant, plot = self._get_plant(actor, plant_id, write=True)
        self.plants.delete(plant)
        self._sync_plant_count(plot)

    # ---------- consulta ----------
    def list_plants(self, actor: Actor, plot_id: UUID, status: Optional[str] = None):
        plot = self.inventory.access_plot(actor, plot_id)
        if status is not None and status not in ps.PLANT_STATUSES:
            raise ValueError("Estado de planta no válido")
        return self.plants.list_for_plot(plot.id, status)

    def summary(self, actor: Actor, plot_id: UUID) -> ps.PlantsSummary:
        plot = self.inventory.access_plot(actor, plot_id)
        raw = self.plants.counts_by_status(plot.id)
        counts = {s: raw.get(s, 0) for s in ps.PLANT_STATUSES}
        total = sum(counts.values())
        rows, columns = self.plants.dimensions(plot.id)
        return ps.PlantsSummary(
            rows=rows, columns=columns, total=total, counts=counts,
            mortality_rate=round(counts["dead"] / total * 100, 2) if total else 0.0,
        )

    def get_by_position(self, actor: Actor, plot_id: UUID, row: int, col: int):
        plot = self.inventory.access_plot(actor, plot_id)
        plant = self.plants.get_by_position(plot.id, row, col)
        if plant is None:
            raise LookupError("Planta no encontrada")
        return plant

    def export_rows(self, actor: Actor, plot_id: UUID) -> list[dict]:
        """Una fila por planta con su estado actual y la última observación."""
        plot = self.inventory.access_plot(actor, plot_id)
        by_plant: dict = {}
        for o in self.observations.list_for_plot(plot.id):
            by_plant.setdefault(o.plant_id, []).append(o)
        rows = []
        for p in self.plants.list_for_plot(plot.id):
            obs = by_plant.get(p.id, [])
            last = max(obs, key=lambda o: (o.observed_on, o.created_at), default=None)
            rows.append({
                "row": p.row, "col": p.col, "status": p.status,
                "observations": len(obs),
                "last_observed_on": last.observed_on if last else None,
                "last_notes": last.notes if last else None,
            })
        return rows

    def get_detail(self, actor: Actor, plant_id: UUID):
        plant, _ = self._get_plant(actor, plant_id)
        return plant, self.observations.list_for_plant(plant.id)

    # ---------- observaciones ----------
    def observe(self, actor: Actor, plant_id: UUID, data: ps.ObservationCreate):
        plant, _ = self._get_plant(actor, plant_id, write=True)
        observed_on = self._check_date(data.observed_on)
        created = self.observations.create_many([{
            "plant_id": plant.id, "status": data.status, "notes": data.notes,
            "observed_on": observed_on, "recorded_by": actor.id,
        }])
        self.plants.set_status([plant], data.status)
        return created[0]

    def observe_many(self, actor: Actor, plot_id: UUID, data: ps.BulkObservationCreate) -> ps.BulkResult:
        """Registra el mismo estado en varias plantas del lote (p. ej. toda una fila)."""
        plot = self._writable_plot(actor, plot_id)
        ids = list(dict.fromkeys(data.plant_ids))
        found = self.plants.get_many(plot.id, ids)
        if len(found) != len(ids):
            raise LookupError("Alguna planta no existe en este lote")
        observed_on = self._check_date(data.observed_on)
        self.observations.create_many([
            {"plant_id": p.id, "status": data.status, "notes": data.notes,
             "observed_on": observed_on, "recorded_by": actor.id}
            for p in found
        ])
        self.plants.set_status(found, data.status)
        return ps.BulkResult(updated=len(found))
