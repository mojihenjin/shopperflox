from uuid import UUID

from src.domain.exceptions import (
    AuthenticationError,
    DomainValidationError,
    EntityAlreadyExistsError,
    EntityNotFoundError,
    PermissionDeniedError,
)
from src.domain.interfaces import UserUnitOfWorkProtocol
from src.domain.models import (
    UserAddressDomain,
    UserDomain,
    UserPersonalDomain,
)
from src.utils import factory_now


class UserService:
    MAX_USER_ADDRESSES: int = 20

    def __init__(self, uow: UserUnitOfWorkProtocol) -> None:
        self.uow = uow

    def _ensure_actor_access(
        self, actor: UserDomain, target_user_id: UUID, admin_perm: str
    ) -> None:
        is_self = actor.id == target_user_id
        has_perm = (
            admin_perm in actor.global_permissions or "*" in actor.global_permissions
        )
        if not (is_self or has_perm):
            raise PermissionDeniedError("Access denied to user resource")

    async def get_user_profile(
        self, *, actor_id: UUID, target_user_id: UUID
    ) -> tuple[UserDomain, UserPersonalDomain | None]:
        async with self.uow:
            actor = await self.uow.users.get_by_id(actor_id)
            if actor is None or actor.is_deleted:
                raise AuthenticationError("Actor user not found or deleted")

            self._ensure_actor_access(actor, target_user_id, "users:read")

            target_user = await self.uow.users.get_by_id(target_user_id)
            if target_user is None or target_user.is_deleted:
                raise EntityNotFoundError("User not found")

            personal = await self.uow.personal.get_by_user_id(target_user_id)
            return target_user, personal

    async def get_by_login(self, login: str) -> UserDomain:
        async with self.uow:
            user = await self.uow.users.get_by_login(login)
            if user is None or user.is_deleted:
                raise EntityNotFoundError("User not found")
            return user

    async def update_personal(
        self,
        *,
        actor_id: UUID,
        target_user_id: UUID,
        firstname: str | None,
        lastname: str | None,
        phone_number: str | None = None,
        middlename: str | None = None,
    ) -> UserPersonalDomain:
        async with self.uow:
            actor = await self.uow.users.get_by_id(actor_id)
            if actor is None or actor.is_deleted:
                raise AuthenticationError("Actor user not found or deleted")

            self._ensure_actor_access(actor, target_user_id, "users:write")

            target_user = await self.uow.users.get_by_id(target_user_id)
            if target_user is None or target_user.is_deleted:
                raise EntityNotFoundError("User not found")

            if phone_number:
                existing = await self.uow.personal.get_by_phone(phone_number)
                if existing and existing.id != target_user_id:
                    raise EntityAlreadyExistsError(
                        f"Phone number '{phone_number}' is already registered"
                    )

            personal = await self.uow.personal.get_by_user_id(target_user_id)
            if personal is None:
                personal = UserPersonalDomain(
                    id=target_user_id,
                    created_by=actor_id,
                    firstname=firstname,
                    lastname=lastname,
                    middlename=middlename,
                    phone_number=phone_number,
                )
                await self.uow.personal.add(personal)
            else:
                personal.firstname = firstname
                personal.lastname = lastname
                personal.middlename = middlename
                personal.phone_number = phone_number
                personal.updated_at = factory_now()
                await self.uow.personal.update(personal)

            await self.uow.commit()
            return personal

    async def list_addresses(
        self,
        *,
        actor_id: UUID,
        target_user_id: UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> list[UserAddressDomain]:
        async with self.uow:
            actor = await self.uow.users.get_by_id(actor_id)
            if actor is None or actor.is_deleted:
                raise AuthenticationError("Actor user not found or deleted")

            self._ensure_actor_access(actor, target_user_id, "users:read")

            target_user = await self.uow.users.get_by_id(target_user_id)
            if target_user is None or target_user.is_deleted:
                raise EntityNotFoundError("User not found")

            return await self.uow.addresses.list_by_user_id(
                target_user_id, limit=limit, offset=offset
            )

    async def add_address(
        self,
        *,
        actor_id: UUID,
        target_user_id: UUID,
        city: str,
        street: str | None = None,
        house: str = "",
        apartment: str | None = None,
        postal_code: str,
        country: str = "Россия",
        region: str | None = None,
        is_default: bool = False,
    ) -> UserAddressDomain:
        async with self.uow:
            actor = await self.uow.users.get_by_id(actor_id)
            if actor is None or actor.is_deleted:
                raise AuthenticationError("Actor user not found or deleted")

            self._ensure_actor_access(actor, target_user_id, "users:write")

            target_user = await self.uow.users.get_by_id(target_user_id)
            if target_user is None or target_user.is_deleted:
                raise EntityNotFoundError("User not found")

            existing_addresses = await self.uow.addresses.list_by_user_id(
                target_user_id, limit=self.MAX_USER_ADDRESSES + 1
            )
            if len(existing_addresses) >= self.MAX_USER_ADDRESSES:
                raise DomainValidationError(
                    f"User cannot have more than {self.MAX_USER_ADDRESSES} addresses"
                )

            if not existing_addresses:
                is_default = True

            if is_default:
                await self.uow.addresses.unset_default_for_user(target_user_id)

            address = UserAddressDomain(
                user_id=target_user_id,
                country=country,
                region=region,
                city=city,
                house=house or street or "",
                apartment=apartment,
                postal_code=postal_code,
                street=street,
                is_default=is_default,
                created_by=actor_id,
            )
            await self.uow.addresses.add(address)
            await self.uow.commit()
            return address

    async def set_default_address(
        self,
        *,
        actor_id: UUID,
        target_user_id: UUID,
        address_id: UUID,
    ) -> UserAddressDomain:
        async with self.uow:
            actor = await self.uow.users.get_by_id(actor_id)
            if actor is None or actor.is_deleted:
                raise AuthenticationError("Actor user not found or deleted")

            self._ensure_actor_access(actor, target_user_id, "users:write")

            address = await self.uow.addresses.get_by_id(address_id)
            if address is None or address.user_id != target_user_id:
                raise EntityNotFoundError("Address not found")

            await self.uow.addresses.unset_default_for_user(target_user_id)
            address.is_default = True
            await self.uow.addresses.update(address)
            await self.uow.commit()
            return address

    async def delete_address(
        self,
        *,
        actor_id: UUID,
        target_user_id: UUID,
        address_id: UUID,
    ) -> None:
        async with self.uow:
            actor = await self.uow.users.get_by_id(actor_id)
            if actor is None or actor.is_deleted:
                raise AuthenticationError("Actor user not found or deleted")

            self._ensure_actor_access(actor, target_user_id, "users:write")

            address = await self.uow.addresses.get_by_id(address_id)
            if address is None or address.user_id != target_user_id:
                raise EntityNotFoundError("Address not found")

            await self.uow.addresses.delete(address_id)
            await self.uow.commit()

    async def soft_delete_user(
        self,
        *,
        actor_id: UUID,
        target_user_id: UUID,
    ) -> None:
        async with self.uow:
            actor = await self.uow.users.get_by_id(actor_id)
            if actor is None or actor.is_deleted:
                raise AuthenticationError("Actor user not found or deleted")

            self._ensure_actor_access(actor, target_user_id, "users:delete")

            target_user = await self.uow.users.get_by_id(target_user_id)
            if target_user is None or target_user.is_deleted:
                raise EntityNotFoundError("User not found")

            now = factory_now()
            target_user.deleted_at = now
            target_user.updated_at = now
            await self.uow.users.update(target_user)
            await self.uow.commit()
