"""users_add_plan_storage

Revision ID: 62f12763d900
Revises: 83da797488b8
Create Date: 2026-07-01 18:47:07.536098

"""

from typing import Sequence, Union

from alembic import op
# import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "62f12763d900"
down_revision: Union[str, Sequence[str], None] = "83da797488b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE users ADD COLUMN IF NOT EXISTS plan_type TEXT NOT NULL DEFAULT 'FREE';
        ALTER TABLE users ADD COLUMN IF NOT EXISTS storage_used_bytes BIGINT NOT NULL DEFAULT 0;
        """
    )


def downgrade() -> None:
    """Downgrade schema."""
    pass
