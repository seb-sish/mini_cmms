"""002_equipment_table

Revision ID: 002_equipment_table
Revises: 001_initial_users_and_sessions
Create Date: 2026-10-24 22:17:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision: str = "002_equipment_table"
down_revision: Union[str, None] = "001_initial_users_and_sessions"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.create_table(
        "equipment",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("inventory_number", sa.String(50), nullable=False),
        sa.Column("category", sa.String(100), nullable=False),
        sa.Column("location", sa.String(100), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="OPERATIONAL"),
        sa.Column("commissioned_on", sa.Date(), nullable=False),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("uq_equipment_inventory_number", "equipment", ["inventory_number"], unique=True)
    op.create_index("ix_equipment_category", "equipment", ["category"])
    op.create_index("ix_equipment_location", "equipment", ["location"])
    op.create_index("ix_equipment_status", "equipment", ["status"])
    op.create_index("ix_equipment_archived_at", "equipment", ["archived_at"])

def downgrade() -> None:
    op.drop_table("equipment")
