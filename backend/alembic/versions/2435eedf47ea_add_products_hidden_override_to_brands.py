"""add_products_hidden_override_to_brands

Revision ID: 2435eedf47ea
Revises: 7e26cc693b30
Create Date: 2026-11-17 17:28:19.248723

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "2435eedf47ea"
down_revision: Union[str, Sequence[str], None] = "7e26cc693b30"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "brands",
        sa.Column("products_hidden_override", sa.SmallInteger(), nullable=True),
    )
    op.create_check_constraint(
        "chk_brands_products_hidden_override",
        "brands",
        "products_hidden_override IS NULL OR products_hidden_override IN (1, 2)",
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint("chk_brands_products_hidden_override", "brands", type_="check")
    op.drop_column("brands", "products_hidden_override")
