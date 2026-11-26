# src/features/inventory/application/services.py
from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from typing import Optional
from uuid import UUID

from apps.backend.src.features.inventory.domain import schemas
from apps.backend.src.features.inventory.domain.repository_ports import CostRepository, HarvestRepository, PlotRepository


ZERO = Decimal(0)
_CENTS = Decimal("0.01")


def _round2(value: Decimal) -> Decimal:
    """Redondeo único del resumen, al salir: 2 decimales, ROUND_HALF_UP (los cálculos internos son exactos)."""
    return value.quantize(_CENTS, rounding=ROUND_HALF_UP)


@dataclass(frozen=True)
class Actor:
    """Quién realiza la acción. El servicio no depende del módulo de auth."""
    id: UUID
    is_admin: bool = False


class InventoryService:
    """
    Lógica de negocio del inventario de producción.
    - Cada usuario solo ve y modifica sus lotes y cosechas.
    - Un admin puede consultar los de cualquier usuario, pero no modificarlos.
    - Un recurso ajeno se reporta como inexistente (LookupError) para no revelar su existencia.
    """

    def __init__(
        self, plot_repo: PlotRepository, harvest_repo: HarvestRepository, cost_repo: CostRepository
    ):
        self.plot_repo = plot_repo
        self.harvest_repo = harvest_repo
        self.cost_repo = cost_repo

    # ---------- acceso ----------
    def _get_plot(self, actor: Actor, plot_id: UUID, write: bool = False):
        plot = self.plot_repo.get(plot_id)
        allowed = plot is not None and (
            plot.owner_id == actor.id or (actor.is_admin and not write)
        )
        if not allowed:
            raise LookupError("Lote no encontrado")
        return plot

    def access_plot(self, actor: Actor, plot_id: UUID, write: bool = False):
        """Lote al que el actor puede acceder (lectura, o escritura si es el dueño). Lo usa PlantService."""
        return self._get_plot(actor, plot_id, write=write)

    def _get_harvest(self, actor: Actor, harvest_id: UUID, write: bool = False):
        harvest = self.harvest_repo.get(harvest_id)
        if harvest is None:
            raise LookupError("Cosecha no encontrada")
        try:
            self._get_plot(actor, harvest.plot_id, write=write)
        except LookupError:
            raise LookupError("Cosecha no encontrada")
        return harvest

    def _get_cost(self, actor: Actor, cost_id: UUID, write: bool = False):
        cost = self.cost_repo.get(cost_id)
        if cost is None:
            raise LookupError("Costo no encontrado")
        try:
            self._get_plot(actor, cost.plot_id, write=write)
        except LookupError:
            raise LookupError("Costo no encontrado")
        return cost

    @staticmethod
    def _scope_owner(actor: Actor, owner_id: Optional[UUID]) -> Optional[UUID]:
        """Un usuario normal siempre ve lo suyo; un admin puede filtrar o ver todo."""
        return owner_id if actor.is_admin else actor.id

    # ---------- validaciones ----------
    @staticmethod
    def _check_not_future(value: Optional[date], label: str):
        if value is not None and value > date.today():
            raise ValueError(f"{label} no puede ser futura")

    @staticmethod
    def _check_after_planting(harvested_on: date, planting_date: Optional[date]):
        if planting_date is not None and harvested_on < planting_date:
            raise ValueError("La cosecha no puede ser anterior a la siembra del lote")

    # ---------- lotes ----------
    def create_plot(self, actor: Actor, data: schemas.PlotCreate):
        self._check_not_future(data.planting_date, "La fecha de siembra")
        if self.plot_repo.get_by_name(actor.id, data.name):
            raise ValueError("Ya tienes un lote con ese nombre")
        return self.plot_repo.create(actor.id, data.model_dump())

    def list_plots(
        self, actor: Actor, owner_id: Optional[UUID] = None, include_inactive: bool = False
    ):
        return self.plot_repo.list(self._scope_owner(actor, owner_id), include_inactive)

    def get_plot(self, actor: Actor, plot_id: UUID):
        return self._get_plot(actor, plot_id)

    def update_plot(self, actor: Actor, plot_id: UUID, data: schemas.PlotUpdate):
        plot = self._get_plot(actor, plot_id, write=True)
        fields = data.model_dump(exclude_unset=True)
        if "planting_date" in fields:
            self._check_not_future(fields["planting_date"], "La fecha de siembra")
        if fields.get("name") and fields["name"] != plot.name:
            if self.plot_repo.get_by_name(actor.id, fields["name"]):
                raise ValueError("Ya tienes un lote con ese nombre")
        # nombre, variedad y superficie no admiten null
        for required in ("name", "variety", "area_ha"):
            if required in fields and fields[required] is None:
                raise ValueError(f"'{required}' no puede estar vacío")
        return self.plot_repo.update(plot, fields)

    def delete_plot(self, actor: Actor, plot_id: UUID) -> None:
        """Con cosechas o costos registrados el lote se archiva para conservar el histórico."""
        plot = self._get_plot(actor, plot_id, write=True)
        if self.plot_repo.has_harvests(plot.id) or self.cost_repo.exists_for_plot(plot.id):
            self.plot_repo.update(plot, {"is_active": False})
        else:
            self.plot_repo.delete(plot)

    # ---------- cosechas ----------
    def add_harvest(self, actor: Actor, plot_id: UUID, data: schemas.HarvestCreate):
        plot = self._get_plot(actor, plot_id, write=True)
        if not plot.is_active:
            raise ValueError("El lote está archivado")
        self._check_not_future(data.harvested_on, "La fecha de cosecha")
        self._check_after_planting(data.harvested_on, plot.planting_date)
        return self.harvest_repo.create(plot.id, data.model_dump())

    def list_harvests(self, actor: Actor, plot_id: UUID):
        plot = self._get_plot(actor, plot_id)
        return self.harvest_repo.list_for_plot(plot.id)

    def update_harvest(self, actor: Actor, harvest_id: UUID, data: schemas.HarvestUpdate):
        harvest = self._get_harvest(actor, harvest_id, write=True)
        fields = data.model_dump(exclude_unset=True)
        for required in ("harvested_on", "quantity_kg", "grade"):
            if required in fields and fields[required] is None:
                raise ValueError(f"'{required}' no puede estar vacío")
        if "harvested_on" in fields:
            plot = self._get_plot(actor, harvest.plot_id, write=True)
            self._check_not_future(fields["harvested_on"], "La fecha de cosecha")
            self._check_after_planting(fields["harvested_on"], plot.planting_date)
        return self.harvest_repo.update(harvest, fields)

    def delete_harvest(self, actor: Actor, harvest_id: UUID) -> None:
        harvest = self._get_harvest(actor, harvest_id, write=True)
        self.harvest_repo.delete(harvest)

    # ---------- costos ----------
    def add_cost(self, actor: Actor, plot_id: UUID, data: schemas.CostCreate):
        plot = self._get_plot(actor, plot_id, write=True)
        if not plot.is_active:
            raise ValueError("El lote está archivado")
        self._check_not_future(data.incurred_on, "La fecha del costo")
        return self.cost_repo.create(plot.id, data.model_dump())

    def list_costs(self, actor: Actor, plot_id: UUID):
        plot = self._get_plot(actor, plot_id)
        return self.cost_repo.list_for_plot(plot.id)

    def update_cost(self, actor: Actor, cost_id: UUID, data: schemas.CostUpdate):
        cost = self._get_cost(actor, cost_id, write=True)
        fields = data.model_dump(exclude_unset=True)
        for required in ("incurred_on", "category", "amount"):
            if required in fields and fields[required] is None:
                raise ValueError(f"'{required}' no puede estar vacío")
        if "incurred_on" in fields:
            self._check_not_future(fields["incurred_on"], "La fecha del costo")
        return self.cost_repo.update(cost, fields)

    def delete_cost(self, actor: Actor, cost_id: UUID) -> None:
        cost = self._get_cost(actor, cost_id, write=True)
        self.cost_repo.delete(cost)

    # ---------- exportación ----------
    def _export_scope(self, actor, date_from, date_to, owner_id, plot_id):
        if date_from and date_to and date_from > date_to:
            raise ValueError("'from' no puede ser posterior a 'to'")
        if plot_id is not None:
            plots = [self._get_plot(actor, plot_id)]
        else:
            plots = self.plot_repo.list(self._scope_owner(actor, owner_id), include_inactive=True)
        return {p.id: p for p in plots}

    def harvest_export(self, actor, date_from=None, date_to=None, owner_id=None, plot_id=None):
        """(lote, cosecha) ordenados por fecha, para exportar."""
        plots = self._export_scope(actor, date_from, date_to, owner_id, plot_id)
        rows = self.harvest_repo.list_for_plots(list(plots), date_from, date_to)
        rows = sorted(rows, key=lambda h: (h.harvested_on, plots[h.plot_id].name))
        return [(plots[h.plot_id], h) for h in rows]

    def cost_export(self, actor, date_from=None, date_to=None, owner_id=None, plot_id=None):
        """(lote, costo) ordenados por fecha, para exportar."""
        plots = self._export_scope(actor, date_from, date_to, owner_id, plot_id)
        rows = self.cost_repo.list_for_plots(list(plots), date_from, date_to)
        rows = sorted(rows, key=lambda c: (c.incurred_on, plots[c.plot_id].name))
        return [(plots[c.plot_id], c) for c in rows]

    # ---------- resumen ----------
    def summary(
        self,
        actor: Actor,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        owner_id: Optional[UUID] = None,
    ) -> schemas.SummaryResponse:
        if date_from and date_to and date_from > date_to:
            raise ValueError("'from' no puede ser posterior a 'to'")

        plots = {
            p.id: p
            for p in self.plot_repo.list(self._scope_owner(actor, owner_id), include_inactive=True)
        }
        harvests = self.harvest_repo.list_for_plots(list(plots), date_from, date_to)

        costs = self.cost_repo.list_for_plots(list(plots), date_from, date_to)
        cost_by_plot: dict = defaultdict(Decimal)
        cost_by_category: dict = defaultdict(Decimal)
        for c in costs:
            cost_by_plot[c.plot_id] += c.amount
            cost_by_category[c.category] += c.amount
        total_cost = sum(cost_by_plot.values(), ZERO)

        total = ZERO
        by_plot: dict = defaultdict(Decimal)
        by_month: dict = defaultdict(Decimal)
        by_grade: dict = defaultdict(Decimal)
        last: Optional[date] = None
        for h in harvests:
            kg = h.quantity_kg
            total += kg
            by_plot[h.plot_id] += kg
            by_month[h.harvested_on.strftime("%Y-%m")] += kg
            by_grade[h.grade] += kg
            if last is None or h.harvested_on > last:
                last = h.harvested_on

        plot_rows = []
        # lotes con cosecha o con costos en el periodo; primero los que más produjeron
        plot_ids = sorted(set(by_plot) | set(cost_by_plot), key=lambda pid: (-by_plot.get(pid, ZERO), plots[pid].name))
        for plot_id in plot_ids:
            kg = by_plot.get(plot_id, ZERO)
            cost = cost_by_plot.get(plot_id, ZERO)
            area = plots[plot_id].area_ha
            plot_rows.append(schemas.PlotSummary(
                plot_id=plot_id, plot_name=plots[plot_id].name,
                total_kg=_round2(kg), yield_kg_per_ha=_round2(kg / area),
                total_cost=_round2(cost),
                cost_per_kg=_round2(cost / kg) if kg else None,
            ))
        # rendimiento global: sobre la superficie de los lotes que produjeron en el periodo
        producing_area = sum((plots[pid].area_ha for pid in by_plot), ZERO)

        return schemas.SummaryResponse(
            total_kg=_round2(total),
            harvest_count=len(harvests),
            yield_kg_per_ha=_round2(total / producing_area) if producing_area else ZERO,
            last_harvest_on=last,
            by_plot=plot_rows,
            by_month=[
                schemas.MonthSummary(month=m, total_kg=_round2(kg))
                for m, kg in sorted(by_month.items())
            ],
            by_grade=[
                schemas.GradeSummary(grade=g, total_kg=_round2(kg))
                for g, kg in sorted(by_grade.items(), key=lambda kv: -kv[1])
            ],
            total_cost=_round2(total_cost),
            cost_per_kg=_round2(total_cost / total) if total else None,
            by_category=[
                schemas.CategorySummary(category=c, total=_round2(v))
                for c, v in sorted(cost_by_category.items(), key=lambda kv: -kv[1])
            ],
        )
