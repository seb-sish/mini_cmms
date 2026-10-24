from datetime import datetime, timezone
from enum import StrEnum
from typing import Any, Optional
import uuid
from sqlalchemy import DateTime, ForeignKey, Index, JSON, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, UUIDPrimaryKeyMixin

class WorkOrderEventType(StrEnum):
    CREATED = "CREATED"
    ASSIGNED = "ASSIGNED"
    REASSIGNED = "REASSIGNED"
    STARTED = "STARTED"
    CHECKLIST_ITEM_UPDATED = "CHECKLIST_ITEM_UPDATED"
    COMPLETED = "COMPLETED"
    CLOSED = "CLOSED"
    CANCELLED = "CANCELLED"

class WorkOrderEvent(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "work_order_events"

    work_order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("work_orders.id", ondelete="CASCADE"),
        nullable=False,
    )
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    actor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    details: Mapped[Optional[dict[str, Any]]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"), nullable=True
    )

    work_order: Mapped["WorkOrder"] = relationship("WorkOrder", back_populates="events")
    actor: Mapped["User"] = relationship("User")

    __table_args__ = (
        Index("ix_work_order_events_work_order_id", work_order_id),
        Index("ix_work_order_events_occurred_at", occurred_at),
    )
