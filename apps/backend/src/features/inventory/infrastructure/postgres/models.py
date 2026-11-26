# src/features/inventory/infrastructure/postgres/models.py
import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Boolean, Column, Date, DateTime, ForeignKey, Index, Integer, Numeric, String, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from apps.backend.src.core.databases.postgres_db import Base


class Plot(Base):
    __tablename__ = "plots"
    __table_args__ = (UniqueConstraint("owner_id", "name", name="uq_plots_owner_name"),)

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    variety = Column(String(100), nullable=False)
    area_ha = Column(Numeric(10, 2), nullable=False)
    planting_date = Column(Date, nullable=True)
    plant_count = Column(Integer, nullable=True)
    notes = Column(String(500), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    harvests = relationship("Harvest", back_populates="plot", cascade="all, delete-orphan")
    costs = relationship("PlotCost", back_populates="plot", cascade="all, delete-orphan")
    # Las plantas (y sus observaciones) se borran con el lote; lo resuelve el ON DELETE CASCADE de la BD
    plants = relationship("Plant", cascade="all, delete-orphan", passive_deletes=True)


class Harvest(Base):
    __tablename__ = "harvests"
    __table_args__ = (Index("ix_harvests_plot_date", "plot_id", "harvested_on"),)

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    plot_id = Column(UUID(as_uuid=True), ForeignKey("plots.id"), nullable=False)
    harvested_on = Column(Date, nullable=False)
    quantity_kg = Column(Numeric(12, 2), nullable=False)
    grade = Column(String(20), nullable=False, default="standard")
    notes = Column(String(500), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    plot = relationship("Plot", back_populates="harvests")


class PlotCost(Base):
    """Gasto asociado a un lote (insumos, mano de obra, riego...). Sin moneda: es la del usuario."""
    __tablename__ = "plot_costs"
    __table_args__ = (Index("ix_plot_costs_plot_date", "plot_id", "incurred_on"),)

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    plot_id = Column(UUID(as_uuid=True), ForeignKey("plots.id"), nullable=False)
    incurred_on = Column(Date, nullable=False)
    category = Column(String(20), nullable=False, default="other")
    amount = Column(Numeric(14, 2), nullable=False)
    notes = Column(String(500), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    plot = relationship("Plot", back_populates="costs")


class Plant(Base):
    """Planta individual dentro de un lote, identificada por fila y columna."""
    __tablename__ = "plants"
    __table_args__ = (UniqueConstraint("plot_id", "row_num", "col_num", name="uq_plants_position"),)

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    plot_id = Column(UUID(as_uuid=True), ForeignKey("plots.id", ondelete="CASCADE"), nullable=False, index=True)
    row = Column("row_num", Integer, nullable=False)
    col = Column("col_num", Integer, nullable=False)
    # Estado actual (desnormalizado): el historial completo está en plant_observations
    status = Column(String(20), nullable=False, default="healthy")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    observations = relationship("PlantObservation", back_populates="plant", cascade="all, delete-orphan")


class PlantObservation(Base):
    __tablename__ = "plant_observations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    plant_id = Column(UUID(as_uuid=True), ForeignKey("plants.id", ondelete="CASCADE"), nullable=False, index=True)
    status = Column(String(20), nullable=False)
    notes = Column(String(500), nullable=True)
    observed_on = Column(Date, nullable=False)
    recorded_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    # Marca con microsegundos desde Python: desempata observaciones del mismo día de forma estable
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
                        server_default=func.now())

    plant = relationship("Plant", back_populates="observations")
