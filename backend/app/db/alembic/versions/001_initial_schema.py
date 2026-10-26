"""Начальная схема Mini-CMMS.

Revision ID: 001
Сохранены структура, порядок столбцов и серверные defaults прежней цепочки 001–009."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "equipment",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("inventory_number", sa.String(length=64), nullable=False),
        sa.Column("category", sa.String(length=100), nullable=False),
        sa.Column("location", sa.String(length=200), nullable=False),
        sa.Column(
            "status", sa.String(length=20), nullable=False, server_default=sa.text("'OPERATIONAL'::character varying")
        ),
        sa.Column("commissioned_on", sa.Date(), nullable=False),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_equipment_archived_at", "equipment", ["archived_at"], unique=False)
    op.create_index("ix_equipment_category", "equipment", ["category"], unique=False)
    op.create_index("ix_equipment_location", "equipment", ["location"], unique=False)
    op.create_index("ix_equipment_status", "equipment", ["status"], unique=False)
    op.create_index("uq_equipment_inventory_number", "equipment", ["inventory_number"], unique=True)
    op.create_table(
        "users",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("login", sa.String(length=64), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=100), nullable=True),
        sa.Column(
            "role", sa.String(length=20), nullable=False, server_default=sa.text("'OPERATOR'::character varying")
        ),
        sa.Column(
            "status", sa.String(length=20), nullable=False, server_default=sa.text("'ACTIVE'::character varying")
        ),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("uq_users_lower_login", "users", [sa.literal_column("lower(login)")], unique=True)
    op.create_table(
        "faults",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("equipment_id", sa.UUID(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("detected_on", sa.Date(), nullable=False),
        sa.Column(
            "severity", sa.String(length=20), nullable=False, server_default=sa.text("'MEDIUM'::character varying")
        ),
        sa.Column("status", sa.String(length=20), nullable=False, server_default=sa.text("'OPEN'::character varying")),
        sa.Column("author_id", sa.UUID(), nullable=False),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["author_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["equipment_id"], ["equipment.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_faults_author_id", "faults", ["author_id"], unique=False)
    op.create_index("ix_faults_detected_on", "faults", ["detected_on"], unique=False)
    op.create_index("ix_faults_equipment_id", "faults", ["equipment_id"], unique=False)
    op.create_index("ix_faults_severity", "faults", ["severity"], unique=False)
    op.create_index("ix_faults_status", "faults", ["status"], unique=False)
    op.create_table(
        "maintenance_plans",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("scope", sa.String(length=20), nullable=False),
        sa.Column("equipment_id", sa.UUID(), nullable=True),
        sa.Column("category", sa.String(length=100), nullable=True),
        sa.Column("interval_days", sa.Integer(), nullable=False),
        sa.Column("first_due_on", sa.Date(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column(
            "checklist",
            sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["equipment_id"], ["equipment.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_maintenance_plans_category", "maintenance_plans", ["category"], unique=False)
    op.create_index("ix_maintenance_plans_equipment_id", "maintenance_plans", ["equipment_id"], unique=False)
    op.create_index("ix_maintenance_plans_is_active", "maintenance_plans", ["is_active"], unique=False)
    op.create_index("ix_maintenance_plans_scope", "maintenance_plans", ["scope"], unique=False)
    op.create_table(
        "user_sessions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_user_sessions_user_id", "user_sessions", ["user_id"], unique=False)
    op.create_index("uq_user_sessions_token_hash", "user_sessions", ["token_hash"], unique=True)
    op.create_table(
        "maintenance_schedules",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("plan_id", sa.UUID(), nullable=False),
        sa.Column("equipment_id", sa.UUID(), nullable=False),
        sa.Column("next_due_on", sa.Date(), nullable=False),
        sa.Column("last_completed_on", sa.Date(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["equipment_id"], ["equipment.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["plan_id"], ["maintenance_plans.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_maintenance_schedules_is_active", "maintenance_schedules", ["is_active"], unique=False)
    op.create_index("ix_maintenance_schedules_next_due_on", "maintenance_schedules", ["next_due_on"], unique=False)
    op.create_index(
        "uq_maintenance_schedules_plan_equipment", "maintenance_schedules", ["plan_id", "equipment_id"], unique=True
    )
    op.create_table(
        "notifications",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("recipient_id", sa.UUID(), nullable=False),
        sa.Column("plan_id", sa.UUID(), nullable=False),
        sa.Column("schedule_id", sa.UUID(), nullable=False),
        sa.Column("equipment_id", sa.UUID(), nullable=False),
        sa.Column("planned_due_on", sa.Date(), nullable=False),
        sa.Column("type", sa.String(length=50), nullable=False),
        sa.Column("message", sa.String(length=500), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["equipment_id"], ["equipment.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["plan_id"], ["maintenance_plans.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["recipient_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["schedule_id"], ["maintenance_schedules.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_notifications_created_at", "notifications", ["created_at"], unique=False)
    op.create_index("ix_notifications_recipient_id", "notifications", ["recipient_id"], unique=False)
    op.create_index(
        "uq_notifications_idempotent",
        "notifications",
        ["schedule_id", "planned_due_on", "type", "recipient_id"],
        unique=True,
    )
    op.create_table(
        "work_orders",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("number", sa.String(length=50), nullable=False),
        sa.Column("type", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column(
            "priority", sa.String(length=20), nullable=False, server_default=sa.text("'NORMAL'::character varying")
        ),
        sa.Column("equipment_id", sa.UUID(), nullable=False),
        sa.Column("fault_id", sa.UUID(), nullable=True),
        sa.Column("schedule_id", sa.UUID(), nullable=True),
        sa.Column("planned_due_on", sa.Date(), nullable=True),
        sa.Column("author_id", sa.UUID(), nullable=False),
        sa.Column("assignee_id", sa.UUID(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("closed_by", sa.UUID(), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_by", sa.UUID(), nullable=True),
        sa.Column("cancellation_reason", sa.Text(), nullable=True),
        sa.Column("result", sa.Text(), nullable=True),
        sa.Column(
            "replaced_parts",
            sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.ForeignKeyConstraint(["assignee_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["author_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["cancelled_by"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["closed_by"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["equipment_id"], ["equipment.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["fault_id"], ["faults.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["schedule_id"], ["maintenance_schedules.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_work_orders_assignee_id", "work_orders", ["assignee_id"], unique=False)
    op.create_index("ix_work_orders_created_at", "work_orders", ["created_at"], unique=False)
    op.create_index("ix_work_orders_equipment_id", "work_orders", ["equipment_id"], unique=False)
    op.create_index("ix_work_orders_fault_id", "work_orders", ["fault_id"], unique=False)
    op.create_index("ix_work_orders_schedule_id", "work_orders", ["schedule_id"], unique=False)
    op.create_index("ix_work_orders_status", "work_orders", ["status"], unique=False)
    op.create_index("ix_work_orders_type", "work_orders", ["type"], unique=False)
    op.create_index(
        "uq_work_orders_active_fault",
        "work_orders",
        ["fault_id"],
        unique=True,
        postgresql_where=sa.text(
            "fault_id IS NOT NULL AND status IN ('CREATED', 'ASSIGNED', 'IN_PROGRESS', 'COMPLETED')"
        ),
        sqlite_where=sa.text("fault_id IS NOT NULL AND status IN ('CREATED', 'ASSIGNED', 'IN_PROGRESS', 'COMPLETED')"),
    )
    op.create_index(
        "uq_work_orders_active_schedule",
        "work_orders",
        ["schedule_id"],
        unique=True,
        postgresql_where=sa.text(
            "schedule_id IS NOT NULL AND status IN ('CREATED', 'ASSIGNED', 'IN_PROGRESS', 'COMPLETED')"
        ),
        sqlite_where=sa.text(
            "schedule_id IS NOT NULL AND status IN ('CREATED', 'ASSIGNED', 'IN_PROGRESS', 'COMPLETED')"
        ),
    )
    op.create_index("uq_work_orders_number", "work_orders", ["number"], unique=True)
    op.create_table(
        "work_checklist_items",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("work_order_id", sa.UUID(), nullable=False),
        sa.Column("order", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("required", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("checked", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("checked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["work_order_id"], ["work_orders.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_work_checklist_items_work_order_id", "work_checklist_items", ["work_order_id"], unique=False)
    op.create_table(
        "work_history",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("work_order_id", sa.UUID(), nullable=False),
        sa.Column("equipment_id", sa.UUID(), nullable=False),
        sa.Column("plan_id", sa.UUID(), nullable=True),
        sa.Column("fault_id", sa.UUID(), nullable=True),
        sa.Column("technician_id", sa.UUID(), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("result", sa.Text(), nullable=False),
        sa.Column(
            "replaced_parts",
            sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["equipment_id"], ["equipment.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["fault_id"], ["faults.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["plan_id"], ["maintenance_plans.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["technician_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["work_order_id"], ["work_orders.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_work_history_completed_at", "work_history", ["completed_at"], unique=False)
    op.create_index("ix_work_history_equipment_id", "work_history", ["equipment_id"], unique=False)
    op.create_index("ix_work_history_technician_id", "work_history", ["technician_id"], unique=False)
    op.create_index("uq_work_history_work_order_id", "work_history", ["work_order_id"], unique=True)
    op.create_table(
        "work_order_events",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("work_order_id", sa.UUID(), nullable=False),
        sa.Column("event_type", sa.String(length=50), nullable=False),
        sa.Column("actor_id", sa.UUID(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("from_status", sa.String(length=20), nullable=True),
        sa.Column("to_status", sa.String(length=20), nullable=True),
        sa.Column("old_assignee_id", sa.UUID(), nullable=True),
        sa.Column("new_assignee_id", sa.UUID(), nullable=True),
        sa.Column("details", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["actor_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["new_assignee_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["old_assignee_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["work_order_id"], ["work_orders.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_work_order_events_occurred_at", "work_order_events", ["occurred_at"], unique=False)
    op.create_index("ix_work_order_events_work_order_id", "work_order_events", ["work_order_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_work_order_events_work_order_id", table_name="work_order_events")
    op.drop_index("ix_work_order_events_occurred_at", table_name="work_order_events")
    op.drop_table("work_order_events")
    op.drop_index("uq_work_history_work_order_id", table_name="work_history")
    op.drop_index("ix_work_history_technician_id", table_name="work_history")
    op.drop_index("ix_work_history_equipment_id", table_name="work_history")
    op.drop_index("ix_work_history_completed_at", table_name="work_history")
    op.drop_table("work_history")
    op.drop_index("ix_work_checklist_items_work_order_id", table_name="work_checklist_items")
    op.drop_table("work_checklist_items")
    op.drop_index("uq_work_orders_number", table_name="work_orders")
    op.drop_index(
        "uq_work_orders_active_schedule",
        table_name="work_orders",
        postgresql_where=sa.text(
            "schedule_id IS NOT NULL AND status IN ('CREATED', 'ASSIGNED', 'IN_PROGRESS', 'COMPLETED')"
        ),
        sqlite_where=sa.text(
            "schedule_id IS NOT NULL AND status IN ('CREATED', 'ASSIGNED', 'IN_PROGRESS', 'COMPLETED')"
        ),
    )
    op.drop_index(
        "uq_work_orders_active_fault",
        table_name="work_orders",
        postgresql_where=sa.text(
            "fault_id IS NOT NULL AND status IN ('CREATED', 'ASSIGNED', 'IN_PROGRESS', 'COMPLETED')"
        ),
        sqlite_where=sa.text("fault_id IS NOT NULL AND status IN ('CREATED', 'ASSIGNED', 'IN_PROGRESS', 'COMPLETED')"),
    )
    op.drop_index("ix_work_orders_type", table_name="work_orders")
    op.drop_index("ix_work_orders_status", table_name="work_orders")
    op.drop_index("ix_work_orders_schedule_id", table_name="work_orders")
    op.drop_index("ix_work_orders_fault_id", table_name="work_orders")
    op.drop_index("ix_work_orders_equipment_id", table_name="work_orders")
    op.drop_index("ix_work_orders_created_at", table_name="work_orders")
    op.drop_index("ix_work_orders_assignee_id", table_name="work_orders")
    op.drop_table("work_orders")
    op.drop_index("uq_notifications_idempotent", table_name="notifications")
    op.drop_index("ix_notifications_recipient_id", table_name="notifications")
    op.drop_index("ix_notifications_created_at", table_name="notifications")
    op.drop_table("notifications")
    op.drop_index("uq_maintenance_schedules_plan_equipment", table_name="maintenance_schedules")
    op.drop_index("ix_maintenance_schedules_next_due_on", table_name="maintenance_schedules")
    op.drop_index("ix_maintenance_schedules_is_active", table_name="maintenance_schedules")
    op.drop_table("maintenance_schedules")
    op.drop_index("uq_user_sessions_token_hash", table_name="user_sessions")
    op.drop_index("ix_user_sessions_user_id", table_name="user_sessions")
    op.drop_table("user_sessions")
    op.drop_index("ix_maintenance_plans_scope", table_name="maintenance_plans")
    op.drop_index("ix_maintenance_plans_is_active", table_name="maintenance_plans")
    op.drop_index("ix_maintenance_plans_equipment_id", table_name="maintenance_plans")
    op.drop_index("ix_maintenance_plans_category", table_name="maintenance_plans")
    op.drop_table("maintenance_plans")
    op.drop_index("ix_faults_status", table_name="faults")
    op.drop_index("ix_faults_severity", table_name="faults")
    op.drop_index("ix_faults_equipment_id", table_name="faults")
    op.drop_index("ix_faults_detected_on", table_name="faults")
    op.drop_index("ix_faults_author_id", table_name="faults")
    op.drop_table("faults")
    op.drop_index("uq_users_lower_login", table_name="users")
    op.drop_table("users")
    op.drop_index("uq_equipment_inventory_number", table_name="equipment")
    op.drop_index("ix_equipment_status", table_name="equipment")
    op.drop_index("ix_equipment_location", table_name="equipment")
    op.drop_index("ix_equipment_category", table_name="equipment")
    op.drop_index("ix_equipment_archived_at", table_name="equipment")
    op.drop_table("equipment")
