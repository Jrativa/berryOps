"""Repositorios en memoria de plantas y observaciones."""
import uuid
from collections import Counter
from datetime import datetime, timezone
from types import SimpleNamespace


class FakePlantRepository:
    def __init__(self):
        self.items = {}

    def existing_positions(self, plot_id):
        return {(p.row, p.col) for p in self.items.values() if p.plot_id == plot_id}

    def create_many(self, plot_id, positions):
        for r, c in positions:
            self.create(plot_id, r, c)

    def create(self, plot_id, row, col):
        obj = SimpleNamespace(id=uuid.uuid4(), plot_id=plot_id, row=row, col=col,
                              status="healthy", created_at=datetime.now(timezone.utc))
        self.items[obj.id] = obj
        return obj

    def get(self, plant_id):
        return self.items.get(plant_id)

    def get_by_position(self, plot_id, row, col):
        return next((p for p in self.items.values()
                     if p.plot_id == plot_id and p.row == row and p.col == col), None)

    def get_many(self, plot_id, plant_ids):
        ids = set(plant_ids)
        return [p for p in self.items.values() if p.plot_id == plot_id and p.id in ids]

    def list_for_plot(self, plot_id, status=None):
        rows = [p for p in self.items.values()
                if p.plot_id == plot_id and (status is None or p.status == status)]
        return sorted(rows, key=lambda p: (p.row, p.col))

    def counts_by_status(self, plot_id):
        return dict(Counter(p.status for p in self.items.values() if p.plot_id == plot_id))

    def dimensions(self, plot_id):
        mine = [p for p in self.items.values() if p.plot_id == plot_id]
        return (max((p.row for p in mine), default=0), max((p.col for p in mine), default=0))

    def set_status(self, plants, status):
        for p in plants:
            p.status = status

    def delete(self, plant):
        self.items.pop(plant.id, None)


class FakeObservationRepository:
    def __init__(self, plants=None):
        self.plants = plants
        self.items = []

    def create_many(self, items):
        created = [SimpleNamespace(id=uuid.uuid4(), created_at=datetime.now(timezone.utc), **i)
                   for i in items]
        self.items.extend(created)
        return created

    def list_for_plot(self, plot_id):
        plants = {p.id for p in self.plants.items.values() if p.plot_id == plot_id}
        return [o for o in self.items if o.plant_id in plants]

    def list_for_plant(self, plant_id):
        return sorted((o for o in self.items if o.plant_id == plant_id),
                      key=lambda o: (o.observed_on, o.created_at), reverse=True)
