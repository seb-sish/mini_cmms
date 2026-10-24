from datetime import date, datetime
from enum import StrEnum
from typing import Optional
import uuid
from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Index, Integer, JSON, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin, VersionMixin

class WorkOrderType(StrEnum):
    REPAIR = "REPAIR"
    PLANNED = "PLANNED"

class WorkOrderStatus(StrEnum):
    CREATED = "CREATED"
    ASSIGNED = "ASSIGNED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CLOSED = "CLOSED"
    CANCELLED = "CANCELLED"

class WorkOrderPriority(StrEnum):
    LOW = "LOW"
    NORMAL = "NORMAL"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class WorkOrder(Base, UUIDPrimaryKeyMixin, TimestampMixin, VersionMixin):
    __tablename__ = "work_orders"

    number: Mapped[str] = mapped_column(String(50), nullable=False)
    type: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default=WorkOrderStatus.CREATED, nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    priority: Mapped[str] = mapped_column(String(20), default=WorkOrderPriority.NORMAL, nullable=False)

    equipment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("equipment.id", ondelete="RESTRICT"),
        nullable=False,
    )
    fault_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("faults.id", ondelete="RESTRICT"),
        nullable=True,
    )
    schedule_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("maintenance_schedules.id", ondelete="RESTRICT"),
        nullable=True,
    )
    planned_due_on: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    author_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    assignee_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
    )

    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
    )
    cancelled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
    )
    cancellation_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    result: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    replaced_parts: Mapped[list[str]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"), default=list, nullable=False
    )

    equipment: Mapped["Equipment"] = relationship("Equipment")
    fault: Mapped[Optional["Fault"]] = relationship("Fault")
    schedule: Mapped[Optional["MaintenanceSchedule"]] = relationship("MaintenanceSchedule")
    author: Mapped["User"] = relationship("User", foreign_keys=[author_id])
    assignee: Mapped[Optional["User"]] = relationship("User", foreign_keys=[assignee_id])

    checklist: Mapped[list["WorkChecklistItem"]] = relationship(
        "WorkChecklistItem", back_populates="work_order", cascade="all, delete-orphan", order_by="WorkChecklistItem.order"
    )
    events: Mapped[list["WorkOrderEvent"]] = relationship(
        "WorkOrderEvent", back_populates="work_order", cascade="all, delete-orphan", order_by="WorkOrderEvent.occurred_at"
    )

    __table_args__ = (
        Index("uq_work_orders_number", number, unique=True),
        Index("ix_work_orders_type", type),
        Index("ix_work_orders_status", status),
        Index("ix_work_orders_equipment_id", equipment_id),
        Index("ix_work_orders_fault_id", fault_id),
        Index("ix_work_orders_schedule_id", schedule_id),
        Index("ix_work_orders_assignee_id", assignee_id),
        Index("ix_work_orders_created_at", "created_at"),
    )

class WorkChecklistItem(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "work_checklist_items"

    work_order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("work_orders.id", ondelete="CASCADE"),
        nullable=False,
    )
    order: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    required: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    checked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    checked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    work_order: Mapped["WorkOrder"] = relationship("WorkOrder", back_populates="checklist")

    __table_args__ = (
        Index("ix_work_checklist_items_work_order_id", work_order_id),
    )
