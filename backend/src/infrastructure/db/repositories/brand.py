from uuid import UUID

from sqlalchemy import delete, func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.exceptions import EntityAlreadyExistsError
from src.domain.models import BrandDomain, BrandMemberDomain, BrandMemberRole
from src.infrastructure.db.models import BrandMemberModel, BrandModel, UserModel


class SqlAlchemyBrandRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def _to_domain(self, model: BrandModel) -> BrandDomain:
        return BrandDomain(
            id=model.id,
            name=model.name,
            slug=model.slug,
            his_url=model.his_url,
            logo_url=model.logo_url,
            is_deleted=model.is_deleted,
            created_at=model.created_at,
        )

    async def get_by_id(self, brand_id: UUID) -> BrandDomain | None:
        model = await self.session.get(BrandModel, brand_id)
        return self._to_domain(model) if model else None

    async def get_by_slug(self, slug: str) -> BrandDomain | None:
        stmt = select(BrandModel).where(BrandModel.slug == slug)
        res = await self.session.execute(stmt)
        model = res.scalar_one_or_none()
        return self._to_domain(model) if model else None

    async def get_by_name(self, name: str) -> BrandDomain | None:
        stmt = select(BrandModel).where(
            func.lower(BrandModel.name) == func.lower(name.strip())
        )
        res = await self.session.execute(stmt)
        model = res.scalar_one_or_none()
        return self._to_domain(model) if model else None

    async def list_active(self, limit: int = 100, offset: int = 0) -> list[BrandDomain]:
        stmt = (
            select(BrandModel)
            .where(BrandModel.is_deleted.is_(False))
            .order_by(BrandModel.name.asc())
            .limit(limit)
            .offset(offset)
        )
        res = await self.session.execute(stmt)
        return [self._to_domain(m) for m in res.scalars().all()]

    async def list_by_user_id(
        self, user_id: UUID
    ) -> list[tuple[BrandDomain, BrandMemberRole]]:
        stmt = (
            select(BrandModel, BrandMemberModel.role)
            .join(BrandMemberModel, BrandModel.id == BrandMemberModel.brand_id)
            .where(BrandMemberModel.user_id == user_id)
            .order_by(BrandModel.name.asc())
        )
        res = await self.session.execute(stmt)
        rows = res.all()
        return [
            (self._to_domain(brand_model), BrandMemberRole(role_str))
            for brand_model, role_str in rows
        ]

    async def add(self, brand: BrandDomain) -> None:
        model = BrandModel(
            id=brand.id,
            name=brand.name,
            slug=brand.slug,
            his_url=brand.his_url,
            logo_url=brand.logo_url,
            is_deleted=brand.is_deleted,
            created_at=brand.created_at,
        )
        self.session.add(model)
        try:
            await self.session.flush()
        except IntegrityError as exc:
            raise EntityAlreadyExistsError(
                f"Brand with name '{brand.name}' or slug '{brand.slug}' already exists"
            ) from exc

    async def update(self, brand: BrandDomain) -> None:
        stmt = (
            update(BrandModel)
            .where(BrandModel.id == brand.id)
            .values(
                name=brand.name,
                slug=brand.slug,
                his_url=brand.his_url,
                logo_url=brand.logo_url,
                is_deleted=brand.is_deleted,
            )
        )
        try:
            await self.session.execute(stmt)
            await self.session.flush()
        except IntegrityError as exc:
            raise EntityAlreadyExistsError(
                f"Brand with name '{brand.name}' or slug '{brand.slug}' already exists"
            ) from exc

    async def add_member(self, member: BrandMemberDomain) -> None:
        model = BrandMemberModel(
            brand_id=member.brand_id,
            user_id=member.user_id,
            role=member.role.value,
            created_at=member.created_at,
        )
        self.session.add(model)
        try:
            await self.session.flush()
        except IntegrityError as exc:
            raise EntityAlreadyExistsError(
                "User is already a member of this brand"
            ) from exc

    async def update_member(self, member: BrandMemberDomain) -> None:
        stmt = (
            update(BrandMemberModel)
            .where(
                BrandMemberModel.brand_id == member.brand_id,
                BrandMemberModel.user_id == member.user_id,
            )
            .values(role=member.role.value)
        )
        await self.session.execute(stmt)
        await self.session.flush()

    async def remove_member(self, brand_id: UUID, user_id: UUID) -> None:
        stmt = delete(BrandMemberModel).where(
            BrandMemberModel.brand_id == brand_id,
            BrandMemberModel.user_id == user_id,
        )
        await self.session.execute(stmt)
        await self.session.flush()

    async def get_member(
        self, brand_id: UUID, user_id: UUID
    ) -> BrandMemberDomain | None:
        stmt = (
            select(BrandMemberModel, UserModel.login)
            .outerjoin(UserModel, BrandMemberModel.user_id == UserModel.id)
            .where(
                BrandMemberModel.brand_id == brand_id,
                BrandMemberModel.user_id == user_id,
            )
        )
        res = await self.session.execute(stmt)
        row = res.first()
        if not row:
            return None
        model, login = row
        return BrandMemberDomain(
            brand_id=model.brand_id,
            user_id=model.user_id,
            role=BrandMemberRole(model.role),
            user_login=login,
            created_at=model.created_at,
        )

    async def list_members(self, brand_id: UUID) -> list[BrandMemberDomain]:
        stmt = (
            select(BrandMemberModel, UserModel.login)
            .outerjoin(UserModel, BrandMemberModel.user_id == UserModel.id)
            .where(BrandMemberModel.brand_id == brand_id)
            .order_by(BrandMemberModel.created_at.asc())
        )
        res = await self.session.execute(stmt)
        rows = res.all()
        return [
            BrandMemberDomain(
                brand_id=m.brand_id,
                user_id=m.user_id,
                role=BrandMemberRole(m.role),
                user_login=login,
                created_at=m.created_at,
            )
            for m, login in rows
        ]

    async def count_representatives(self, brand_id: UUID) -> int:
        stmt = (
            select(func.count())
            .select_from(BrandMemberModel)
            .where(
                BrandMemberModel.brand_id == brand_id,
                BrandMemberModel.role == BrandMemberRole.REPRESENTATIVE.value,
            )
        )
        res = await self.session.execute(stmt)
        return res.scalar_one() or 0
