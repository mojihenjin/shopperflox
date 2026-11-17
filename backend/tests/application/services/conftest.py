from datetime import datetime
from types import TracebackType
from typing import Any, Self
from uuid import UUID

import pytest
from uuid6 import uuid7

from src.domain.exceptions import AuthenticationError, EntityAlreadyExistsError
from src.domain.interfaces import (
    UserAddressRepositoryProtocol,
    UserBanRepositoryProtocol,
    UserPersonalRepositoryProtocol,
    UserRepositoryProtocol,
)
from src.domain.models import (
    AdminReviewItemDomain,
    BrandDomain,
    BrandMemberDomain,
    BrandMemberRole,
    CartDomain,
    CartItemDomain,
    CategoryDomain,
    FavoriteDomain,
    ModerationStatus,
    OrderDomain,
    OrderItemDomain,
    OrderStatus,
    PaymentDomain,
    ProductDomain,
    ProductImageDomain,
    ProductVariantDomain,
    ReviewDomain,
    UserAddressDomain,
    UserBanDomain,
    UserDomain,
    UserPersonalDomain,
)
from src.utils import factory_now


class InMemoryUserRepository:
    def __init__(self) -> None:
        self.store: dict[UUID, UserDomain] = {}

    async def get_by_id(
        self, user_id: UUID, *, include_deleted: bool = False
    ) -> UserDomain | None:
        user = self.store.get(user_id)
        if user and user.is_deleted and not include_deleted:
            return None
        return user

    async def get_by_login(
        self, login: str, *, include_deleted: bool = False
    ) -> UserDomain | None:
        clean = login.strip().lower()
        for user in self.store.values():
            if user.login.strip().lower() == clean:
                if user.is_deleted and not include_deleted:
                    continue
                return user
        return None

    async def get_by_email(
        self, email: str, *, include_deleted: bool = False
    ) -> UserDomain | None:
        clean = email.strip().lower()
        for user in self.store.values():
            if user.email and user.email.strip().lower() == clean:
                if user.is_deleted and not include_deleted:
                    continue
                return user
        return None

    async def exists_active(self, login: str, email: str | None = None) -> bool:
        clean_login = login.strip().lower()
        clean_email = email.strip().lower() if email else None
        for user in self.store.values():
            if not user.is_deleted:
                if user.login.strip().lower() == clean_login or (
                    clean_email
                    and user.email
                    and user.email.strip().lower() == clean_email
                ):
                    return True
        return False

    async def add(self, user: UserDomain) -> None:
        self.store[user.id] = user

    async def update(self, user: UserDomain) -> None:
        self.store[user.id] = user

    async def count_superadmins(self) -> int:
        return sum(
            1
            for u in self.store.values()
            if not u.is_deleted and "*" in u.global_permissions
        )

    async def list_admin(
        self,
        *,
        search: str | None = None,
        status: str = "all",
        verified_profile: bool | None = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[tuple[UserDomain, UserBanDomain | None]], int]:
        users = list(self.store.values())
        if search:
            s = search.strip().lower()
            users = [
                u
                for u in users
                if s in u.login.lower() or (u.email and s in u.email.lower())
            ]
        if status == "deleted":
            users = [u for u in users if u.is_deleted]
        elif status == "active":
            users = [u for u in users if not u.is_deleted]
        if verified_profile is not None:
            users = [u for u in users if u.verified_profile == verified_profile]

        reverse = sort_order == "desc"
        if sort_by == "login":
            users.sort(key=lambda u: u.login, reverse=reverse)
        else:
            users.sort(key=lambda u: u.created_at, reverse=reverse)

        total = len(users)
        paged = users[offset : offset + limit]
        return [(u, None) for u in paged], total


class InMemoryUserPersonalRepository:
    def __init__(self) -> None:
        self.store: dict[UUID, UserPersonalDomain] = {}

    async def get_by_user_id(self, user_id: UUID) -> UserPersonalDomain | None:
        return self.store.get(user_id)

    async def get_by_phone(self, phone_number: str) -> UserPersonalDomain | None:
        for p in self.store.values():
            if p.phone_number == phone_number:
                return p
        return None

    async def add(self, personal: UserPersonalDomain) -> None:
        self.store[personal.id] = personal

    async def update(self, personal: UserPersonalDomain) -> None:
        self.store[personal.id] = personal


