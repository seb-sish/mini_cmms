from datetime import date, datetime
from enum import StrEnum
from typing import Optional
from sqlalchemy import Date, DateTime, Index, String
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin, VersionMixin

class EquipmentStatus(StrEnum):
    OPERATIONAL = "OPERATIONAL"
    UNDER_REPAIR = "UNDER_REPAIR"
    OUT_OF_SERVICE = "OUT_OF_SERVICE"

class Equipment(Base, UUIDPrimaryKeyMixin, TimestampMixin, VersionMixin):
    __tablename__ = "equipment"

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    inventory_number: Mapped[str] = mapped_column(String(50), nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    location: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default=EquipmentStatus.OPERATIONAL, nullable=False)
    commissioned_on: Mapped[date] = mapped_column(Date, nullable=False)
    archived_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("uq_equipment_inventory_number", inventory_number, unique=True),
        Index("ix_equipment_category", category),
        Index("ix_equipment_location", location),
        Index("ix_equipment_status", status),
        Index("ix_equipment_archived_at", archived_at),
    )
