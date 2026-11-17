import re
import secrets
import string
from datetime import datetime
from uuid import UUID

from src.domain.exceptions import (
    DomainValidationError,
    EntityAlreadyExistsError,
    EntityNotFoundError,
    InvalidStateTransitionError,
    PermissionDeniedError,
)
from src.domain.interfaces import (
    BrandUnitOfWorkProtocol,
    CatalogUnitOfWorkProtocol,
    PasswordHasherProtocol,
    ReviewUnitOfWorkProtocol,
    TaskQueueProtocol,
    TokenBlacklistProtocol,
    UserUnitOfWorkProtocol,
)
from src.domain.models import (
    AdminReviewItemDomain,
    BrandDomain,
    BrandMemberDomain,
    CategoryDomain,
    ModerationRequestType,
    ModerationStatus,
    ProductDomain,
    UserBanDomain,
    UserDomain,
)
from src.utils import factory_now


class AdminService:
    def __init__(
        self,
        *,
        user_uow: UserUnitOfWorkProtocol,
        catalog_uow: CatalogUnitOfWorkProtocol,
        brand_uow: BrandUnitOfWorkProtocol,
        review_uow: ReviewUnitOfWorkProtocol,
        hasher: PasswordHasherProtocol,
        token_blacklist: TokenBlacklistProtocol | None = None,
        task_queue: TaskQueueProtocol | None = None,
    ) -> None:
        self.user_uow = user_uow
        self.catalog_uow = catalog_uow
        self.brand_uow = brand_uow
        self.review_uow = review_uow
        self.hasher = hasher
        self.token_blacklist = token_blacklist
        self.task_queue = task_queue

    @staticmethod
    def _slugify(text: str) -> str:
        s = re.sub(r"[^\w\s-]", "", text.strip().lower())
        s = re.sub(r"[-\s]+", "-", s).strip("-")
        return s or "category"

    def _check_admin_permission(self, actor: UserDomain) -> None:
        perms = set(actor.global_permissions)
        if "*" not in perms and "admin:access" not in perms:
            raise PermissionDeniedError(
                "Admin permission '*' or 'admin:access' required"
            )

    # ---------------- Users ----------------

    async def list_users(
        self,
        *,
        actor: UserDomain,
        search: str | None = None,
        status: str = "all",
        verified_profile: bool | None = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[tuple[UserDomain, UserBanDomain | None]], int]:
        self._check_admin_permission(actor)
        async with self.user_uow:
            return await self.user_uow.users.list_admin(
                search=search,
                status=status,
                verified_profile=verified_profile,
                sort_by=sort_by,
                sort_order=sort_order,
                limit=limit,
                offset=offset,
            )

    async def update_user(
        self,
        *,
        actor: UserDomain,
        target_user_id: UUID,
        login: str | None = None,
        global_permissions: list[str] | None = None,
        verified_profile: bool | None = None,
    ) -> tuple[UserDomain, UserBanDomain | None]:
        self._check_admin_permission(actor)
        async with self.user_uow:
            target = await self.user_uow.users.get_by_id(
                target_user_id, include_deleted=True
            )
            if target is None:
                raise EntityNotFoundError("User not found")

            if login is not None:
                clean_login = login.strip()
                if not clean_login:
                    raise DomainValidationError("Login cannot be empty")
                if clean_login.lower() != target.login.lower():
                    if await self.user_uow.users.exists_active(login=clean_login):
                        raise EntityAlreadyExistsError(
                            f"User with login '{clean_login}' already exists"
                        )
                    target.login = clean_login

            if global_permissions is not None:
                perms = list(dict.fromkeys(global_permissions))
                if "*" in target.global_permissions and "*" not in perms:
                    superadmins_count = await self.user_uow.users.count_superadmins()
                    if superadmins_count <= 1:
                        raise DomainValidationError(
                            "Cannot remove superadmin permission from the last active superadmin"
                        )
                target.global_permissions = perms

            if verified_profile is not None:
                target.verified_profile = verified_profile

            target.updated_at = factory_now()
            await self.user_uow.users.update(target)
            await self.user_uow.commit()

            active_ban = await self.user_uow.bans.get_active_by_user_id(target_user_id)
            return target, active_ban

    async def ban_user(
        self,
        *,
        actor: UserDomain,
        target_user_id: UUID,
        reason: str,
        ended_at: datetime | None = None,
    ) -> UserBanDomain:
        self._check_admin_permission(actor)
        if actor.id == target_user_id:
            raise DomainValidationError("Cannot ban yourself")

        clean_reason = reason.strip()
        if not clean_reason:
            raise DomainValidationError("Ban reason cannot be empty")

        async with self.user_uow:
            target = await self.user_uow.users.get_by_id(
                target_user_id, include_deleted=True
            )
            if target is None or target.is_deleted:
                raise EntityNotFoundError("User not found")

            active_ban = await self.user_uow.bans.get_active_by_user_id(target_user_id)
            if active_ban and active_ban.is_active():
                raise EntityAlreadyExistsError("User is already actively banned")

            ban = UserBanDomain(
                user_id=target_user_id,
                reason=clean_reason,
                ended_at=ended_at,
                created_by=actor.id,
            )
            await self.user_uow.bans.add(ban)
            await self.user_uow.commit()

        if self.token_blacklist:
            await self.token_blacklist.revoke_user(target_user_id)

        return ban

    async def unban_user(
        self,
        *,
        actor: UserDomain,
        target_user_id: UUID,
    ) -> UserBanDomain:
        self._check_admin_permission(actor)
        async with self.user_uow:
            target = await self.user_uow.users.get_by_id(
                target_user_id, include_deleted=True
            )
            if target is None:
                raise EntityNotFoundError("User not found")

            now = factory_now()
            active_bans = await self.user_uow.bans.list_active_by_user_id(
                target_user_id, at=now
            )
            if not active_bans:
                raise EntityNotFoundError("No active ban found for user")

            for b in active_bans:
                b.ended_at = now
                await self.user_uow.bans.update(b)
            await self.user_uow.commit()

        return active_bans[0]

    async def delete_user(
        self,
        *,
        actor: UserDomain,
        target_user_id: UUID,
    ) -> None:
        self._check_admin_permission(actor)
        if actor.id == target_user_id:
            raise DomainValidationError("Cannot delete yourself")

        async with self.user_uow:
            target = await self.user_uow.users.get_by_id(
                target_user_id, include_deleted=True
            )
            if target is None or target.is_deleted:
                raise EntityNotFoundError("User not found")

            if "*" in target.global_permissions:
                count = await self.user_uow.users.count_superadmins()
                if count <= 1:
                    raise DomainValidationError(
                        "Cannot delete the last active superadmin"
                    )

            target.deleted_at = factory_now()
            target.updated_at = factory_now()
            await self.user_uow.users.update(target)
            await self.user_uow.commit()

        if self.token_blacklist:
            await self.token_blacklist.revoke_user(target_user_id)

    async def reset_password(
        self,
        *,
        actor: UserDomain,
        target_user_id: UUID,
    ) -> None:
        self._check_admin_permission(actor)
        async with self.user_uow:
            target = await self.user_uow.users.get_by_id(
                target_user_id, include_deleted=True
            )
            if target is None or target.is_deleted:
                raise EntityNotFoundError("User not found")

            if not target.email:
                raise DomainValidationError("User does not have an email address")

            alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
            new_password = "".join(secrets.choice(alphabet) for _ in range(14))

            target.password_hash = self.hasher.hash(new_password)
            target.updated_at = factory_now()
            await self.user_uow.users.update(target)
            await self.user_uow.commit()

        if self.token_blacklist:
            await self.token_blacklist.revoke_user(target_user_id)

        if self.task_queue:
            await self.task_queue.enqueue_email(
                to_email=target.email,
                subject="Password Reset - ShopperFlox",
                body_text=(
                    f"Hello {target.login},\n\n"
                    "Your password has been reset by an administrator.\n"
                    f"Your temporary password is: {new_password}\n\n"
                    "Please log in and change your password immediately."
                ),
            )

    # ---------------- Brands ----------------

    async def list_brands(
        self,
        *,
        actor: UserDomain,
        search: str | None = None,
        moderation_status: str | None = None,
        is_verified: bool | None = None,
        include_deleted: bool = True,
        sort_by: str = "created_at",
        sort_order: str = "desc",
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[tuple[BrandDomain, list[BrandMemberDomain]]], int]:
        self._check_admin_permission(actor)
        async with self.brand_uow:
            return await self.brand_uow.brands.list_admin(
                search=search,
                moderation_status=moderation_status,
                is_verified=is_verified,
                include_deleted=include_deleted,
                sort_by=sort_by,
                sort_order=sort_order,
                limit=limit,
                offset=offset,
            )

    async def remoderate_brand(
        self,
        *,
        actor: UserDomain,
        brand_id: UUID,
    ) -> BrandDomain:
        self._check_admin_permission(actor)
        async with self.brand_uow:
            brand = await self.brand_uow.brands.get_by_id(brand_id)
            if brand is None:
                raise EntityNotFoundError("Brand not found")

            brand.moderation_status = ModerationStatus.PENDING
            brand.rejection_reason = None
            await self.brand_uow.brands.update(brand)
            await self.brand_uow.commit()
            return brand

    async def hide_all_brand_products(
        self,
        *,
        actor: UserDomain,
        brand_id: UUID,
    ) -> int:
        self._check_admin_permission(actor)
        async with self.catalog_uow:
            updated_count = await self.catalog_uow.products.hide_all_by_brand_id(
                brand_id
            )
            await self.catalog_uow.commit()
            return updated_count

    # ---------------- Categories ----------------

    async def list_categories(
        self,
        *,
        actor: UserDomain,
        search: str | None = None,
        sort_by: str = "sort_order",
        sort_order: str = "asc",
    ) -> list[CategoryDomain]:
        self._check_admin_permission(actor)
        async with self.catalog_uow:
            return await self.catalog_uow.categories.list_admin(
                search=search, sort_by=sort_by, sort_order=sort_order
            )

    async def create_category(
        self,
        *,
        actor: UserDomain,
        name: str,
        slug: str | None = None,
        parent_id: UUID | None = None,
        sort_order: int = 0,
    ) -> CategoryDomain:
        self._check_admin_permission(actor)
        clean_name = name.strip()
        if not clean_name:
            raise DomainValidationError("Category name cannot be empty")
        clean_slug = self._slugify(slug.strip() if slug else clean_name)

        async with self.catalog_uow:
            if await self.catalog_uow.categories.get_by_slug(clean_slug):
                raise EntityAlreadyExistsError(
                    f"Category with slug '{clean_slug}' already exists"
                )

            if parent_id is not None:
                parent = await self.catalog_uow.categories.get_by_id(parent_id)
                if parent is None:
                    raise EntityNotFoundError("Parent category not found")

            category = CategoryDomain(
                name=clean_name,
                slug=clean_slug,
                parent_id=parent_id,
                sort_order=sort_order,
                created_by=actor.id,
            )
            await self.catalog_uow.categories.add(category)
            await self.catalog_uow.commit()
            return category

    async def update_category(
        self,
        *,
        actor: UserDomain,
        category_id: UUID,
        name: str | None = None,
        slug: str | None = None,
        parent_id: UUID | None = None,
        sort_order: int | None = None,
    ) -> CategoryDomain:
        self._check_admin_permission(actor)
        async with self.catalog_uow:
            category = await self.catalog_uow.categories.get_by_id(category_id)
            if category is None:
                raise EntityNotFoundError("Category not found")

            if parent_id is not None:
                if parent_id == category_id:
                    raise DomainValidationError("Category cannot be its own parent")
                parent = await self.catalog_uow.categories.get_by_id(parent_id)
                if parent is None:
                    raise EntityNotFoundError("Parent category not found")
                category.parent_id = parent_id

            if name is not None:
                clean_name = name.strip()
                if not clean_name:
                    raise DomainValidationError("Category name cannot be empty")
                category.name = clean_name

            if slug is not None:
                clean_slug = self._slugify(slug.strip())
                if clean_slug != category.slug:
                    existing = await self.catalog_uow.categories.get_by_slug(clean_slug)
                    if existing and existing.id != category_id:
                        raise EntityAlreadyExistsError(
                            f"Category with slug '{clean_slug}' already exists"
                        )
                    category.slug = clean_slug

            if sort_order is not None:
                category.sort_order = sort_order

            await self.catalog_uow.categories.update(category)
            await self.catalog_uow.commit()
            return category

    async def delete_category(
        self,
        *,
        actor: UserDomain,
        category_id: UUID,
    ) -> None:
        self._check_admin_permission(actor)
        async with self.catalog_uow:
            category = await self.catalog_uow.categories.get_by_id(category_id)
            if category is None:
                raise EntityNotFoundError("Category not found")

            prods_count = await self.catalog_uow.products.count_by_category_id(
                category_id
            )
            if prods_count > 0:
                raise InvalidStateTransitionError(
                    f"Cannot delete category with {prods_count} associated product(s)"
                )

            await self.catalog_uow.categories.delete(category_id)
            await self.catalog_uow.commit()

    # ---------------- Products ----------------

    async def list_products(
        self,
        *,
        actor: UserDomain,
        search: str | None = None,
        moderation_status: str | None = None,
        is_hidden: int | None = None,
        is_limited: bool | None = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[ProductDomain], int]:
        self._check_admin_permission(actor)
        async with self.catalog_uow:
            return await self.catalog_uow.products.list_admin(
                search=search,
                moderation_status=moderation_status,
                is_hidden=is_hidden,
                is_limited=is_limited,
                sort_by=sort_by,
                sort_order=sort_order,
                limit=limit,
                offset=offset,
            )

    async def remoderate_product(
        self,
        *,
        actor: UserDomain,
        product_id: UUID,
    ) -> ProductDomain:
        self._check_admin_permission(actor)
        async with self.catalog_uow:
            product = await self.catalog_uow.products.get_by_id(
                product_id, include_unpublished=True
            )
            if product is None:
                raise EntityNotFoundError("Product not found")

            product.moderation_status = ModerationStatus.PENDING
            product.request_type = ModerationRequestType.EDIT
            product.rejection_reason = None
            product.updated_at = factory_now()
            await self.catalog_uow.products.update(product)
            await self.catalog_uow.commit()
            return product

    # ---------------- Reviews ----------------

    async def list_reviews(
        self,
        *,
        actor: UserDomain,
        search: str | None = None,
        rating: int | None = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[AdminReviewItemDomain], int]:
        self._check_admin_permission(actor)
        async with self.review_uow:
            return await self.review_uow.reviews.list_admin(
                search=search,
                rating=rating,
                sort_by=sort_by,
                sort_order=sort_order,
                limit=limit,
                offset=offset,
            )

    async def delete_review(
        self,
        *,
        actor: UserDomain,
        review_id: UUID,
    ) -> None:
        self._check_admin_permission(actor)
        async with self.review_uow:
            review = await self.review_uow.reviews.get_by_id(review_id)
            if review is None:
                raise EntityNotFoundError("Review not found")
            await self.review_uow.reviews.delete(review_id)
            await self.review_uow.commit()