class InMemoryUserAddressRepository:
    def __init__(self) -> None:
        self.store: dict[UUID, UserAddressDomain] = {}

    async def get_by_id(self, address_id: UUID) -> UserAddressDomain | None:
        return self.store.get(address_id)

    async def list_by_user_id(
        self, user_id: UUID, *, limit: int = 50, offset: int = 0
    ) -> list[UserAddressDomain]:
        all_addrs = [a for a in self.store.values() if a.user_id == user_id]
        return all_addrs[offset : offset + limit]

    async def get_default_by_user_id(self, user_id: UUID) -> UserAddressDomain | None:
        for a in self.store.values():
            if a.user_id == user_id and a.is_default:
                return a
        return None

    async def unset_default_for_user(self, user_id: UUID) -> None:
        for a in self.store.values():
            if a.user_id == user_id and a.is_default:
                a.is_default = False

    async def add(self, address: UserAddressDomain) -> None:
        self.store[address.id] = address

    async def update(self, address: UserAddressDomain) -> None:
        self.store[address.id] = address

    async def delete(self, address_id: UUID) -> None:
        self.store.pop(address_id, None)


class InMemoryUserBanRepository:
    def __init__(self) -> None:
        self.store: dict[UUID, UserBanDomain] = {}

    async def get_active_by_user_id(
        self, user_id: UUID, at: datetime | None = None
    ) -> UserBanDomain | None:
        for ban in self.store.values():
            if ban.user_id == user_id and ban.is_active(at=at):
                return ban
        return None

    async def list_active_by_user_id(
        self, user_id: UUID, at: datetime | None = None
    ) -> list[UserBanDomain]:
        return [
            b
            for b in self.store.values()
            if b.user_id == user_id and b.is_active(at=at)
        ]

    async def list_by_user_id(self, user_id: UUID) -> list[UserBanDomain]:
        return [b for b in self.store.values() if b.user_id == user_id]

    async def add(self, ban: UserBanDomain) -> None:
        self.store[ban.id] = ban

    async def update(self, ban: UserBanDomain) -> None:
        self.store[ban.id] = ban


class FakeUserUnitOfWork:
    def __init__(self) -> None:
        self.users: UserRepositoryProtocol = InMemoryUserRepository()
        self.personal: UserPersonalRepositoryProtocol = InMemoryUserPersonalRepository()
        self.addresses: UserAddressRepositoryProtocol = InMemoryUserAddressRepository()
        self.bans: UserBanRepositoryProtocol = InMemoryUserBanRepository()
        self.committed = False
        self.rolled_back = False

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        if exc_type is not None:
            await self.rollback()

    async def commit(self) -> None:
        self.committed = True

    async def rollback(self) -> None:
        self.rolled_back = True


class FakePasswordHasher:
    def __init__(self) -> None:
        self.verify_call_count = 0

    def hash(self, password: str) -> str:
        return f"hashed_{password}"

    def verify(self, plain_password: str, hashed_password: str) -> bool:
        self.verify_call_count += 1
        return hashed_password == f"hashed_{plain_password}"

    async def verify_dummy(self, plain_password: str) -> None:
        self.verify_call_count += 1


class FakeTokenProvider:
    def create_access_token(
        self,
        user_id: UUID,
        permissions: list[str] | None = None,
        *,
        login: str | None = None,
        global_permissions: list[str] | None = None,
        verified_profile: bool = False,
        verified_email: bool = False,
    ) -> str:
        perms = (
            global_permissions
            if global_permissions is not None
            else (permissions or [])
        )
        return f"access_{user_id}_{','.join(perms)}"

    def create_refresh_token(self, user_id: UUID) -> str:
        return f"refresh_{user_id}_jti_{uuid7()}"

    def decode_token(
        self, token: str, expected_type: str | None = "access"
    ) -> dict[str, Any]:
        parts = token.split("_")
        if expected_type == "refresh":
            if not token.startswith("refresh_"):
                raise AuthenticationError("Invalid token type")
            jti = parts[3] if len(parts) > 3 else f"jti_{parts[1]}"
            return {
                "sub": parts[1],
                "type": "refresh",
                "jti": jti,
                "exp": 9999999999,
            }

        if not token.startswith("access_"):
            raise AuthenticationError("Invalid token")
        return {
            "sub": parts[1],
            "permissions": parts[2].split(",") if parts[2] else [],
            "type": "access",
        }


