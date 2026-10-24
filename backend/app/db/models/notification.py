from datetime import date, datetime, timezone
from enum import StrEnum
import uuid
from sqlalchemy import Date, DateTime, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, UUIDPrimaryKeyMixin

class NotificationType(StrEnum):
    THREE_DAYS_BEFORE = "THREE_DAYS_BEFORE"
    ON_DUE_DATE = "ON_DUE_DATE"

class Notification(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "notifications"

    recipient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    plan_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("maintenance_plans.id", ondelete="CASCADE"),
        nullable=False,
    )
    schedule_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("maintenance_schedules.id", ondelete="CASCADE"),
        nullable=False,
    )
    equipment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("equipment.id", ondelete="CASCADE"),
        nullable=False,
    )
    planned_due_on: Mapped[date] = mapped_column(Date, nullable=False)
    type: Mapped[str] = mapped_column(String(50), nullable=False)
    message: Mapped[str] = mapped_column(String(500), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    recipient: Mapped["User"] = relationship("User", foreign_keys=[recipient_id])
    plan: Mapped["MaintenancePlan"] = relationship("MaintenancePlan")
    schedule: Mapped["MaintenanceSchedule"] = relationship("MaintenanceSchedule")
    equipment: Mapped["Equipment"] = relationship("Equipment")

    __table_args__ = (
        Index("uq_notifications_idempotent", schedule_id, planned_due_on, type, recipient_id, unique=True),
        Index("ix_notifications_recipient_id", recipient_id),
        Index("ix_notifications_created_at", created_at),
    )
