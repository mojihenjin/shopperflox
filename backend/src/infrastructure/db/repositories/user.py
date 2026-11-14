from datetime import datetime
from uuid import UUID

from sqlalchemy import delete, func, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.exceptions import EntityAlreadyExistsError, EntityNotFoundError
from src.domain.models import (
    UserAddressDomain,
    UserBanDomain,
    UserDomain,
    UserPersonalDomain,
)
from src.infrastructure.db.models import (
    UserAddressModel,
    UserBanModel,
    UserModel,
    UserPersonalModel,
)
from src.utils import factory_now


class SqlAlchemyUserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def _to_domain(self, model: UserModel) -> UserDomain:
        return UserDomain(
            id=model.id,
            login=model.login,
            email=model.email,
            password_hash=model.password_hash,
            verified_profile=model.verified_profile,
            verified_email=model.verified_email,
            global_permissions=list(model.global_permissions),
            created_by=model.created_by,
            created_at=model.created_at,
            updated_at=model.updated_at,
            deleted_at=model.deleted_at,
        )

    async def get_by_id(
        self, user_id: UUID, *, include_deleted: bool = False
    ) -> UserDomain | None:
        stmt = select(UserModel).where(UserModel.id == user_id)
        if not include_deleted:
            stmt = stmt.where(UserModel.deleted_at.is_(None))
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_domain(model) if model else None

    async def get_by_login(self, login: str) -> UserDomain | None:
        stmt = select(UserModel).where(
            UserModel.login == login, UserModel.deleted_at.is_(None)
        )
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_domain(model) if model else None

    async def get_by_email(self, email: str) -> UserDomain | None:
        stmt = select(UserModel).where(
            UserModel.email == email, UserModel.deleted_at.is_(None)
        )
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_domain(model) if model else None

    async def exists_active(self, login: str, email: str | None = None) -> bool:
        cond = UserModel.login == login
        if email:
            cond = or_(cond, UserModel.email == email)
        stmt = select(func.count()).where(cond, UserModel.deleted_at.is_(None))
        count = await self.session.scalar(stmt)
        return bool(count and count > 0)

    async def add(self, user: UserDomain) -> None:
        model = UserModel(
            id=user.id,
            login=user.login,
            email=user.email,
            password_hash=user.password_hash,
            verified_profile=user.verified_profile,
            verified_email=user.verified_email,
            global_permissions=user.global_permissions,
            created_by=user.created_by,
            created_at=user.created_at,
            updated_at=user.updated_at,
            deleted_at=user.deleted_at,
        )
        self.session.add(model)
        try:
            await self.session.flush()
        except IntegrityError as exc:
            raise EntityAlreadyExistsError(
                f"User with login '{user.login}' or email '{user.email}' already exists"
            ) from exc

    async def update(self, user: UserDomain) -> None:
        model = await self.session.get(UserModel, user.id)
        if model is None:
            raise EntityNotFoundError("User not found")
        model.login = user.login
        model.email = user.email
        model.password_hash = user.password_hash
        model.verified_profile = user.verified_profile
        model.verified_email = user.verified_email
        model.global_permissions = user.global_permissions
        model.updated_at = user.updated_at
        model.deleted_at = user.deleted_at
        try:
            await self.session.flush()
        except IntegrityError as exc:
            raise EntityAlreadyExistsError(
                f"User with login '{user.login}' or email '{user.email}' already exists"
            ) from exc


class SqlAlchemyUserPersonalRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def _to_domain(self, model: UserPersonalModel) -> UserPersonalDomain:
        return UserPersonalDomain(
            id=model.id,
            firstname=model.firstname,
            lastname=model.lastname,
            phone_number=model.phone_number,
            created_by=model.created_by,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    async def get_by_user_id(self, user_id: UUID) -> UserPersonalDomain | None:
        model = await self.session.get(UserPersonalModel, user_id)
        return self._to_domain(model) if model else None

    async def get_by_phone(self, phone_number: str) -> UserPersonalDomain | None:
        stmt = select(UserPersonalModel).where(
            UserPersonalModel.phone_number == phone_number
        )
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_domain(model) if model else None

    async def add(self, personal: UserPersonalDomain) -> None:
        model = UserPersonalModel(
            id=personal.id,
            firstname=personal.firstname,
            lastname=personal.lastname,
            phone_number=personal.phone_number,
            created_by=personal.created_by,
            created_at=personal.created_at,
            updated_at=personal.updated_at,
        )
        self.session.add(model)
        try:
            await self.session.flush()
        except IntegrityError as exc:
            raise EntityAlreadyExistsError(
                f"Personal profile for user {personal.id} or phone '{personal.phone_number}' already exists"
            ) from exc

    async def update(self, personal: UserPersonalDomain) -> None:
        model = await self.session.get(UserPersonalModel, personal.id)
        if model is None:
            raise EntityNotFoundError("Personal profile not found")
        model.firstname = personal.firstname
        model.lastname = personal.lastname
        model.phone_number = personal.phone_number
        model.updated_at = personal.updated_at
        try:
            await self.session.flush()
        except IntegrityError as exc:
            raise EntityAlreadyExistsError(
                f"Phone '{personal.phone_number}' already in use"
            ) from exc


class SqlAlchemyUserAddressRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def _to_domain(self, model: UserAddressModel) -> UserAddressDomain:
        return UserAddressDomain(
            id=model.id,
            user_id=model.user_id,
            city=model.city,
            street=model.street,
            postal_code=model.postal_code,
            is_default=model.is_default,
            created_by=model.created_by,
            created_at=model.created_at,
        )

    async def get_by_id(self, address_id: UUID) -> UserAddressDomain | None:
        model = await self.session.get(UserAddressModel, address_id)
        return self._to_domain(model) if model else None

    async def list_by_user_id(self, user_id: UUID) -> list[UserAddressDomain]:
        stmt = (
            select(UserAddressModel)
            .where(UserAddressModel.user_id == user_id)
            .order_by(UserAddressModel.created_at.desc())
        )
        result = await self.session.scalars(stmt)
        return [self._to_domain(m) for m in result]

    async def get_default_by_user_id(self, user_id: UUID) -> UserAddressDomain | None:
        stmt = select(UserAddressModel).where(
            UserAddressModel.user_id == user_id,
            UserAddressModel.is_default.is_(True),
        )
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_domain(model) if model else None

    async def unset_default_for_user(self, user_id: UUID) -> None:
        stmt = (
            update(UserAddressModel)
            .where(
                UserAddressModel.user_id == user_id,
                UserAddressModel.is_default.is_(True),
            )
            .values(is_default=False)
        )
        await self.session.execute(stmt)
        await self.session.flush()

    async def add(self, address: UserAddressDomain) -> None:
        model = UserAddressModel(
            id=address.id,
            user_id=address.user_id,
            city=address.city,
            street=address.street,
            postal_code=address.postal_code,
            is_default=address.is_default,
            created_by=address.created_by,
            created_at=address.created_at,
        )
        self.session.add(model)
        try:
            await self.session.flush()
        except IntegrityError as exc:
            raise EntityAlreadyExistsError(
                f"Default address conflict for user {address.user_id}"
            ) from exc

    async def update(self, address: UserAddressDomain) -> None:
        model = await self.session.get(UserAddressModel, address.id)
        if model is None:
            raise EntityNotFoundError("Address not found")
        model.city = address.city
        model.street = address.street
        model.postal_code = address.postal_code
        model.is_default = address.is_default
        try:
            await self.session.flush()
        except IntegrityError as exc:
            raise EntityAlreadyExistsError(
                f"Default address conflict for user {address.user_id}"
            ) from exc

    async def delete(self, address_id: UUID) -> None:
        stmt = delete(UserAddressModel).where(UserAddressModel.id == address_id)
        await self.session.execute(stmt)
        await self.session.flush()


class SqlAlchemyUserBanRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def _to_domain(self, model: UserBanModel) -> UserBanDomain:
        return UserBanDomain(
            id=model.id,
            user_id=model.user_id,
            reason=model.reason,
            created_by=model.created_by,
            created_at=model.created_at,
            ended_at=model.ended_at,
        )

    async def get_active_by_user_id(
        self, user_id: UUID, at: datetime | None = None
    ) -> UserBanDomain | None:
        check_time = at or factory_now()
        stmt = (
            select(UserBanModel)
            .where(
                UserBanModel.user_id == user_id,
                or_(
                    UserBanModel.ended_at.is_(None),
                    UserBanModel.ended_at > check_time,
                ),
            )
            .order_by(UserBanModel.created_at.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_domain(model) if model else None

    async def list_by_user_id(self, user_id: UUID) -> list[UserBanDomain]:
        stmt = (
            select(UserBanModel)
            .where(UserBanModel.user_id == user_id)
            .order_by(UserBanModel.created_at.desc())
        )
        result = await self.session.scalars(stmt)
        return [self._to_domain(m) for m in result]

    async def add(self, ban: UserBanDomain) -> None:
        model = UserBanModel(
            id=ban.id,
            user_id=ban.user_id,
            reason=ban.reason,
            created_by=ban.created_by,
            created_at=ban.created_at,
            ended_at=ban.ended_at,
        )
        self.session.add(model)
        try:
            await self.session.flush()
        except IntegrityError as exc:
            raise EntityAlreadyExistsError(
                f"Failed to create ban for user {ban.user_id}"
            ) from exc

    async def update(self, ban: UserBanDomain) -> None:
        model = await self.session.get(UserBanModel, ban.id)
        if model is None:
            raise EntityNotFoundError("Ban not found")
        model.reason = ban.reason
        model.ended_at = ban.ended_at
        try:
            await self.session.flush()
        except IntegrityError as exc:
            raise EntityAlreadyExistsError(
                f"Failed to update ban for user {ban.user_id}"
            ) from exc