class FakeTokenBlacklist:
    def __init__(self) -> None:
        self.revoked_tokens: set[str] = set()
        self.revoked_users: dict[UUID, float] = {}

    async def is_revoked(self, jti: str) -> bool:
        return jti in self.revoked_tokens

    async def revoke(self, jti: str, ttl_seconds: int) -> None:
        self.revoked_tokens.add(jti)

    async def revoke_user(self, user_id: UUID, ttl_seconds: int = 2592000) -> None:
        self.revoked_users[user_id] = factory_now().timestamp()

    async def is_user_revoked(
        self, user_id: UUID, token_iat: float | None = None
    ) -> bool:
        revoked_at = self.revoked_users.get(user_id)
        if revoked_at is None:
            return False
        if token_iat is None:
            return True
        return revoked_at >= float(token_iat)


@pytest.fixture
def uow():
    return FakeUserUnitOfWork()


@pytest.fixture
def hasher():
    return FakePasswordHasher()


@pytest.fixture
def blacklist():
    return FakeTokenBlacklist()


@pytest.fixture
def token_provider():
    return FakeTokenProvider()


class InMemoryCategoryRepository:
    def __init__(self) -> None:
        self.store: dict[UUID, CategoryDomain] = {}

    async def get_by_id(self, category_id: UUID) -> CategoryDomain | None:
        return self.store.get(category_id)

    async def get_by_slug(self, slug: str) -> CategoryDomain | None:
        for c in self.store.values():
            if c.slug == slug:
                return c
        return None

    async def list_all(self) -> list[CategoryDomain]:
        return sorted(self.store.values(), key=lambda c: (c.sort_order, c.name))

    async def add(self, category: CategoryDomain) -> None:
        self.store[category.id] = category

    async def update(self, category: CategoryDomain) -> None:
        self.store[category.id] = category

    async def delete(self, category_id: UUID) -> None:
        self.store.pop(category_id, None)

    async def list_admin(
        self,
        *,
        search: str | None = None,
        sort_by: str = "sort_order",
        sort_order: str = "asc",
    ) -> list[CategoryDomain]:
        cats = list(self.store.values())
        if search:
            s = search.strip().lower()
            cats = [c for c in cats if s in c.name.lower() or s in c.slug.lower()]
        reverse = sort_order == "desc"
        if sort_by == "name":
            cats.sort(key=lambda c: c.name, reverse=reverse)
        elif sort_by == "created_at":
            cats.sort(key=lambda c: c.created_at, reverse=reverse)
        else:
            cats.sort(key=lambda c: c.sort_order, reverse=reverse)
        return cats


