"""007_work_orders_active_uq

Revision ID: 007_work_orders_active_uq
Revises: 006_notifications_table
Create Date: 2026-10-25 12:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '007_work_orders_active_uq'
down_revision: Union[str, None] = '006_notifications_table'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

ACTIVE_STATUS_TUPLE = "('CREATED', 'ASSIGNED', 'IN_PROGRESS', 'COMPLETED')"

def upgrade() -> None:
    conn = op.get_bind()

    # Read-only preflight check: check for any active duplicates on faults
    fault_dups = conn.execute(sa.text(f"""
        SELECT fault_id, count(*) as cnt
        FROM work_orders
        WHERE fault_id IS NOT NULL AND status IN {ACTIVE_STATUS_TUPLE}
        GROUP BY fault_id
        HAVING count(*) > 1
    """)).fetchall()
    if fault_dups:
        dups_info = []
        for r in fault_dups:
            f_id = r[0]
            ids = [str(row[0]) for row in conn.execute(sa.text(
                f"SELECT id FROM work_orders WHERE fault_id = '{f_id}' AND status IN {ACTIVE_STATUS_TUPLE}"
            )).fetchall()]
            dups_info.append(f"fault_id={f_id}: work_order_ids={ids}")
        raise RuntimeError(
            f"Cannot apply migration 007: found duplicate active work orders for faults: {'; '.join(dups_info)}"
        )

    # Read-only preflight check: check for any active duplicates on schedules
    sched_dups = conn.execute(sa.text(f"""
        SELECT schedule_id, count(*) as cnt
        FROM work_orders
        WHERE schedule_id IS NOT NULL AND status IN {ACTIVE_STATUS_TUPLE}
        GROUP BY schedule_id
        HAVING count(*) > 1
    """)).fetchall()
    if sched_dups:
        dups_info = []
        for r in sched_dups:
            s_id = r[0]
            ids = [str(row[0]) for row in conn.execute(sa.text(
                f"SELECT id FROM work_orders WHERE schedule_id = '{s_id}' AND status IN {ACTIVE_STATUS_TUPLE}"
            )).fetchall()]
            dups_info.append(f"schedule_id={s_id}: work_order_ids={ids}")
        raise RuntimeError(
            f"Cannot apply migration 007: found duplicate active work orders for schedules: {'; '.join(dups_info)}"
        )

    op.create_index(
        'uq_work_orders_active_fault',
        'work_orders',
        ['fault_id'],
        unique=True,
        postgresql_where=sa.text(f"fault_id IS NOT NULL AND status IN {ACTIVE_STATUS_TUPLE}"),
        sqlite_where=sa.text(f"fault_id IS NOT NULL AND status IN {ACTIVE_STATUS_TUPLE}"),
    )
    op.create_index(
        'uq_work_orders_active_schedule',
        'work_orders',
        ['schedule_id'],
        unique=True,
        postgresql_where=sa.text(f"schedule_id IS NOT NULL AND status IN {ACTIVE_STATUS_TUPLE}"),
        sqlite_where=sa.text(f"schedule_id IS NOT NULL AND status IN {ACTIVE_STATUS_TUPLE}"),
    )

def downgrade() -> None:
    op.drop_index('uq_work_orders_active_schedule', table_name='work_orders')
    op.drop_index('uq_work_orders_active_fault', table_name='work_orders')
