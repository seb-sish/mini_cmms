"""003_faults_table

Revision ID: 003_faults_table
Revises: 002_equipment_table
Create Date: 2026-10-24 22:18:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision: str = "003_faults_table"
down_revision: Union[str, None] = "002_equipment_table"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.create_table(
        "faults",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("equipment_id", UUID(as_uuid=True), sa.ForeignKey("equipment.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("detected_on", sa.Date(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="OPEN"),
        sa.Column("author_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_faults_equipment_id", "faults", ["equipment_id"])
    op.create_index("ix_faults_status", "faults", ["status"])
    op.create_index("ix_faults_author_id", "faults", ["author_id"])
    op.create_index("ix_faults_detected_on", "faults", ["detected_on"])

def downgrade() -> None:
    op.drop_table("faults")