class InMemoryProductRepository:
    def __init__(self) -> None:
        self.store: dict[UUID, ProductDomain] = {}

    async def get_by_id(
        self, product_id: UUID, *, include_unpublished: bool = False
    ) -> ProductDomain | None:
        p = self.store.get(product_id)
        if not p or p.deleted_at is not None:
            return None
        if not include_unpublished and not p.is_published:
            return None
        return p

    async def get_by_slug(
        self, slug: str, *, include_unpublished: bool = False
    ) -> ProductDomain | None:
        for p in self.store.values():
            if p.slug == slug and p.deleted_at is None:
                if not include_unpublished and not p.is_published:
                    continue
                return p
        return None

    async def list_catalog(
        self,
        *,
        category_id: UUID | None = None,
        brand_id: UUID | None = None,
        brand_slug: str | None = None,
        min_price: Any = None,
        max_price: Any = None,
        search: str | None = None,
        size: str | None = None,
        color: str | None = None,
        is_limited: bool | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[ProductDomain], int]:
        matched = []
        for p in self.store.values():
            if (
                not p.is_published
                or p.deleted_at is not None
                or p.effective_hidden != 0
                or p.brand_is_deleted
            ):
                continue
            if category_id is not None and p.category_id != category_id:
                continue
            if brand_id is not None and p.brand_id != brand_id:
                continue
            if brand_slug is not None and p.brand_slug != brand_slug:
                continue
            if min_price is not None and p.base_price < min_price:
                continue
            if max_price is not None and p.base_price > max_price:
                continue
            if is_limited is not None and p.is_limited != is_limited:
                continue
            if search:
                s = search.lower()
                desc = p.description.lower() if p.description else ""
                if s not in p.title.lower() and s not in desc:
                    continue
            matched.append(p)
        return matched[offset : offset + limit], len(matched)

    async def list_self_worked_by_creator(
        self, creator_id: UUID
    ) -> list[ProductDomain]:
        return [
            p
            for p in self.store.values()
            if p.creator_id == creator_id
            and p.is_self_worked
            and p.is_published
            and (
                p.moderation_status == "approved"
                or p.moderation_status == ModerationStatus.APPROVED
            )
            and p.is_hidden == 0
            and p.deleted_at is None
        ]

    async def increment_views(self, product_id: UUID) -> None:
        p = self.store.get(product_id)
        if p:
            p.views_count += 1

    async def increment_orders(self, product_id: UUID, quantity: int) -> None:
        p = self.store.get(product_id)
        if p:
            p.orders_count += quantity

    async def add(self, product: ProductDomain) -> None:
        self.store[product.id] = product

    async def update(self, product: ProductDomain) -> None:
        self.store[product.id] = product

    async def update_brand_name_for_products(
        self, brand_id: UUID, brand_name: str
    ) -> None:
        for p in self.store.values():
            if p.brand_id == brand_id:
                p.brand = brand_name

    async def list_pending_products(
        self,
        *,
        request_type: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[ProductDomain], int]:
        matched = []
        for p in sorted(self.store.values(), key=lambda x: x.created_at):
            if p.deleted_at is not None or p.moderation_status != "pending":
                continue
            if request_type and p.request_type != request_type:
                continue
            matched.append(p)
        return matched[offset : offset + limit], len(matched)

    async def count_pending_products(self) -> int:
        return sum(
            1
            for p in self.store.values()
            if p.deleted_at is None and p.moderation_status == "pending"
        )

    async def count_by_category_id(self, category_id: UUID) -> int:
        return sum(
            1
            for p in self.store.values()
            if p.deleted_at is None and p.category_id == category_id
        )

    async def hide_all_by_brand_id(self, brand_id: UUID) -> int:
        count = 0
        for p in self.store.values():
            if p.deleted_at is None and p.brand_id == brand_id:
                p.is_hidden = 2
                count += 1
        return count

    async def list_admin(
        self,
        *,
        search: str | None = None,
        moderation_status: str | None = None,
        is_hidden: int | None = None,
        is_limited: bool | None = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[ProductDomain], int]:
        prods = [p for p in self.store.values() if p.deleted_at is None]
        if search:
            s = search.strip().lower()
            prods = [
                p
                for p in prods
                if s in p.title.lower()
                or s in p.slug.lower()
                or (p.brand and s in p.brand.lower())
            ]
        if moderation_status:
            prods = [
                p
                for p in prods
                if str(p.moderation_status).lower() == str(moderation_status).lower()
            ]
        if is_hidden is not None:
            prods = [p for p in prods if p.is_hidden == is_hidden]
        if is_limited is not None:
            prods = [p for p in prods if p.is_limited == is_limited]

        reverse = sort_order == "desc"
        if sort_by == "base_price":
            prods.sort(key=lambda p: p.base_price, reverse=reverse)
        elif sort_by == "views_count":
            prods.sort(key=lambda p: p.views_count, reverse=reverse)
        elif sort_by == "orders_count":
            prods.sort(key=lambda p: p.orders_count, reverse=reverse)
        elif sort_by == "title":
            prods.sort(key=lambda p: p.title, reverse=reverse)
        else:
            prods.sort(key=lambda p: p.created_at, reverse=reverse)

        total = len(prods)
        return prods[offset : offset + limit], total


class InMemoryProductVariantRepository:
    def __init__(self) -> None:
        self.store: dict[UUID, ProductVariantDomain] = {}

    async def get_by_id(self, variant_id: UUID) -> ProductVariantDomain | None:
        return self.store.get(variant_id)

    async def get_by_sku(self, sku: str) -> ProductVariantDomain | None:
        for v in self.store.values():
            if v.sku == sku:
                return v
        return None

    async def get_by_ids_for_update(
        self, variant_ids: list[UUID]
    ) -> list[ProductVariantDomain]:
        return [self.store[v_id] for v_id in sorted(variant_ids) if v_id in self.store]

    async def list_by_product_id(self, product_id: UUID) -> list[ProductVariantDomain]:
        return [v for v in self.store.values() if v.product_id == product_id]

    async def add(self, variant: ProductVariantDomain) -> None:
        self.store[variant.id] = variant

    async def update(self, variant: ProductVariantDomain) -> None:
        self.store[variant.id] = variant

    async def increment_orders(self, variant_id: UUID, quantity: int) -> None:
        v = self.store.get(variant_id)
        if v:
            v.orders_count += quantity

    async def delete(self, variant_id: UUID) -> None:
        self.store.pop(variant_id, None)


