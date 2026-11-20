from uuid import UUID

from sqlalchemy import delete, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.exceptions import EntityNotFoundError
from src.domain.models import PostOfficeDomain
from src.infrastructure.db.models import PostOfficeModel


class SqlAlchemyPostOfficeRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def _to_domain(self, model: PostOfficeModel) -> PostOfficeDomain:
        return PostOfficeDomain(
            id=model.id,
            name=model.name,
            country=model.country,
            region=model.region,
            city=model.city,
            house=model.house,
            postal_code=model.postal_code,
            note=model.note,
            is_active=model.is_active,
            created_by=model.created_by,
            created_at=model.created_at,
        )

    async def get_by_id(self, office_id: UUID) -> PostOfficeDomain | None:
        model = await self.session.get(PostOfficeModel, office_id)
        return self._to_domain(model) if model else None

    async def list_all(
        self,
        *,
        search: str | None = None,
        city: str | None = None,
        is_active: bool | None = None,
    ) -> list[PostOfficeDomain]:
        stmt = select(PostOfficeModel)
        if is_active is not None:
            stmt = stmt.where(PostOfficeModel.is_active == is_active)
        if city is not None and city.strip():
            stmt = stmt.where(PostOfficeModel.city.ilike(f"%{city.strip()}%"))
        if search is not None and search.strip():
            term = f"%{search.strip()}%"
            stmt = stmt.where(
                or_(
                    PostOfficeModel.name.ilike(term),
                    PostOfficeModel.postal_code.ilike(term),
                    PostOfficeModel.city.ilike(term),
                    PostOfficeModel.house.ilike(term),
                )
            )
        stmt = stmt.order_by(PostOfficeModel.created_at.desc())
        res = await self.session.scalars(stmt)
        return [self._to_domain(m) for m in res]

    async def add(self, office: PostOfficeDomain) -> None:
        model = PostOfficeModel(
            id=office.id,
            name=office.name,
            country=office.country,
            region=office.region,
            city=office.city,
            house=office.house,
            postal_code=office.postal_code,
            note=office.note,
            is_active=office.is_active,
            created_by=office.created_by,
            created_at=office.created_at,
        )
        self.session.add(model)
        await self.session.flush()

    async def update(self, office: PostOfficeDomain) -> None:
        model = await self.session.get(PostOfficeModel, office.id)
        if model is None:
            raise EntityNotFoundError("Post office not found")
        model.name = office.name
        model.country = office.country
        model.region = office.region
        model.city = office.city
        model.house = office.house
        model.postal_code = office.postal_code
        model.note = office.note
        model.is_active = office.is_active
        await self.session.flush()

    async def delete(self, office_id: UUID) -> None:
        stmt = delete(PostOfficeModel).where(PostOfficeModel.id == office_id)
        res = await self.session.execute(stmt)
        if res.rowcount == 0:
            raise EntityNotFoundError("Post office not found")
        await self.session.flush()
