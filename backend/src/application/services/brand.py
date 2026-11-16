import re
from uuid import UUID

from uuid6 import uuid7

from src.domain.exceptions import (
    DomainValidationError,
    EntityNotFoundError,
    PermissionDeniedError,
)
from src.domain.interfaces import BrandUnitOfWorkProtocol, FileStorageProtocol
from src.domain.models import (
    BrandDomain,
    BrandMemberDomain,
    BrandMemberRole,
    ModerationStatus,
    UserDomain,
)

from .notification import NotificationService


class BrandService:
    def __init__(
        self,
        uow: BrandUnitOfWorkProtocol,
        storage: FileStorageProtocol | None = None,
        notification_service: NotificationService | None = None,
    ) -> None:
        self.uow = uow
        self.storage = storage
        self.notification_service = notification_service

    @staticmethod
    def _slugify(text: str) -> str:
        s = re.sub(r"[^\w\s-]", "", text.strip().lower())
        s = re.sub(r"[-\s]+", "-", s).strip("-")
        return s or "brand"

    def _check_creator_brand_permission(self, actor: UserDomain) -> None:
        if not actor or not (
            "*" in actor.global_permissions
            or "creator:brand" in actor.global_permissions
            or any(
                p.startswith("creator:") or p == "creator"
                for p in actor.global_permissions
            )
        ):
            raise PermissionDeniedError("Permission 'creator:brand' required")

    def _check_moderator_permission(self, actor: UserDomain) -> None:
        if not actor or not (
            "*" in actor.global_permissions
            or "mod:approve_manager" in actor.global_permissions
        ):
            raise PermissionDeniedError("Permission 'mod:approve_manager' required")

    async def _require_representative(
        self, actor: UserDomain, brand_id: UUID
    ) -> BrandMemberDomain | None:
        if not actor:
            raise PermissionDeniedError("Authentication required")
        if "*" in actor.global_permissions:
            return None
        member = await self.uow.brands.get_member(brand_id, actor.id)
        if not member or member.role != BrandMemberRole.REPRESENTATIVE:
            raise PermissionDeniedError("Representative role required for this brand")
        return member

    async def _require_member(
        self, actor: UserDomain, brand_id: UUID
    ) -> BrandMemberDomain | None:
        if not actor:
            raise PermissionDeniedError("Authentication required")
        if (
            "*" in actor.global_permissions
            or "mod:approve_manager" in actor.global_permissions
            or "catalog:manage" in actor.global_permissions
        ):
            return None
        member = await self.uow.brands.get_member(brand_id, actor.id)
        if not member:
            raise PermissionDeniedError("Membership required for this brand")
        return member

    @staticmethod
    def _detect_image_format(data: bytes) -> tuple[str, str]:
        if len(data) < 12:
            raise DomainValidationError("Invalid or corrupted image file")

        # JPEG: \xff\xd8\xff
        if data.startswith(b"\xff\xd8\xff"):
            return "jpg", "image/jpeg"

        # PNG: \x89PNG\r\n\x1a\n
        if data.startswith(b"\x89PNG\r\n\x1a\n"):
            return "png", "image/png"

        # WebP: RIFF....WEBP
        if data.startswith(b"RIFF") and data[8:12] == b"WEBP":
            return "webp", "image/webp"

        raise DomainValidationError(
            "Unsupported image format. Allowed formats: JPEG, PNG, WebP"
        )

    async def create_brand(
        self,
        *,
        actor: UserDomain,
        name: str,
        his_url: str | None = None,
    ) -> BrandDomain:
        self._check_creator_brand_permission(actor)
        name_clean = name.strip()
        if not name_clean:
            raise DomainValidationError("Brand name cannot be empty")

        clean_his_url = his_url.strip() if his_url and his_url.strip() else None

        base_slug = self._slugify(name_clean)

        async with self.uow:
            slug = base_slug
            counter = 2
            while await self.uow.brands.get_by_slug(slug):
                slug = f"{base_slug}-{counter}"
                counter += 1

            brand = BrandDomain(
                id=uuid7(),
                name=name_clean,
                slug=slug,
                his_url=clean_his_url,
                is_deleted=False,
                moderation_status=ModerationStatus.PENDING,
                is_verified=False,
                views_count=0,
                orders_count=0,
            )
            await self.uow.brands.add(brand)

            # Automatically add creator as representative
            creator_member = BrandMemberDomain(
                brand_id=brand.id,
                user_id=actor.id,
                user_login=actor.login,
                role=BrandMemberRole.REPRESENTATIVE,
            )
            await self.uow.brands.add_member(creator_member)
            await self.uow.commit()

        return brand

    async def get_brand(
        self, slug: str, *, actor: UserDomain | None = None
    ) -> BrandDomain:
        clean_slug = slug.strip()
        async with self.uow:
            brand = await self.uow.brands.get_by_slug(clean_slug)
            if brand is None or brand.is_deleted:
                raise EntityNotFoundError("Brand not found")

            if brand.moderation_status != ModerationStatus.APPROVED:
                has_access = False
                if actor is not None:
                    if (
                        "*" in actor.global_permissions
                        or "mod:approve_manager" in actor.global_permissions
                    ):
                        has_access = True
                    else:
                        member = await self.uow.brands.get_member(brand.id, actor.id)
                        if member is not None:
                            has_access = True
                if not has_access:
                    raise EntityNotFoundError("Brand not found")

            await self.uow.brands.increment_views(brand.id)
            brand.views_count += 1
            await self.uow.commit()
            return brand

    async def list_pending_brands(
        self,
        *,
        actor: UserDomain,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[BrandDomain], int]:
        self._check_moderator_permission(actor)
        async with self.uow:
            brands = await self.uow.brands.list_pending(limit=limit, offset=offset)
            total = await self.uow.brands.count_pending()
            return brands, total

    async def count_pending_brands(self, *, actor: UserDomain) -> int:
        self._check_moderator_permission(actor)
        async with self.uow:
            return await self.uow.brands.count_pending()

    async def approve_brand(self, *, actor: UserDomain, brand_id: UUID) -> BrandDomain:
        self._check_moderator_permission(actor)
        async with self.uow:
            brand = await self.uow.brands.get_by_id(brand_id)
            if brand is None or brand.is_deleted:
                raise EntityNotFoundError("Brand not found")

            brand.moderation_status = ModerationStatus.APPROVED
            brand.rejection_reason = None
            await self.uow.brands.update(brand)
            members = await self.uow.brands.list_members(brand.id)
            await self.uow.commit()

        reps = [
            m for m in members if m.role == BrandMemberRole.REPRESENTATIVE
        ] or members
        if self.notification_service is not None:
            for rep in reps:
                await self.notification_service.notify_user(
                    user_id=rep.user_id,
                    title="Заявка одобрена",
                    body=f"Бренд «{brand.name}» прошёл проверку и опубликован.",
                    link=f"/brands/{brand.slug}",
                    send_email=False,
                )

        return brand

    async def reject_brand(
        self, *, actor: UserDomain, brand_id: UUID, reason: str | None = None
    ) -> BrandDomain:
        self._check_moderator_permission(actor)
        clean_reason = reason.strip() if reason and reason.strip() else None
        async with self.uow:
            brand = await self.uow.brands.get_by_id(brand_id)
            if brand is None or brand.is_deleted:
                raise EntityNotFoundError("Brand not found")

            brand.moderation_status = ModerationStatus.REJECTED
            brand.rejection_reason = clean_reason
            await self.uow.brands.update(brand)
            members = await self.uow.brands.list_members(brand.id)
            await self.uow.commit()

        reps = [
            m for m in members if m.role == BrandMemberRole.REPRESENTATIVE
        ] or members
        body_text = (
            f"Отклонено: {clean_reason}"
            if clean_reason
            else "Отклонено: Причина не указана"
        )
        if self.notification_service is not None:
            for rep in reps:
                await self.notification_service.notify_user(
                    user_id=rep.user_id,
                    title="Заявка отклонена",
                    body=body_text,
                    link=f"/brands/{brand.slug}",
                    send_email=True,
                )

        return brand

    async def verify_brand(
        self, *, actor: UserDomain, brand_id: UUID, is_verified: bool
    ) -> BrandDomain:
        self._check_moderator_permission(actor)
        async with self.uow:
            brand = await self.uow.brands.get_by_id(brand_id)
            if brand is None or brand.is_deleted:
                raise EntityNotFoundError("Brand not found")

            brand.is_verified = is_verified
            await self.uow.brands.update(brand)
            await self.uow.commit()
            return brand

    async def list_active_brands(
        self, limit: int = 100, offset: int = 0
    ) -> list[BrandDomain]:
        async with self.uow:
            return await self.uow.brands.list_active(limit=limit, offset=offset)

    async def list_my_brands(
        self, actor: UserDomain
    ) -> list[tuple[BrandDomain, BrandMemberRole]]:
        if not actor:
            raise PermissionDeniedError("Authentication required")
        async with self.uow:
            return await self.uow.brands.list_by_user_id(actor.id)

    async def update_brand(
        self,
        *,
        actor: UserDomain,
        brand_id: UUID,
        name: str | None = None,
        his_url: str | None = ...,
    ) -> BrandDomain:
        async with self.uow:
            brand = await self.uow.brands.get_by_id(brand_id)
            if brand is None:
                raise EntityNotFoundError("Brand not found")

            await self._require_representative(actor, brand_id)

            if name is not None:
                name_clean = name.strip()
                if not name_clean:
                    raise DomainValidationError("Brand name cannot be empty")
                if name_clean != brand.name:
                    brand.name = name_clean
                    base_slug = self._slugify(name_clean)
                    slug = base_slug
                    counter = 2
                    existing = await self.uow.brands.get_by_slug(slug)
                    while existing and existing.id != brand.id:
                        slug = f"{base_slug}-{counter}"
                        counter += 1
                        existing = await self.uow.brands.get_by_slug(slug)
                    brand.slug = slug

                    await self.uow.products.update_brand_name_for_products(
                        brand_id, name_clean
                    )

            if his_url is not ...:
                brand.his_url = his_url.strip() if his_url and his_url.strip() else None

            await self.uow.brands.update(brand)
            await self.uow.commit()
            return brand

    async def upload_brand_logo(
        self,
        *,
        actor: UserDomain,
        brand_id: UUID,
        file_data: bytes,
    ) -> BrandDomain:
        if len(file_data) > 5 * 1024 * 1024:
            raise DomainValidationError("File size exceeds 5 MB limit")

        ext, content_type = self._detect_image_format(file_data)

        if not self.storage:
            raise DomainValidationError("File storage is not configured")

        async with self.uow:
            brand = await self.uow.brands.get_by_id(brand_id)
            if brand is None:
                raise EntityNotFoundError("Brand not found")

            await self._require_representative(actor, brand_id)

            key = f"brands/{brand_id}/logo_{uuid7().hex[:8]}.{ext}"
            public_url = await self.storage.upload_file(
                key=key,
                data=file_data,
                content_type=content_type,
            )
            brand.logo_url = public_url
            await self.uow.brands.update(brand)
            await self.uow.commit()
            return brand

    async def delete_brand(
        self,
        *,
        actor: UserDomain,
        brand_id: UUID,
    ) -> BrandDomain:
        async with self.uow:
            brand = await self.uow.brands.get_by_id(brand_id)
            if brand is None:
                raise EntityNotFoundError("Brand not found")

            await self._require_representative(actor, brand_id)

            brand.is_deleted = True
            await self.uow.brands.update(brand)
            await self.uow.commit()
            return brand

    async def list_members(
        self,
        *,
        actor: UserDomain,
        brand_id: UUID,
    ) -> list[BrandMemberDomain]:
        async with self.uow:
            brand = await self.uow.brands.get_by_id(brand_id)
            if brand is None:
                raise EntityNotFoundError("Brand not found")

            await self._require_member(actor, brand_id)
            return await self.uow.brands.list_members(brand_id)

    async def add_or_update_member(
        self,
        *,
        actor: UserDomain,
        brand_id: UUID,
        login: str,
        role: BrandMemberRole,
    ) -> BrandMemberDomain:
        async with self.uow:
            brand = await self.uow.brands.get_by_id(brand_id)
            if brand is None:
                raise EntityNotFoundError("Brand not found")

            await self._require_representative(actor, brand_id)

            clean_login = login.strip().lower()
            target_user = await self.uow.users.get_by_login(clean_login)
            if target_user is None:
                raise EntityNotFoundError("User not found")

            existing_member = await self.uow.brands.get_member(brand_id, target_user.id)
            if existing_member is not None:
                existing_member.role = role
                await self.uow.brands.update_member(existing_member)
                member = existing_member
            else:
                member = BrandMemberDomain(
                    brand_id=brand_id,
                    user_id=target_user.id,
                    user_login=target_user.login,
                    role=role,
                )
                await self.uow.brands.add_member(member)

            await self.uow.commit()
            return member

    async def remove_member(
        self,
        *,
        actor: UserDomain,
        brand_id: UUID,
        target_user_id: UUID,
    ) -> tuple[bool, bool]:
        async with self.uow:
            brand = await self.uow.brands.get_by_id(brand_id)
            if brand is None:
                raise EntityNotFoundError("Brand not found")

            target_member = await self.uow.brands.get_member(brand_id, target_user_id)
            if target_member is None:
                raise EntityNotFoundError("Member not found in this brand")

            is_self = actor.id == target_user_id
            if not is_self and "*" not in actor.global_permissions:
                actor_member = await self.uow.brands.get_member(brand_id, actor.id)
                if (
                    not actor_member
                    or actor_member.role != BrandMemberRole.REPRESENTATIVE
                ):
                    raise PermissionDeniedError(
                        "Only representatives can remove other members"
                    )

            await self.uow.brands.remove_member(brand_id, target_user_id)

            rep_count = await self.uow.brands.count_representatives(brand_id)
            brand_deleted = False
            if rep_count == 0:
                brand.is_deleted = True
                await self.uow.brands.update(brand)
                brand_deleted = True

            await self.uow.commit()
            return True, brand_deleted