class InMemoryProductImageRepository:
    def __init__(self) -> None:
        self.store: dict[UUID, ProductImageDomain] = {}

    async def get_by_id(self, image_id: UUID) -> ProductImageDomain | None:
        return self.store.get(image_id)

    async def list_by_product_id(self, product_id: UUID) -> list[ProductImageDomain]:
        imgs = [i for i in self.store.values() if i.product_id == product_id]
        return sorted(imgs, key=lambda x: (x.sort_order, x.created_at))

    async def unset_main_for_product(self, product_id: UUID) -> None:
        for i in self.store.values():
            if i.product_id == product_id and i.is_main:
                i.is_main = False

    async def add(self, image: ProductImageDomain) -> None:
        self.store[image.id] = image

    async def update(self, image: ProductImageDomain) -> None:
        self.store[image.id] = image

    async def delete(self, image_id: UUID) -> None:
        self.store.pop(image_id, None)


class InMemoryFavoriteRepository:
    def __init__(self, product_repo: InMemoryProductRepository) -> None:
        self.store: dict[tuple[UUID, UUID], FavoriteDomain] = {}
        self.product_repo = product_repo

    async def exists(self, user_id: UUID, product_id: UUID) -> bool:
        return (user_id, product_id) in self.store

    async def list_user_favorite_products(
        self, user_id: UUID, *, limit: int = 20, offset: int = 0
    ) -> tuple[list[ProductDomain], int]:
        prods = []
        for u, p_id in self.store:
            if u == user_id:
                p = await self.product_repo.get_by_id(p_id, include_unpublished=False)
                if p and p.is_available:
                    prods.append(p)
        return prods[offset : offset + limit], len(prods)

    async def add(self, favorite: FavoriteDomain) -> None:
        self.store[(favorite.user_id, favorite.product_id)] = favorite

    async def delete(self, user_id: UUID, product_id: UUID) -> None:
        self.store.pop((user_id, product_id), None)


class InMemoryBrandRepository:
    def __init__(self) -> None:
        self.brands: dict[UUID, BrandDomain] = {}
        self.members: dict[tuple[UUID, UUID], BrandMemberDomain] = {}

    async def get_by_id(self, brand_id: UUID) -> BrandDomain | None:
        return self.brands.get(brand_id)

    async def get_by_slug(self, slug: str) -> BrandDomain | None:
        for b in self.brands.values():
            if b.slug == slug:
                return b
        return None

    async def get_by_name(self, name: str) -> BrandDomain | None:
        clean = name.strip().lower()
        for b in self.brands.values():
            if b.name.strip().lower() == clean:
                return b
        return None

    async def list_active(self, limit: int = 100, offset: int = 0) -> list[BrandDomain]:
        matched = [
            b
            for b in self.brands.values()
            if not b.is_deleted and b.moderation_status == "approved"
        ]
        matched.sort(key=lambda x: x.name)
        return matched[offset : offset + limit]

    async def list_pending(
        self, limit: int = 100, offset: int = 0
    ) -> list[BrandDomain]:
        matched = [
            b
            for b in self.brands.values()
            if not b.is_deleted and b.moderation_status == "pending"
        ]
        matched.sort(key=lambda x: x.created_at, reverse=True)
        return matched[offset : offset + limit]

    async def count_pending(self) -> int:
        return sum(
            1
            for b in self.brands.values()
            if not b.is_deleted and b.moderation_status == "pending"
        )

    async def list_admin(
        self,
        *,
        search: str | None = None,
        moderation_status: str | None = None,
        is_verified: bool | None = None,
        include_deleted: bool = True,
        sort_by: str = "created_at",
        sort_order: str = "desc",
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[tuple[BrandDomain, list[BrandMemberDomain]]], int]:
        brands = list(self.brands.values())
        if not include_deleted:
            brands = [b for b in brands if not b.is_deleted]
        if search:
            s = search.strip().lower()
            brands = [b for b in brands if s in b.name.lower() or s in b.slug.lower()]
        if moderation_status:
            brands = [
                b
                for b in brands
                if str(b.moderation_status).lower() == str(moderation_status).lower()
            ]
        if is_verified is not None:
            brands = [b for b in brands if b.is_verified == is_verified]

        reverse = sort_order == "desc"
        if sort_by == "name":
            brands.sort(key=lambda b: b.name, reverse=reverse)
        elif sort_by == "views_count":
            brands.sort(key=lambda b: b.views_count, reverse=reverse)
        elif sort_by == "orders_count":
            brands.sort(key=lambda b: b.orders_count, reverse=reverse)
        else:
            brands.sort(key=lambda b: b.created_at, reverse=reverse)

        total = len(brands)
        paged = brands[offset : offset + limit]
        result = []
        for b in paged:
            mems = [m for (b_id, _), m in self.members.items() if b_id == b.id]
            result.append((b, mems))
        return result, total

    async def increment_views(self, brand_id: UUID) -> None:
        b = self.brands.get(brand_id)
        if b:
            b.views_count += 1

    async def increment_orders(self, brand_id: UUID, quantity: int) -> None:
        b = self.brands.get(brand_id)
        if b:
            b.orders_count += quantity

    async def list_by_user_id(
        self, user_id: UUID
    ) -> list[tuple[BrandDomain, BrandMemberRole]]:
        res = []
        for (b_id, u_id), m in self.members.items():
            if u_id == user_id:
                brand = self.brands.get(b_id)
                if brand:
                    res.append((brand, m.role))
        res.sort(key=lambda x: x[0].name)
        return res

    async def add(self, brand: BrandDomain) -> None:
        for b in self.brands.values():
            if b.slug == brand.slug or b.name.lower() == brand.name.lower():
                raise EntityAlreadyExistsError("Brand already exists")
        self.brands[brand.id] = brand

    async def update(self, brand: BrandDomain) -> None:
        self.brands[brand.id] = brand

    async def add_member(self, member: BrandMemberDomain) -> None:
        key = (member.brand_id, member.user_id)
        if key in self.members:
            raise EntityAlreadyExistsError("Member already exists")
        self.members[key] = member

    async def update_member(self, member: BrandMemberDomain) -> None:
        key = (member.brand_id, member.user_id)
        self.members[key] = member

    async def remove_member(self, brand_id: UUID, user_id: UUID) -> None:
        self.members.pop((brand_id, user_id), None)

    async def get_member(
        self, brand_id: UUID, user_id: UUID
    ) -> BrandMemberDomain | None:
        return self.members.get((brand_id, user_id))

    async def list_members(self, brand_id: UUID) -> list[BrandMemberDomain]:
        res = [m for (b_id, _), m in self.members.items() if b_id == brand_id]
        res.sort(key=lambda x: x.created_at)
        return res

    async def count_representatives(self, brand_id: UUID) -> int:
        return sum(
            1
            for (b_id, _), m in self.members.items()
            if b_id == brand_id and m.role == BrandMemberRole.REPRESENTATIVE
        )


