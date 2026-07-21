"""google_oauth

Revision ID: dfa47d9818c9
Revises: 9a6995dea22e
Create Date: 2026-07-21 21:43:30.118759

"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "dfa47d9818c9"
down_revision: Union[str, Sequence[str], None] = "9a6995dea22e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute(
        """
        TRUNCATE TABLE users CASCADE;
        
        ALTER TABLE users
        ADD COLUMN email TEXT UNIQUE NOT NULL,
        ADD COLUMN google_sub TEXT UNIQUE NOT NULL;
        
        ALTER TABLE users
        DROP COLUMN password_hash;
        """
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute(
        """
        ALTER TABLE users
        ADD COLUMN password_hash TEXT NOT NULL DEFAULT '';
        
        ALTER TABLE users
        DROP COLUMN google_sub,
        DROP COLUMN email;
        """
    )
