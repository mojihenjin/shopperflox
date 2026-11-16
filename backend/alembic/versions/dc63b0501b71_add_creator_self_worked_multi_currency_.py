"""add creator self worked multi currency characteristics and image color

Revision ID: dc63b0501b71
Revises: e1f568063fe5
Create Date: 2026-11-16 17:02:51.656127

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "dc63b0501b71"
down_revision: Union[str, Sequence[str], None] = "e1f568063fe5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "product_images", sa.Column("color", sa.String(length=100), nullable=True)
    )
    op.create_index(
        "ix_product_images_color", "product_images", ["color"], unique=False
    )
    op.alter_column(
        "product_variants", "size", existing_type=sa.VARCHAR(length=64), nullable=True
    )
    op.alter_column(
        "product_variants",
        "color_name",
        existing_type=sa.VARCHAR(length=64),
        nullable=True,
    )
    op.add_column("products", sa.Column("creator_id", sa.Uuid(), nullable=True))
    op.add_column(
        "products",
        sa.Column(
            "is_self_worked",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
    )
    op.add_column(
        "products",
        sa.Column("price_usd", sa.Numeric(precision=12, scale=2), nullable=True),
    )
    op.add_column(
        "products",
        sa.Column("price_eur", sa.Numeric(precision=12, scale=2), nullable=True),
    )
    op.add_column(
        "products", sa.Column("material", sa.String(length=255), nullable=True)
    )
    op.add_column(
        "products", sa.Column("density", sa.String(length=128), nullable=True)
    )
    op.add_column(
        "products", sa.Column("composition", sa.String(length=255), nullable=True)
    )
    op.add_column(
        "products", sa.Column("print_method", sa.String(length=255), nullable=True)
    )
    op.add_column("products", sa.Column("note", sa.Text(), nullable=True))
    op.create_index("ix_products_creator_id", "products", ["creator_id"], unique=False)
    op.create_foreign_key(
        "fk_products_creator_id_users",
        "products",
        "users",
        ["creator_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_check_constraint(
        "chk_products_price_usd_non_negative",
        "products",
        "price_usd IS NULL OR price_usd >= 0",
    )
    op.create_check_constraint(
        "chk_products_price_eur_non_negative",
        "products",
        "price_eur IS NULL OR price_eur >= 0",
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint("chk_products_price_eur_non_negative", "products", type_="check")
    op.drop_constraint("chk_products_price_usd_non_negative", "products", type_="check")
    op.drop_constraint("fk_products_creator_id_users", "products", type_="foreignkey")
    op.drop_index("ix_products_creator_id", table_name="products")
    op.drop_column("products", "note")
    op.drop_column("products", "print_method")
    op.drop_column("products", "composition")
    op.drop_column("products", "density")
    op.drop_column("products", "material")
    op.drop_column("products", "price_eur")
    op.drop_column("products", "price_usd")
    op.drop_column("products", "is_self_worked")
    op.drop_column("products", "creator_id")
    op.alter_column(
        "product_variants",
        "color_name",
        existing_type=sa.VARCHAR(length=64),
        nullable=False,
    )
    op.alter_column(
        "product_variants", "size", existing_type=sa.VARCHAR(length=64), nullable=False
    )
    op.drop_index("ix_product_images_color", table_name="product_images")
    op.drop_column("product_images", "color")