class FakeCatalogUnitOfWork:
    def __init__(self) -> None:
        self.categories = InMemoryCategoryRepository()
        self.products = InMemoryProductRepository()
        self.variants = InMemoryProductVariantRepository()
        self.images = InMemoryProductImageRepository()
        self.favorites = InMemoryFavoriteRepository(self.products)
        self.brands = InMemoryBrandRepository()
        self.committed = False
        self.rolled_back = False

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        if exc_type is not None:
            await self.rollback()

    async def commit(self) -> None:
        self.committed = True

    async def rollback(self) -> None:
        self.rolled_back = True


class FakeBrandUnitOfWork:
    def __init__(
        self,
        brands_repo: InMemoryBrandRepository | None = None,
        users_repo: InMemoryUserRepository | None = None,
        products_repo: InMemoryProductRepository | None = None,
    ) -> None:
        self.brands = brands_repo or InMemoryBrandRepository()
        self.users = users_repo or InMemoryUserRepository()
        self.products = products_repo or InMemoryProductRepository()
        self.committed = False
        self.rolled_back = False

    async def commit(self) -> None:
        self.committed = True

    async def rollback(self) -> None:
        self.rolled_back = True

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        if exc_type is not None:
            await self.rollback()


@pytest.fixture
def brand_uow():
    return FakeBrandUnitOfWork()


@pytest.fixture
def catalog_uow():
    return FakeCatalogUnitOfWork()


