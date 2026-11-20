from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    SmallInteger,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from uuid6 import uuid7

from .base import Base

if TYPE_CHECKING:
    from .user import UserModel


class BrandModel(Base):
    __tablename__ = "brands"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid7)
    name: Mapped[str] = mapped_column(
        String(150), unique=True, nullable=False, index=True
    )
    slug: Mapped[str] = mapped_column(
        String(180), unique=True, nullable=False, index=True
    )
    his_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    logo_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    is_deleted: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false", nullable=False, index=True
    )
    views_count: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0", nullable=False
    )
    orders_count: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0", nullable=False
    )
    moderation_status: Mapped[str] = mapped_column(
        String(20),
        default="pending",
        server_default="pending",
        nullable=False,
        index=True,
    )
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_verified: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false", nullable=False, index=True
    )
    products_hidden_override: Mapped[int | None] = mapped_column(
        SmallInteger, nullable=True, default=None
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    members: Mapped[list["BrandMemberModel"]] = relationship(
        back_populates="brand", cascade="all, delete-orphan"
    )

    __table_args__ = (
        CheckConstraint(
            "products_hidden_override IS NULL OR products_hidden_override IN (1, 2)",
            name="chk_brands_products_hidden_override",
        ),
    )


class BrandMemberModel(Base):
    __tablename__ = "brand_members"

    brand_id: Mapped[UUID] = mapped_column(
        ForeignKey("brands.id", ondelete="CASCADE"), primary_key=True
    )
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True, index=True
    )
    role: Mapped[str] = mapped_column(String(30), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    brand: Mapped["BrandModel"] = relationship(back_populates="members")
    user: Mapped["UserModel"] = relationship()
