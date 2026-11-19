from uuid import UUID

from src.domain.exceptions import EntityNotFoundError, PermissionDeniedError
from src.domain.interfaces.post_office import PostOfficeUnitOfWorkProtocol
from src.domain.models import PostOfficeDomain, UserDomain


class PostOfficeService:
    def __init__(self, uow: PostOfficeUnitOfWorkProtocol) -> None:
        self.uow = uow

    def _check_admin_permissions(self, actor: UserDomain) -> None:
        allowed = {"mod:mail-manager", "admin:access", "*"}
        if not any(perm in allowed for perm in actor.global_permissions):
            raise PermissionDeniedError(
                "Access denied: required 'mod:mail-manager' or 'admin:access'"
            )

    async def list_active(
        self, search: str | None = None, city: str | None = None
    ) -> list[PostOfficeDomain]:
        async with self.uow:
            return await self.uow.post_offices.list_all(
                search=search, city=city, is_active=True
            )

    async def list_all(
        self,
        actor: UserDomain,
        search: str | None = None,
        city: str | None = None,
    ) -> list[PostOfficeDomain]:
        self._check_admin_permissions(actor)
        async with self.uow:
            return await self.uow.post_offices.list_all(
                search=search, city=city, is_active=None
            )

    async def create(
        self,
        actor: UserDomain,
        *,
        name: str,
        country: str = "Россия",
        region: str | None = None,
        city: str,
        house: str,
        postal_code: str,
        note: str | None = None,
        is_active: bool = True,
    ) -> PostOfficeDomain:
        self._check_admin_permissions(actor)
        office = PostOfficeDomain(
            name=name,
            country=country,
            region=region,
            city=city,
            house=house,
            postal_code=postal_code,
            note=note,
            is_active=is_active,
            created_by=actor.id,
        )
        async with self.uow:
            await self.uow.post_offices.add(office)
            await self.uow.commit()
        return office

    async def update(
        self,
        actor: UserDomain,
        office_id: UUID,
        *,
        name: str | None = None,
        country: str | None = None,
        region: str | None = None,
        city: str | None = None,
        house: str | None = None,
        postal_code: str | None = None,
        note: str | None = None,
        is_active: bool | None = None,
    ) -> PostOfficeDomain:
        self._check_admin_permissions(actor)
        async with self.uow:
            office = await self.uow.post_offices.get_by_id(office_id)
            if office is None:
                raise EntityNotFoundError("Post office not found")

            if name is not None:
                office.name = name
            if country is not None:
                office.country = country
            if region is not None:
                office.region = region
            if city is not None:
                office.city = city
            if house is not None:
                office.house = house
            if postal_code is not None:
                office.postal_code = postal_code
            if note is not None:
                office.note = note
            if is_active is not None:
                office.is_active = is_active

            await self.uow.post_offices.update(office)
            await self.uow.commit()
            return office

    async def delete(self, actor: UserDomain, office_id: UUID) -> None:
        self._check_admin_permissions(actor)
        async with self.uow:
            await self.uow.post_offices.delete(office_id)
            await self.uow.commit()
