"""009_contract_column_lengths

Revision ID: 009_contract_column_lengths
Revises: 008_users_full_name_nullable
Create Date: 2026-10-25 19:26:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "009_contract_column_lengths"
down_revision: str | None = "008_users_full_name_nullable"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Длины приведены к максимальным значениям нормативного контракта:
# Equipment.name/location — 200, Equipment.inventory_number — 64,
# MaintenancePlan.name — 200, User.login — 64.
# Расширение VARCHAR в PostgreSQL сохраняет данные.
_WIDENED = (
    ("equipment", "name", 100, 200),
    ("equipment", "inventory_number", 50, 64),
    ("equipment", "location", 100, 200),
    ("maintenance_plans", "name", 100, 200),
    ("users", "login", 50, 64),
)


def upgrade() -> None:
    for table, column, old_length, new_length in _WIDENED:
        op.alter_column(
            table,
            column,
            existing_type=sa.VARCHAR(length=old_length),
            type_=sa.String(length=new_length),
            existing_nullable=False,
        )


def downgrade() -> None:
    for table, column, old_length, new_length in reversed(_WIDENED):
        op.alter_column(
            table,
            column,
            existing_type=sa.VARCHAR(length=new_length),
            type_=sa.VARCHAR(length=old_length),
            existing_nullable=False,
        )