class InMemoryCartRepository:
    def __init__(self) -> None:
        self.carts: dict[UUID, CartDomain] = {}
        self.items: dict[tuple[UUID, UUID], CartItemDomain] = {}

    async def get_by_user_id(self, user_id: UUID) -> CartDomain | None:
        for c in self.carts.values():
            if c.user_id == user_id:
                return c
        return None

    async def get_or_create_for_user(self, user_id: UUID) -> CartDomain:
        cart = await self.get_by_user_id(user_id)
        if cart is not None:
            return cart
        cart = CartDomain(id=uuid7(), user_id=user_id, created_by=user_id)
        self.carts[cart.id] = cart
        return cart

    async def list_items(self, cart_id: UUID) -> list[CartItemDomain]:
        return [i for (c_id, _), i in self.items.items() if c_id == cart_id]

    async def get_item(self, cart_id: UUID, variant_id: UUID) -> CartItemDomain | None:
        return self.items.get((cart_id, variant_id))

    async def upsert_item(
        self, cart_id: UUID, variant_id: UUID, quantity: int
    ) -> CartItemDomain:
        key = (cart_id, variant_id)
        if key in self.items:
            item = self.items[key]
            item.quantity = quantity
        else:
            item = CartItemDomain(
                id=uuid7(),
                cart_id=cart_id,
                variant_id=variant_id,
                quantity=quantity,
            )
            self.items[key] = item
        return item

    async def remove_item(self, cart_id: UUID, variant_id: UUID) -> None:
        self.items.pop((cart_id, variant_id), None)

    async def clear_cart(self, cart_id: UUID) -> None:
        to_del = [key for key in self.items if key[0] == cart_id]
        for key in to_del:
            self.items.pop(key, None)


class InMemoryOrderRepository:
    def __init__(self) -> None:
        self.orders: dict[UUID, OrderDomain] = {}
        self.items: dict[UUID, list[OrderItemDomain]] = {}

    async def get_by_id(
        self, order_id: UUID, *, for_update: bool = False
    ) -> OrderDomain | None:
        return self.orders.get(order_id)

    async def list_items(self, order_id: UUID) -> list[OrderItemDomain]:
        return self.items.get(order_id, [])

    async def list_by_user_id(
        self, user_id: UUID, limit: int = 20, offset: int = 0
    ) -> tuple[list[OrderDomain], int]:
        user_orders = [o for o in self.orders.values() if o.user_id == user_id]
        user_orders.sort(key=lambda x: x.created_at, reverse=True)
        return user_orders[offset : offset + limit], len(user_orders)

    async def list_all(
        self,
        status: OrderStatus | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[OrderDomain], int]:
        all_orders = list(self.orders.values())
        if status is not None:
            all_orders = [o for o in all_orders if o.status == status]
        all_orders.sort(key=lambda x: x.created_at, reverse=True)
        return all_orders[offset : offset + limit], len(all_orders)

    async def has_user_purchased_product(self, user_id: UUID, product_id: UUID) -> bool:
        for order in self.orders.values():
            if order.user_id == user_id and order.status == OrderStatus.DELIVERED:
                # We check order items' variant
                items = self.items.get(order.id, [])
                for i in items:
                    # In test setup, we can tag or verify variant's product
                    if getattr(i, "_product_id", None) == product_id:
                        return True
        return False

    async def add(
        self, order: OrderDomain, items: list[OrderItemDomain] | None = None
    ) -> None:
        self.orders[order.id] = order
        if items:
            self.items[order.id] = list(items)

    async def update(self, order: OrderDomain) -> None:
        self.orders[order.id] = order

    async def get_item_by_id(self, item_id: UUID) -> OrderItemDomain | None:
        for items_list in self.items.values():
            for item in items_list:
                if item.id == item_id:
                    return item
        return None

    async def update_item(self, item: OrderItemDomain) -> None:
        for items_list in self.items.values():
            for i, existing in enumerate(items_list):
                if existing.id == item.id:
                    items_list[i] = item
                    return


class InMemoryPaymentRepository:
    def __init__(self) -> None:
        self.payments: dict[UUID, PaymentDomain] = {}

    async def get_by_id(
        self, payment_id: UUID, *, for_update: bool = False
    ) -> PaymentDomain | None:
        return self.payments.get(payment_id)

    async def get_by_order_id(
        self, order_id: UUID, *, for_update: bool = False
    ) -> PaymentDomain | None:
        for p in self.payments.values():
            if p.order_id == order_id:
                return p
        return None

    async def get_by_external_id(
        self, external_transaction_id: str, *, for_update: bool = False
    ) -> PaymentDomain | None:
        for p in self.payments.values():
            if p.external_id == external_transaction_id:
                return p
        return None

    async def add(self, payment: PaymentDomain) -> None:
        self.payments[payment.id] = payment

    async def update(self, payment: PaymentDomain) -> None:
        self.payments[payment.id] = payment


