"""make_user_login_and_email_unique_indexes_case_insensitive

Revision ID: ab5c0d78facc
Revises: 30e9606383f0
Create Date: 2026-11-15 17:30:22.082682

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "ab5c0d78facc"
down_revision: Union[str, Sequence[str], None] = "30e9606383f0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_index("uq_users_login_active", table_name="users")
    op.drop_index("uq_users_email_active", table_name="users")
    op.create_index(
        "uq_users_login_active",
        "users",
        [sa.text("lower(login)")],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
        sqlite_where=sa.text("deleted_at IS NULL"),
    )
    op.create_index(
        "uq_users_email_active",
        "users",
        [sa.text("lower(email)")],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL AND email IS NOT NULL"),
        sqlite_where=sa.text("deleted_at IS NULL AND email IS NOT NULL"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("uq_users_login_active", table_name="users")
    op.drop_index("uq_users_email_active", table_name="users")
    op.create_index(
        "uq_users_email_active",
        "users",
        ["email"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL AND email IS NOT NULL"),
        sqlite_where=sa.text("deleted_at IS NULL AND email IS NOT NULL"),
    )
    op.create_index(
        "uq_users_login_active",
        "users",
        ["login"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
        sqlite_where=sa.text("deleted_at IS NULL"),
    )
