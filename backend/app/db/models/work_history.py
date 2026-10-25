import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import JSON, DateTime, ForeignKey, Index, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.db.models.equipment import Equipment
    from app.db.models.user import User
    from app.db.models.work_order import WorkOrder


class WorkHistory(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "work_history"

    work_order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("work_orders.id", ondelete="RESTRICT"),
        nullable=False,
    )
    equipment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("equipment.id", ondelete="RESTRICT"),
        nullable=False,
    )
    plan_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("maintenance_plans.id", ondelete="RESTRICT"),
        nullable=True,
    )
    fault_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("faults.id", ondelete="RESTRICT"),
        nullable=True,
    )
    technician_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    closed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    result: Mapped[str] = mapped_column(Text, nullable=False)
    replaced_parts: Mapped[list[str]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"), default=list, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    equipment: Mapped["Equipment"] = relationship("Equipment")
    work_order: Mapped["WorkOrder"] = relationship("WorkOrder")
    technician: Mapped["User"] = relationship("User", foreign_keys=[technician_id])

    __table_args__ = (
        Index("uq_work_history_work_order_id", work_order_id, unique=True),
        Index("ix_work_history_equipment_id", equipment_id),
        Index("ix_work_history_technician_id", technician_id),
        Index("ix_work_history_completed_at", completed_at),
    )
