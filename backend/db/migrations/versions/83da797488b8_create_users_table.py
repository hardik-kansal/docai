"""create_users_table

Revision ID: 83da797488b8
Revises:
Create Date: 2026-06-24 16:15:09.005614

"""

from typing import Sequence, Union

from alembic import op
# import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "83da797488b8"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE EXTENSION IF NOT EXISTS "pgcrypto";  -- for gen_random_uuid() 

        CREATE TABLE IF NOT EXISTS users (
            user_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),  -- PRIMARY KEY = Automatically indexed
            username  TEXT NOT NULL UNIQUE,  -- UNIQUE = Automatically indexed
            password_hash TEXT NOT NULL,
            scopes    TEXT[] NOT NULL DEFAULT '{}',
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );

        """
    )


# does not have any .hex() thats why used UUID, (afa-agadg-agadg-adgda11)
# convert to str using .hex() in User Repository "afaagadgagadgadgda11"
# uuid.uuid4 is version 4 just, have nothing to do with bytes, and its random
# timestampz is timestamp with timezone.utc


def downgrade() -> None:
    op.execute("""
    DROP TABLE USERS
    """)
    pass
