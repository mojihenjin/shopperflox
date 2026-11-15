from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, ForeignKey, Index, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class UserModel(Base):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    login: Mapped[str] = mapped_column(String(64), nullable=False)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    verified_profile: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    verified_email: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    global_permissions: Mapped[list[str]] = mapped_column(default=list, nullable=False)
    created_by: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(nullable=False)
    updated_at: Mapped[datetime] = mapped_column(nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(nullable=True)

    __table_args__ = (
        Index(
            "uq_users_login_active",
            text("lower(login)"),
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
            sqlite_where=text("deleted_at IS NULL"),
        ),
        Index(
            "uq_users_email_active",
            text("lower(email)"),
            unique=True,
            postgresql_where=text("deleted_at IS NULL AND email IS NOT NULL"),
            sqlite_where=text("deleted_at IS NULL AND email IS NOT NULL"),
        ),
    )


class UserPersonalModel(Base):
    __tablename__ = "user_personal"

    id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    firstname: Mapped[str | None] = mapped_column(String(128), nullable=True)
    lastname: Mapped[str | None] = mapped_column(String(128), nullable=True)
    phone_number: Mapped[str | None] = mapped_column(String(32), nullable=True)
    created_by: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(nullable=False)
    updated_at: Mapped[datetime] = mapped_column(nullable=False)

    __table_args__ = (
        Index(
            "uq_user_personal_phone",
            "phone_number",
            unique=True,
            postgresql_where=text("phone_number IS NOT NULL"),
            sqlite_where=text("phone_number IS NOT NULL"),
        ),
    )


class UserBanModel(Base):
    __tablename__ = "user_bans"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    created_by: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(nullable=False)
    ended_at: Mapped[datetime | None] = mapped_column(nullable=True)

    __table_args__ = (
        Index(
            "uq_user_bans_active",
            "user_id",
            unique=True,
            postgresql_where=text("ended_at IS NULL"),
            sqlite_where=text("ended_at IS NULL"),
        ),
    )


class UserAddressModel(Base):
    __tablename__ = "user_addresses"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    city: Mapped[str] = mapped_column(String(128), nullable=False)
    street: Mapped[str] = mapped_column(String(255), nullable=False)
    postal_code: Mapped[str] = mapped_column(String(32), nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_by: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(nullable=False)

    __table_args__ = (
        Index(
            "uq_user_addresses_default",
            "user_id",
            unique=True,
            postgresql_where=text("is_default = TRUE"),
            sqlite_where=text("is_default = TRUE"),
        ),
    )
