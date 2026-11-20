from uuid import UUID

import pytest
from httpx import AsyncClient

from src.api.dependencies import get_task_queue, get_user_uow
from src.infrastructure.security import JwtTokenProvider


@pytest.fixture
def auth_headers():
    provider = JwtTokenProvider()

    def _make(user_id: UUID, permissions: list[str] | None = None):
        perms = permissions or []
        token = provider.create_access_token(user_id, perms)
        return {"Authorization": f"Bearer {token}"}

    return _make


@pytest.mark.anyio
async def test_full_moderation_lifecycle_and_triggers(
    client: AsyncClient, auth_headers
):
    user_uow_factory = client._transport.app.dependency_overrides.get(get_user_uow)  # type: ignore
    tq_factory = client._transport.app.dependency_overrides.get(get_task_queue)  # type: ignore
    user_uow = user_uow_factory()
    tq = tq_factory()

    # 1. Register moderator, creator, stranger
    reg_mod = await client.post(
        "/api/v1/auth/register",
        json={"login": "mod_reviewer", "password": "Password123!"},
    )
    mod_id = UUID(reg_mod.json()["body"]["user"]["id"])
    mod_headers = auth_headers(mod_id, permissions=["mod:approve_manager"])

    reg_creator = await client.post(
        "/api/v1/auth/register",
        json={"login": "creator_artist", "password": "Password123!"},
    )
    creator_id = UUID(reg_creator.json()["body"]["user"]["id"])
    creator_headers = auth_headers(creator_id, permissions=["creator:products"])

    # Configure creator's verified email and permissions in DB
    async with user_uow:
        creator_user = await user_uow.users.get_by_id(creator_id)
        assert creator_user is not None
        creator_user.email = "creator@shopperflox.com"
        creator_user.verified_email = True
        creator_user.global_permissions = ["creator:products"]
        await user_uow.users.update(creator_user)

        mod_user = await user_uow.users.get_by_id(mod_id)
        assert mod_user is not None
        mod_user.global_permissions = ["mod:approve_manager", "catalog:manage"]
        await user_uow.users.update(mod_user)

        await user_uow.commit()

    reg_stranger = await client.post(
        "/api/v1/auth/register",
        json={"login": "stranger_buyer", "password": "Password123!"},
    )
    stranger_id = UUID(reg_stranger.json()["body"]["user"]["id"])
    stranger_headers = auth_headers(stranger_id)

    # 2. Setup category
    cat_res = await client.post(
        "/api/v1/categories",
        headers=mod_headers,
        json={"name": "Cyber Wear", "slug": "cyber-wear"},
    )
    assert cat_res.status_code == 201
    category_id = cat_res.json()["body"]["id"]

    # =========================================================================
    # Step 1: Product creation -> PENDING, CREATE, hidden from public catalog
    # =========================================================================
    p1_res = await client.post(
        "/api/v1/products",
        headers=creator_headers,
        json={
            "category_id": category_id,
            "title": "Cyberpunk Vest",
            "slug": "cyberpunk-vest",
            "base_price": 3500.0,
            "is_published": True,
        },
    )
    assert p1_res.status_code == 201
    p1_data = p1_res.json()["body"]
    p1_id = p1_data["id"]
    assert p1_data["moderation_status"] == "pending"
    assert p1_data["request_type"] == "CREATE"
    assert p1_data["rejection_reason"] is None

    # Hidden from public catalog
    cat_list = await client.get("/api/v1/products")
    assert cat_list.status_code == 200
    assert not any(p["id"] == p1_id for p in cat_list.json()["body"])

    # Anonymous / stranger cannot view pending product by direct slug
    guest_view = await client.get("/api/v1/products/cyberpunk-vest")
    assert guest_view.status_code == 404

    stranger_view = await client.get(
        "/api/v1/products/cyberpunk-vest", headers=stranger_headers
    )
    assert stranger_view.status_code == 404

    # Creator and moderator can view pending product
    creator_view = await client.get(
        "/api/v1/products/cyberpunk-vest", headers=creator_headers
    )
    assert creator_view.status_code == 200
    assert creator_view.json()["body"]["product"]["id"] == p1_id

    mod_view = await client.get("/api/v1/products/cyberpunk-vest", headers=mod_headers)
    assert mod_view.status_code == 200

    # Moderator sees it in pending queue
    queue_res = await client.get(
        "/api/v1/moderation/products?request_type=CREATE", headers=mod_headers
    )
    assert queue_res.status_code == 200
    queue_items = queue_res.json()["body"]
    assert any(p["id"] == p1_id for p in queue_items)
    assert queue_res.json()["metadata"]["total"] >= 1

    # Pending count
    count_res = await client.get(
        "/api/v1/moderation/products/pending-count", headers=mod_headers
    )
    assert count_res.status_code == 200
    assert count_res.json()["body"]["pending_count"] >= 1

    # Stranger forbidden on moderation queue
    forbidden_queue = await client.get(
        "/api/v1/moderation/products", headers=stranger_headers
    )
    assert forbidden_queue.status_code == 403

    # =========================================================================
    # Step 2: Rejection with reason and without reason + email task enqueue
    # =========================================================================
    # P2: with reason
    p2_res = await client.post(
        "/api/v1/products",
        headers=creator_headers,
        json={
            "category_id": category_id,
            "title": "Reject Reason Item",
            "slug": "reject-reason-item",
            "base_price": 1000.0,
            "is_published": True,
        },
    )
    p2_id = p2_res.json()["body"]["id"]

    tq.sent_emails.clear()
    reject_reason_res = await client.post(
        f"/api/v1/moderation/products/{p2_id}/reject",
        headers=mod_headers,
        json={"reason": "Low resolution image & incomplete description"},
    )
    assert reject_reason_res.status_code == 200
    p2_mod = reject_reason_res.json()["body"]
    assert p2_mod["moderation_status"] == "rejected"
    assert p2_mod["rejection_reason"] == "Low resolution image & incomplete description"

    # Check notification sent to creator
    notifs_res = await client.get("/api/v1/notifications", headers=creator_headers)
    assert notifs_res.status_code == 200
    c_notifs = notifs_res.json()["body"]
    assert len(c_notifs) >= 1
    latest_notif = c_notifs[0]
    assert latest_notif["title"] == "Заявка отклонена"
    assert (
        latest_notif["body"]
        == "Отклонено: Low resolution image & incomplete description"
    )
    assert latest_notif["link"] == "/creator/products/reject-reason-item/edit"

    # Check email enqueued
    assert len(tq.sent_emails) == 1
    to_email, subject, body_text = tq.sent_emails[0]
    assert to_email == "creator@shopperflox.com"
    assert subject == "Заявка отклонена"
    assert "Low resolution image & incomplete description" in body_text

    # P3: without reason
    p3_res = await client.post(
        "/api/v1/products",
        headers=creator_headers,
        json={
            "category_id": category_id,
            "title": "Reject Blank Item",
            "slug": "reject-blank-item",
            "base_price": 1200.0,
            "is_published": True,
        },
    )
    p3_id = p3_res.json()["body"]["id"]

    tq.sent_emails.clear()
    reject_blank_res = await client.post(
        f"/api/v1/moderation/products/{p3_id}/reject",
        headers=mod_headers,
        json={"reason": None},
    )
    assert reject_blank_res.status_code == 200
    p3_mod = reject_blank_res.json()["body"]
    assert p3_mod["moderation_status"] == "rejected"
    assert p3_mod["rejection_reason"] is None

    notifs_res2 = await client.get("/api/v1/notifications", headers=creator_headers)
    latest_notif2 = notifs_res2.json()["body"][0]
    assert latest_notif2["title"] == "Заявка отклонена"
    assert latest_notif2["body"] == "Отклонено: Причина не указана"

    # Editing a rejected product transitions it back to PENDING and clears reason
    edit_rejected = await client.patch(
        f"/api/v1/products/{p3_id}",
        headers=creator_headers,
        json={"title": "Reject Blank Item (Fixed)"},
    )
    assert edit_rejected.status_code == 200
    p3_fixed = edit_rejected.json()["body"]
    assert p3_fixed["moderation_status"] == "pending"
    assert p3_fixed["rejection_reason"] is None

    # =========================================================================
    # Step 3: Approval -> Public catalog -> Operational edit vs Substantial edit
    # =========================================================================
    approve_res = await client.post(
        f"/api/v1/moderation/products/{p1_id}/approve",
        headers=mod_headers,
    )
    assert approve_res.status_code == 200
    p1_appr = approve_res.json()["body"]
    assert p1_appr["moderation_status"] == "approved"
    assert p1_appr["rejection_reason"] is None

    # Creator receives approval notification (without email task)
    tq.sent_emails.clear()
    notifs_appr = await client.get("/api/v1/notifications", headers=creator_headers)
    appr_notif = notifs_appr.json()["body"][0]
    assert appr_notif["title"] == "Заявка одобрена"
    assert "прошёл проверку и опубликован" in appr_notif["body"]
    assert len(tq.sent_emails) == 0

    # Public catalog now includes P1
    pub_list = await client.get("/api/v1/products")
    assert any(p["id"] == p1_id for p in pub_list.json()["body"])

    # Public direct slug view works for guest
    guest_appr = await client.get("/api/v1/products/cyberpunk-vest")
    assert guest_appr.status_code == 200

    # 3a. Operational changes: base_price and is_limited DO NOT trigger re-moderation
    op_edit = await client.patch(
        f"/api/v1/products/{p1_id}",
        headers=creator_headers,
        json={"base_price": 3999.0, "is_limited": True},
    )
    assert op_edit.status_code == 200
    assert op_edit.json()["body"]["moderation_status"] == "approved"

    # Still in public catalog
    pub_list2 = await client.get("/api/v1/products")
    assert any(p["id"] == p1_id for p in pub_list2.json()["body"])

    # 3b. Substantial change: changing title transitions APPROVED -> PENDING (request_type=EDIT)
    sub_edit = await client.patch(
        f"/api/v1/products/{p1_id}",
        headers=creator_headers,
        json={"title": "Cyberpunk Vest MK-II"},
    )
    assert sub_edit.status_code == 200
    sub_data = sub_edit.json()["body"]
    assert sub_data["moderation_status"] == "pending"
    assert sub_data["request_type"] == "EDIT"
    assert sub_data["rejection_reason"] is None

    # Disappears from public catalog
    pub_list3 = await client.get("/api/v1/products")
    assert not any(p["id"] == p1_id for p in pub_list3.json()["body"])

    # Appears in moderation queue under EDIT filter
    edit_queue = await client.get(
        "/api/v1/moderation/products?request_type=EDIT", headers=mod_headers
    )
    assert edit_queue.status_code == 200
    assert any(p["id"] == p1_id for p in edit_queue.json()["body"])

    # Re-approve MK-II
    re_appr = await client.post(
        f"/api/v1/moderation/products/{p1_id}/approve",
        headers=mod_headers,
    )
    assert re_appr.status_code == 200
    assert re_appr.json()["body"]["moderation_status"] == "approved"

    # 3c. Adding image triggers re-moderation back to PENDING (EDIT)
    add_img_res = await client.post(
        f"/api/v1/products/{p1_id}/images",
        headers=creator_headers,
        json={"url": "https://cdn.example.com/vest-mk2.jpg", "is_main": True},
    )
    assert add_img_res.status_code == 201

    # Check product is PENDING again
    p1_check = await client.get(
        "/api/v1/products/cyberpunk-vest", headers=creator_headers
    )
    assert p1_check.status_code == 200
    assert p1_check.json()["body"]["product"]["moderation_status"] == "pending"
    assert p1_check.json()["body"]["product"]["request_type"] == "EDIT"
