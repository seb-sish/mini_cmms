"""005_work_orders_tables

Revision ID: 005_work_orders_tables
Revises: 004_maintenance_tables
Create Date: 2026-10-24 22:25:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision: str = "005_work_orders_tables"
down_revision: Union[str, None] = "004_maintenance_tables"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.create_table(
        "work_orders",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("number", sa.String(50), nullable=False),
        sa.Column("type", sa.String(20), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="CREATED"),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("equipment_id", UUID(as_uuid=True), sa.ForeignKey("equipment.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("fault_id", UUID(as_uuid=True), sa.ForeignKey("faults.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("schedule_id", UUID(as_uuid=True), sa.ForeignKey("maintenance_schedules.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("planned_due_on", sa.Date(), nullable=True),
        sa.Column("author_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("assignee_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("closed_by", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_by", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("cancelled_reason", sa.Text(), nullable=True),
        sa.Column("result", sa.Text(), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("uq_work_orders_number", "work_orders", ["number"], unique=True)
    op.create_index("ix_work_orders_type", "work_orders", ["type"])
    op.create_index("ix_work_orders_status", "work_orders", ["status"])
    op.create_index("ix_work_orders_equipment_id", "work_orders", ["equipment_id"])
    op.create_index("ix_work_orders_fault_id", "work_orders", ["fault_id"])
    op.create_index("ix_work_orders_schedule_id", "work_orders", ["schedule_id"])
    op.create_index("ix_work_orders_assignee_id", "work_orders", ["assignee_id"])
    op.create_index("ix_work_orders_created_at", "work_orders", ["created_at"])

    op.create_table(
        "work_checklist_items",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("work_order_id", UUID(as_uuid=True), sa.ForeignKey("work_orders.id", ondelete="CASCADE"), nullable=False),
        sa.Column("order", sa.Integer(), nullable=False),
        sa.Column("description", sa.String(500), nullable=False),
        sa.Column("is_required", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("is_checked", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("checked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("comment", sa.Text(), nullable=True),
    )
    op.create_index("ix_work_checklist_items_work_order_id", "work_checklist_items", ["work_order_id"])

    op.create_table(
        "work_order_events",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("work_order_id", UUID(as_uuid=True), sa.ForeignKey("work_orders.id", ondelete="CASCADE"), nullable=False),
        sa.Column("event_type", sa.String(50), nullable=False),
        sa.Column("actor_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("details", sa.JSON().with_variant(JSONB, "postgresql"), nullable=True),
    )
    op.create_index("ix_work_order_events_work_order_id", "work_order_events", ["work_order_id"])
    op.create_index("ix_work_order_events_occurred_at", "work_order_events", ["occurred_at"])

    op.create_table(
        "work_history",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("work_order_id", UUID(as_uuid=True), sa.ForeignKey("work_orders.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("equipment_id", UUID(as_uuid=True), sa.ForeignKey("equipment.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("type", sa.String(20), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("assignee_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("closed_by", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("result", sa.Text(), nullable=False),
        sa.Column("checklist_snapshot", sa.JSON().with_variant(JSONB, "postgresql"), nullable=False, server_default="[]"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("uq_work_history_work_order_id", "work_history", ["work_order_id"], unique=True)
    op.create_index("ix_work_history_equipment_id", "work_history", ["equipment_id"])
    op.create_index("ix_work_history_completed_at", "work_history", ["completed_at"])
    op.create_index("ix_work_history_assignee_id", "work_history", ["assignee_id"])

def downgrade() -> None:
    op.drop_table("work_history")
    op.drop_table("work_order_events")
    op.drop_table("work_checklist_items")
    op.drop_table("work_orders")
