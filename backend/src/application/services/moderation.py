from datetime import datetime
from uuid import UUID

from src.domain.exceptions import (
    DomainValidationError,
    EntityAlreadyExistsError,
    EntityNotFoundError,
    PermissionDeniedError,
)
from src.domain.interfaces import UserUnitOfWorkProtocol
from src.domain.models import UserBanDomain, UserDomain
from src.utils import factory_now


class UserModerationService:
    def __init__(self, uow: UserUnitOfWorkProtocol) -> None:
        self.uow = uow

    async def ban_user(
        self,
        *,
        moderator_id: UUID,
        target_user_id: UUID,
        reason: str,
        ended_at: datetime | None = None,
    ) -> UserBanDomain:
        if moderator_id == target_user_id:
            raise DomainValidationError("Cannot ban yourself")

        async with self.uow:
            moderator = await self.uow.users.get_by_id(moderator_id)
            if (
                moderator is None
                or moderator.is_deleted
                or (
                    "users:ban" not in moderator.global_permissions
                    and "*" not in moderator.global_permissions
                )
            ):
                raise PermissionDeniedError("Permission 'users:ban' required")

            target = await self.uow.users.get_by_id(target_user_id)
            if target is None or target.is_deleted:
                raise EntityNotFoundError("Target user not found")

            active_ban = await self.uow.bans.get_active_by_user_id(target_user_id)
            if active_ban and active_ban.is_active():
                raise EntityAlreadyExistsError("User is already actively banned")

            ban = UserBanDomain(
                user_id=target_user_id,
                reason=reason,
                ended_at=ended_at,
                created_by=moderator_id,
            )
            await self.uow.bans.add(ban)
            await self.uow.commit()
            return ban

    async def unban_user(
        self,
        *,
        moderator_id: UUID,
        target_user_id: UUID,
    ) -> UserBanDomain:
        async with self.uow:
            moderator = await self.uow.users.get_by_id(moderator_id)
            if (
                moderator is None
                or moderator.is_deleted
                or (
                    "users:ban" not in moderator.global_permissions
                    and "*" not in moderator.global_permissions
                )
            ):
                raise PermissionDeniedError("Permission 'users:ban' required")

            target = await self.uow.users.get_by_id(target_user_id)
            if target is None or target.is_deleted:
                raise EntityNotFoundError("Target user not found")

            now = factory_now()
            active_bans = await self.uow.bans.list_active_by_user_id(
                target_user_id, at=now
            )
            if not active_bans:
                raise EntityNotFoundError("No active ban found for user")

            for ban in active_bans:
                ban.ended_at = now
                await self.uow.bans.update(ban)

            await self.uow.commit()
            return active_bans[0]

    async def set_permissions(
        self,
        *,
        admin_id: UUID,
        target_user_id: UUID,
        permissions: list[str],
    ) -> UserDomain:
        async with self.uow:
            admin = await self.uow.users.get_by_id(admin_id)
            if (
                admin is None
                or admin.is_deleted
                or (
                    "users:permissions" not in admin.global_permissions
                    and "*" not in admin.global_permissions
                )
            ):
                raise PermissionDeniedError("Permission 'users:permissions' required")

            target = await self.uow.users.get_by_id(target_user_id)
            if target is None or target.is_deleted:
                raise EntityNotFoundError("Target user not found")

            # Deduplicate preserving order
            target.global_permissions = list(dict.fromkeys(permissions))
            target.updated_at = factory_now()
            await self.uow.users.update(target)
            await self.uow.commit()
            return target
