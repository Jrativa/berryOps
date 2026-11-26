"""Repositorios en memoria del módulo de inventario."""
import uuid
from datetime import datetime, timezone
from types import SimpleNamespace


class FakePlotRepository:
    def __init__(self, harvests=None):
        self.items = {}
        self._harvests = harvests  # para has_harvests

    def create(self, owner_id, data):
        obj = SimpleNamespace(
            id=uuid.uuid4(), owner_id=owner_id, is_active=True,
            created_at=datetime.now(timezone.utc), **data,
        )
        self.items[obj.id] = obj
        return obj

    def get(self, plot_id):
        return self.items.get(plot_id)

    def get_by_name(self, owner_id, name):
        return next((p for p in self.items.values() if p.owner_id == owner_id and p.name == name), None)

    def list(self, owner_id, include_inactive=False):
        rows = [p for p in self.items.values()
                if (owner_id is None or p.owner_id == owner_id) and (include_inactive or p.is_active)]
        return sorted(rows, key=lambda p: p.name)

    def update(self, plot, fields):
        for k, v in fields.items():
            setattr(plot, k, v)
        return plot

    def has_harvests(self, plot_id):
        return any(h.plot_id == plot_id for h in self._harvests.items.values())

    def delete(self, plot):
        self.items.pop(plot.id, None)


class FakeCostRepository:
    def __init__(self):
        self.items = {}

    def create(self, plot_id, data):
        obj = SimpleNamespace(
            id=uuid.uuid4(), plot_id=plot_id, created_at=datetime.now(timezone.utc), **data,
        )
        self.items[obj.id] = obj
        return obj

    def get(self, cost_id):
        return self.items.get(cost_id)

    def list_for_plot(self, plot_id):
        return sorted((c for c in self.items.values() if c.plot_id == plot_id),
                      key=lambda c: c.incurred_on, reverse=True)

    def list_for_plots(self, plot_ids, date_from, date_to):
        ids = set(plot_ids)
        return [c for c in self.items.values()
                if c.plot_id in ids
                and (date_from is None or c.incurred_on >= date_from)
                and (date_to is None or c.incurred_on <= date_to)]

    def exists_for_plot(self, plot_id):
        return any(c.plot_id == plot_id for c in self.items.values())

    def update(self, cost, fields):
        for k, v in fields.items():
            setattr(cost, k, v)
        return cost

    def delete(self, cost):
        self.items.pop(cost.id, None)


class FakeHarvestRepository:
    def __init__(self):
        self.items = {}

    def create(self, plot_id, data):
        obj = SimpleNamespace(
            id=uuid.uuid4(), plot_id=plot_id, created_at=datetime.now(timezone.utc), **data,
        )
        self.items[obj.id] = obj
        return obj

    def get(self, harvest_id):
        return self.items.get(harvest_id)

    def list_for_plot(self, plot_id):
        return sorted((h for h in self.items.values() if h.plot_id == plot_id),
                      key=lambda h: h.harvested_on, reverse=True)

    def list_for_plots(self, plot_ids, date_from, date_to):
        ids = set(plot_ids)
        return [h for h in self.items.values()
                if h.plot_id in ids
                and (date_from is None or h.harvested_on >= date_from)
                and (date_to is None or h.harvested_on <= date_to)]

    def update(self, harvest, fields):
        for k, v in fields.items():
            setattr(harvest, k, v)
        return harvest

    def delete(self, harvest):
        self.items.pop(harvest.id, None)
