"""004_maintenance_tables

Revision ID: 004_maintenance_tables
Revises: 003_faults_table
Create Date: 2026-10-24 22:20:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision: str = "004_maintenance_tables"
down_revision: Union[str, None] = "003_faults_table"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.create_table(
        "maintenance_plans",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("scope", sa.String(20), nullable=False),
        sa.Column("equipment_id", UUID(as_uuid=True), sa.ForeignKey("equipment.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("category", sa.String(100), nullable=True),
        sa.Column("interval_days", sa.Integer(), nullable=False),
        sa.Column("first_due_on", sa.Date(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("checklist", sa.JSON().with_variant(JSONB, "postgresql"), nullable=False, server_default="[]"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_maintenance_plans_scope", "maintenance_plans", ["scope"])
    op.create_index("ix_maintenance_plans_equipment_id", "maintenance_plans", ["equipment_id"])
    op.create_index("ix_maintenance_plans_category", "maintenance_plans", ["category"])
    op.create_index("ix_maintenance_plans_is_active", "maintenance_plans", ["is_active"])

    op.create_table(
        "maintenance_schedules",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("plan_id", UUID(as_uuid=True), sa.ForeignKey("maintenance_plans.id", ondelete="CASCADE"), nullable=False),
        sa.Column("equipment_id", UUID(as_uuid=True), sa.ForeignKey("equipment.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("next_due_on", sa.Date(), nullable=False),
        sa.Column("last_completed_on", sa.Date(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("uq_maintenance_schedules_plan_equipment", "maintenance_schedules", ["plan_id", "equipment_id"], unique=True)
    op.create_index("ix_maintenance_schedules_next_due_on", "maintenance_schedules", ["next_due_on"])
    op.create_index("ix_maintenance_schedules_is_active", "maintenance_schedules", ["is_active"])

def downgrade() -> None:
    op.drop_table("maintenance_schedules")
    op.drop_table("maintenance_plans")