class InMemoryReviewRepository:
    def __init__(self) -> None:
        self.reviews: dict[UUID, ReviewDomain] = {}

    async def get_by_id(self, review_id: UUID) -> ReviewDomain | None:
        return self.reviews.get(review_id)

    async def get_by_user_and_product(
        self, user_id: UUID, product_id: UUID
    ) -> ReviewDomain | None:
        for r in self.reviews.values():
            if r.user_id == user_id and r.product_id == product_id:
                return r
        return None

    async def list_by_product_id(
        self, product_id: UUID, limit: int = 20, offset: int = 0
    ) -> tuple[list[ReviewDomain], int]:
        matched = [
            r
            for r in self.reviews.values()
            if r.product_id == product_id and r.is_published
        ]
        matched.sort(key=lambda x: x.created_at, reverse=True)
        return matched[offset : offset + limit], len(matched)

    async def add(self, review: ReviewDomain) -> None:
        self.reviews[review.id] = review

    async def delete(self, review_id: UUID) -> None:
        self.reviews.pop(review_id, None)

    async def list_admin(
        self,
        *,
        search: str | None = None,
        rating: int | None = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[AdminReviewItemDomain], int]:
        from src.domain.models import AdminReviewItemDomain

        matched = list(self.reviews.values())
        if rating is not None:
            matched = [r for r in matched if r.rating == rating]
        if search:
            s = search.strip().lower()
            matched = [r for r in matched if r.comment and s in r.comment.lower()]

        reverse = sort_order == "desc"
        if sort_by == "rating":
            matched.sort(key=lambda x: x.rating, reverse=reverse)
        else:
            matched.sort(key=lambda x: x.created_at, reverse=reverse)

        total = len(matched)
        paged = matched[offset : offset + limit]
        items = [
            AdminReviewItemDomain(
                review=r,
                user_login="user",
                product_title="Product",
                product_slug="product",
            )
            for r in paged
        ]
        return items, total


class FakeCartUnitOfWork:
    def __init__(
        self,
        variants_repo: InMemoryProductVariantRepository | None = None,
        products_repo: InMemoryProductRepository | None = None,
        images_repo: InMemoryProductImageRepository | None = None,
    ) -> None:
        self.carts = InMemoryCartRepository()
        self.variants = variants_repo or InMemoryProductVariantRepository()
        self.products = products_repo or InMemoryProductRepository()
        self.images = images_repo or InMemoryProductImageRepository()
        self.committed = False
        self.rolled_back = False

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        if exc_type is not None:
            await self.rollback()

    async def commit(self) -> None:
        self.committed = True

    async def rollback(self) -> None:
        self.rolled_back = True


class FakeOrderUnitOfWork:
    def __init__(
        self,
        carts_repo: InMemoryCartRepository | None = None,
        variants_repo: InMemoryProductVariantRepository | None = None,
        products_repo: InMemoryProductRepository | None = None,
        addresses_repo: InMemoryUserAddressRepository | None = None,
        brands_repo: InMemoryBrandRepository | None = None,
    ) -> None:
        self.orders = InMemoryOrderRepository()
        self.carts = carts_repo or InMemoryCartRepository()
        self.variants = variants_repo or InMemoryProductVariantRepository()
        self.products = products_repo or InMemoryProductRepository()
        self.addresses = addresses_repo or InMemoryUserAddressRepository()
        self.payments = InMemoryPaymentRepository()
        self.brands = brands_repo or InMemoryBrandRepository()
        self.committed = False
        self.rolled_back = False

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        if exc_type is not None:
            await self.rollback()

    async def commit(self) -> None:
        self.committed = True

    async def rollback(self) -> None:
        self.rolled_back = True


class FakeReviewUnitOfWork:
    def __init__(
        self,
        orders_repo: InMemoryOrderRepository | None = None,
        products_repo: InMemoryProductRepository | None = None,
    ) -> None:
        self.reviews = InMemoryReviewRepository()
        self.orders = orders_repo or InMemoryOrderRepository()
        self.products = products_repo or InMemoryProductRepository()
        self.committed = False
        self.rolled_back = False

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        if exc_type is not None:
            await self.rollback()

    async def commit(self) -> None:
        self.committed = True

    async def rollback(self) -> None:
        self.rolled_back = True


@pytest.fixture
def cart_uow():
    return FakeCartUnitOfWork()


@pytest.fixture
def order_uow():
    return FakeOrderUnitOfWork()


@pytest.fixture
def review_uow():
    return FakeReviewUnitOfWork()
