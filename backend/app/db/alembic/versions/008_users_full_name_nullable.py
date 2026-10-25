"""008_users_full_name_nullable

Revision ID: 008_users_full_name_nullable
Revises: 007_work_orders_active_uq
Create Date: 2026-10-25 15:26:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "008_users_full_name_nullable"
down_revision: str | None = "007_work_orders_active_uq"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # full_name необязателен по контракту (UserCreate требует только login, password, role),
    # поэтому колонка должна допускать NULL.
    op.alter_column("users", "full_name", existing_type=sa.VARCHAR(length=100), nullable=True)


def downgrade() -> None:
    op.alter_column("users", "full_name", existing_type=sa.VARCHAR(length=100), nullable=False)
