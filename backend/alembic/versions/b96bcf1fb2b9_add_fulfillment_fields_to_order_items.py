"""add_fulfillment_fields_to_order_items

Revision ID: b96bcf1fb2b9
Revises: 2435eedf47ea
Create Date: 2026-11-17 18:01:07.250691

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b96bcf1fb2b9"
down_revision: Union[str, Sequence[str], None] = "2435eedf47ea"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "order_items",
        sa.Column(
            "fulfillment_status",
            sa.String(length=32),
            nullable=False,
            server_default="pending",
        ),
    )
    op.add_column(
        "order_items",
        sa.Column("post_code", sa.String(length=100), nullable=True),
    )
    op.add_column(
        "order_items",
        sa.Column("tracking_url", sa.String(length=512), nullable=True),
    )
    op.add_column(
        "order_items",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_check_constraint(
        "chk_order_items_fulfillment_status",
        "order_items",
        "fulfillment_status IN ('pending', 'packing', 'handed_to_post', 'in_transit', 'delivered')",
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint(
        "chk_order_items_fulfillment_status", "order_items", type_="check"
    )
    op.drop_column("order_items", "updated_at")
    op.drop_column("order_items", "tracking_url")
    op.drop_column("order_items", "post_code")
    op.drop_column("order_items", "fulfillment_status")
