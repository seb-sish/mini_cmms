"""006_notifications_table

Revision ID: 006_notifications_table
Revises: 005_work_orders_tables
Create Date: 2026-10-24 22:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '006_notifications_table'
down_revision: Union[str, None] = '005_work_orders_tables'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.create_table(
        'notifications',
        sa.Column('id', sa.UUID(as_uuid=True), primary_key=True),
        sa.Column('recipient_id', sa.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('plan_id', sa.UUID(as_uuid=True), sa.ForeignKey('maintenance_plans.id', ondelete='CASCADE'), nullable=False),
        sa.Column('schedule_id', sa.UUID(as_uuid=True), sa.ForeignKey('maintenance_schedules.id', ondelete='CASCADE'), nullable=False),
        sa.Column('equipment_id', sa.UUID(as_uuid=True), sa.ForeignKey('equipment.id', ondelete='CASCADE'), nullable=False),
        sa.Column('planned_due_on', sa.Date(), nullable=False),
        sa.Column('type', sa.String(length=50), nullable=False),
        sa.Column('message', sa.String(length=500), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        'uq_notifications_idempotent',
        'notifications',
        ['schedule_id', 'planned_due_on', 'type', 'recipient_id'],
        unique=True,
    )
    op.create_index('ix_notifications_recipient_id', 'notifications', ['recipient_id'])
    op.create_index('ix_notifications_created_at', 'notifications', ['created_at'])

def downgrade() -> None:
    op.drop_table('notifications')
