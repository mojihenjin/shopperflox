"""add uq_user_bans_active partial unique index

Revision ID: 596cae004e59
Revises: b8e5ff056821
Create Date: 2026-11-15 06:53:27.204626

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "596cae004e59"
down_revision: Union[str, Sequence[str], None] = "b8e5ff056821"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_index(
        "uq_user_bans_active",
        "user_bans",
        ["user_id"],
        unique=True,
        postgresql_where=sa.text("ended_at IS NULL"),
        sqlite_where=sa.text("ended_at IS NULL"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        "uq_user_bans_active",
        table_name="user_bans",
    )
