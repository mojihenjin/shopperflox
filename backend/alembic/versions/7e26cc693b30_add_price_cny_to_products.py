"""add_price_cny_to_products

Revision ID: 7e26cc693b30
Revises: 99d4731c0def
Create Date: 2026-11-17 17:06:30.889284

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "7e26cc693b30"
down_revision: Union[str, Sequence[str], None] = "99d4731c0def"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "products",
        sa.Column("price_cny", sa.Numeric(precision=12, scale=2), nullable=True),
    )
    op.create_check_constraint(
        "chk_products_price_cny_non_negative",
        "products",
        "price_cny IS NULL OR price_cny >= 0",
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint("chk_products_price_cny_non_negative", "products", type_="check")
    op.drop_column("products", "price_cny")
