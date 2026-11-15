import asyncio
import json
import sys
from decimal import Decimal
from pathlib import Path
from uuid import UUID

from sqlalchemy import insert
from uuid6 import uuid7

# Ensure backend root is on sys.path
backend_root = Path(__file__).resolve().parent.parent
if str(backend_root) not in sys.path:
    sys.path.insert(0, str(backend_root))

from src.core import settings  # noqa: E402
from src.infrastructure.db import async_session_maker  # noqa: E402
from src.infrastructure.db.models import (  # noqa: E402
    CategoryModel,
    ProductModel,
    ProductVariantModel,
    UserModel,
    UserPersonalModel,
)
from src.infrastructure.security import (  # noqa: E402
    Argon2PasswordHasher,
    JwtTokenProvider,
)
from src.utils import factory_now  # noqa: E402


async def seed_enduro() -> None:
    if not settings.enduro_attack:
        print(
            "ERROR: seed_enduro.py can only be run when ENDURO_ATTACK=True. "
            "Please set ENDURO_ATTACK=True in your environment or .env file."
        )
        sys.exit(1)

    print(f"Starting ENDURO_ATTACK seeding on database: {settings.database_url}...")
    now = factory_now()
    hasher = Argon2PasswordHasher()
    token_provider = JwtTokenProvider()

    # Pre-hash password once for all 1000 users
    raw_password = "EnduroPassword123!"
    password_hash = hasher.hash(raw_password)

    admin_id = uuid7()
    admin_user = {
        "id": admin_id,
        "login": "enduro_admin",
        "email": "admin@enduro.test",
        "password_hash": password_hash,
        "verified_profile": True,
        "verified_email": True,
        "global_permissions": ["*"],
        "created_by": None,
        "created_at": now,
        "updated_at": now,
        "deleted_at": None,
    }

    # 1. Generate 1,000 test users
    print("Generating 1,000 test users...")
    users_data: list[dict] = [admin_user]
    personal_data: list[dict] = [
        {
            "id": admin_id,
            "firstname": "Enduro",
            "lastname": "Admin",
            "phone_number": "+1000000000",
            "created_by": admin_id,
            "created_at": now,
            "updated_at": now,
        }
    ]
    k6_records: list[dict] = []

    admin_access = token_provider.create_access_token(admin_id, ["*"])
    admin_refresh = token_provider.create_refresh_token(admin_id)
    k6_records.append(
        {
            "user_id": str(admin_id),
            "login": "enduro_admin",
            "password": raw_password,
            "access_token": admin_access,
            "refresh_token": admin_refresh,
            "is_admin": True,
        }
    )

    for i in range(1000):
        u_id = uuid7()
        u_login = f"enduro_user_{i:04d}"
        u_email = f"user_{i:04d}@enduro.test"
        users_data.append(
            {
                "id": u_id,
                "login": u_login,
                "email": u_email,
                "password_hash": password_hash,
                "verified_profile": True,
                "verified_email": True,
                "global_permissions": [],
                "created_by": admin_id,
                "created_at": now,
                "updated_at": now,
                "deleted_at": None,
            }
        )
        personal_data.append(
            {
                "id": u_id,
                "firstname": f"User{i}",
                "lastname": "Tester",
                "phone_number": f"+7999{i:07d}",
                "created_by": u_id,
                "created_at": now,
                "updated_at": now,
            }
        )
        acc_token = token_provider.create_access_token(u_id, [])
        ref_token = token_provider.create_refresh_token(u_id)
        k6_records.append(
            {
                "user_id": str(u_id),
                "login": u_login,
                "password": raw_password,
                "access_token": acc_token,
                "refresh_token": ref_token,
                "is_admin": False,
            }
        )

    # 2. Generate 50 categories (10 root, 40 sub)
    print("Generating 50 categories...")
    categories_data: list[dict] = []
    root_category_ids: list[UUID] = []

    for r in range(10):
        cat_id = uuid7()
        root_category_ids.append(cat_id)
        categories_data.append(
            {
                "id": cat_id,
                "name": f"Root Category {r}",
                "slug": f"root-cat-{r}",
                "parent_id": None,
                "sort_order": r,
                "created_by": admin_id,
                "created_at": now,
            }
        )

    all_cat_ids: list[UUID] = list(root_category_ids)
    for s in range(40):
        parent_id = root_category_ids[s % 10]
        cat_id = uuid7()
        all_cat_ids.append(cat_id)
        categories_data.append(
            {
                "id": cat_id,
                "name": f"Sub Category {s}",
                "slug": f"sub-cat-{s}",
                "parent_id": parent_id,
                "sort_order": s,
                "created_by": admin_id,
                "created_at": now,
            }
        )

    # 3. Generate 5,000 products & 15,000 SKU variants
    print("Generating 5,000 products and 15,000 variants...")
    products_data: list[dict] = []
    variants_data: list[dict] = []

    sizes = ["XS", "S", "M", "L", "XL"]
    colors = [
        ("Black", "#000000"),
        ("White", "#FFFFFF"),
        ("Navy", "#000080"),
        ("Red", "#FF0000"),
        ("Grey", "#808080"),
    ]

    for p in range(5000):
        p_id = uuid7()
        cat_id = all_cat_ids[p % len(all_cat_ids)]
        base_price = Decimal(str(50 + (p % 200) * 5))
        products_data.append(
            {
                "id": p_id,
                "category_id": cat_id,
                "title": f"Enduro Product {p:05d}",
                "slug": f"enduro-product-{p:05d}",
                "base_price": base_price,
                "description": f"High performance load testing product {p}",
                "attributes": {
                    "brand": "EnduroAttack",
                    "weight_g": 250,
                    "index": p,
                },
                "is_published": True,
                "created_by": admin_id,
                "created_at": now,
                "updated_at": now,
                "deleted_at": None,
            }
        )

        # 3 SKU variants per product = 15,000 variants
        for v in range(3):
            v_id = uuid7()
            size = sizes[(p + v) % len(sizes)]
            color_name, color_hex = colors[(p + v) % len(colors)]
            variants_data.append(
                {
                    "id": v_id,
                    "product_id": p_id,
                    "sku": f"SKU-{p:05d}-{v}",
                    "size": size,
                    "color_name": color_name,
                    "color_hex": color_hex,
                    "price_override": None,
                    "stock_quantity": 1000,
                    "created_by": admin_id,
                    "created_at": now,
                    "updated_at": now,
                }
            )

    # 4. Bulk insert into database
    print("Writing data in batches to PostgreSQL...")
    async with async_session_maker() as session:
        # Users
        batch_size = 500
        for i in range(0, len(users_data), batch_size):
            await session.execute(
                insert(UserModel).values(users_data[i : i + batch_size])
            )
        for i in range(0, len(personal_data), batch_size):
            await session.execute(
                insert(UserPersonalModel).values(personal_data[i : i + batch_size])
            )
        await session.commit()
        print(f"Inserted {len(users_data)} users.")

        # Categories
        await session.execute(insert(CategoryModel).values(categories_data))
        await session.commit()
        print(f"Inserted {len(categories_data)} categories.")

        # Products
        p_batch_size = 1000
        for i in range(0, len(products_data), p_batch_size):
            await session.execute(
                insert(ProductModel).values(products_data[i : i + p_batch_size])
            )
        await session.commit()
        print(f"Inserted {len(products_data)} products.")

        # Variants
        v_batch_size = 1000
        for i in range(0, len(variants_data), v_batch_size):
            await session.execute(
                insert(ProductVariantModel).values(variants_data[i : i + v_batch_size])
            )
        await session.commit()
        print(f"Inserted {len(variants_data)} variants.")

    # 5. Export k6 tokens & logins
    out_dir = backend_root / "scripts"
    out_dir.mkdir(parents=True, exist_ok=True)
    k6_file = out_dir / "k6_users.json"
    with open(k6_file, "w", encoding="utf-8") as f:
        json.dump(k6_records, f, indent=2)

    print(f"Successfully exported {len(k6_records)} users with tokens to {k6_file}")
    print("ENDURO_ATTACK seeding complete!")


if __name__ == "__main__":
    asyncio.run(seed_enduro())
