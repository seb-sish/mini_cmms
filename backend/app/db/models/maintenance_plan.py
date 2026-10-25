import uuid
from datetime import date
from enum import StrEnum
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, Boolean, Date, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin, VersionMixin

if TYPE_CHECKING:
    from app.db.models.maintenance_schedule import MaintenanceSchedule


class PlanScope(StrEnum):
    EQUIPMENT = "EQUIPMENT"
    CATEGORY = "CATEGORY"


class MaintenancePlan(Base, UUIDPrimaryKeyMixin, TimestampMixin, VersionMixin):
    __tablename__ = "maintenance_plans"

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    scope: Mapped[str] = mapped_column(String(20), nullable=False)
    equipment_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("equipment.id", ondelete="RESTRICT"),
        nullable=True,
    )
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    interval_days: Mapped[int] = mapped_column(Integer, nullable=False)
    first_due_on: Mapped[date] = mapped_column(Date, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    checklist: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"), default=list, nullable=False
    )

    schedules: Mapped[list["MaintenanceSchedule"]] = relationship(
        "MaintenanceSchedule", back_populates="plan", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_maintenance_plans_scope", scope),
        Index("ix_maintenance_plans_equipment_id", equipment_id),
        Index("ix_maintenance_plans_category", category),
        Index("ix_maintenance_plans_is_active", is_active),
    )
