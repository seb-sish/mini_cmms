import uuid
from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Date, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin, VersionMixin

if TYPE_CHECKING:
    from app.db.models.equipment import Equipment
    from app.db.models.maintenance_plan import MaintenancePlan


class MaintenanceSchedule(Base, UUIDPrimaryKeyMixin, TimestampMixin, VersionMixin):
    __tablename__ = "maintenance_schedules"

    plan_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("maintenance_plans.id", ondelete="CASCADE"),
        nullable=False,
    )
    equipment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("equipment.id", ondelete="RESTRICT"),
        nullable=False,
    )
    next_due_on: Mapped[date] = mapped_column(Date, nullable=False)
    last_completed_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    plan: Mapped["MaintenancePlan"] = relationship("MaintenancePlan", back_populates="schedules")
    equipment: Mapped["Equipment"] = relationship("Equipment")

    __table_args__ = (
        Index("uq_maintenance_schedules_plan_equipment", plan_id, equipment_id, unique=True),
        Index("ix_maintenance_schedules_next_due_on", next_due_on),
        Index("ix_maintenance_schedules_is_active", is_active),
    )
