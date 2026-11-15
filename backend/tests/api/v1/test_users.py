import pytest


@pytest.mark.anyio
async def test_users_address_management_and_no_leak(client):
    # Register & login
    await client.post(
        "/api/v1/auth/register",
        json={
            "login": "bob_user",
            "password": "Password123!",
            "email": "bob@example.com",
        },
    )
    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"identifier": "bob_user", "password": "Password123!"},
    )
    access_token = login_resp.json()["body"]["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}

    # Profile initially has empty personal fields
    me_resp = await client.get("/api/v1/users/me", headers=headers)
    assert me_resp.status_code == 200
    me_data = me_resp.json()
    assert "password_hash" not in str(me_data)
    assert me_data["body"]["user"]["login"] == "bob_user"

    # Update personal
    patch_resp = await client.patch(
        "/api/v1/users/me/personal",
        headers=headers,
        json={
            "firstname": "Robert",
            "lastname": "Smith",
            "phone_number": "+1234567890",
        },
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["body"]["firstname"] == "Robert"
    assert patch_resp.json()["body"]["phone_number"] == "+1234567890"

    # Add first address (should auto-become default)
    addr1_resp = await client.post(
        "/api/v1/users/me/addresses",
        headers=headers,
        json={"city": "Berlin", "street": "Alexanderplatz 1", "postal_code": "10178"},
    )
    assert addr1_resp.status_code == 201
    addr1 = addr1_resp.json()["body"]
    assert addr1["city"] == "Berlin"
    assert addr1["is_default"] is True
    addr1_id = addr1["id"]

    # Add second address with is_default=True (should unset addr1 default)
    addr2_resp = await client.post(
        "/api/v1/users/me/addresses",
        headers=headers,
        json={
            "city": "Munich",
            "street": "Marienplatz 2",
            "postal_code": "80331",
            "is_default": True,
        },
    )
    assert addr2_resp.status_code == 201
    addr2 = addr2_resp.json()["body"]
    assert addr2["is_default"] is True
    addr2_id = addr2["id"]

    # List addresses
    list_resp = await client.get("/api/v1/users/me/addresses", headers=headers)
    assert list_resp.status_code == 200
    addresses = list_resp.json()["body"]
    assert len(addresses) == 2

    # Switch default back to addr1
    default_resp = await client.patch(
        f"/api/v1/users/me/addresses/{addr1_id}/default",
        headers=headers,
    )
    assert default_resp.status_code == 200
    assert default_resp.json()["body"]["is_default"] is True

    # Delete addr2
    del_resp = await client.delete(
        f"/api/v1/users/me/addresses/{addr2_id}",
        headers=headers,
    )
    assert del_resp.status_code == 200

    # Verify only 1 address remains
    list_after_resp = await client.get("/api/v1/users/me/addresses", headers=headers)
    assert len(list_after_resp.json()["body"]) == 1
    assert list_after_resp.json()["body"][0]["id"] == addr1_id

    # Soft delete account
    del_me_resp = await client.delete("/api/v1/users/me", headers=headers)
    assert del_me_resp.status_code == 200

    # Subsequent access with old token must return 401
    deleted_me_resp = await client.get("/api/v1/users/me", headers=headers)
    assert deleted_me_resp.status_code == 401


@pytest.mark.anyio
async def test_users_address_limit_and_pagination(client):
    # Register & login
    await client.post(
        "/api/v1/auth/register",
        json={
            "login": "limit_user",
            "password": "Password123!",
            "email": "limit@example.com",
        },
    )
    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"identifier": "limit_user", "password": "Password123!"},
    )
    access_token = login_resp.json()["body"]["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}

    # Add 20 addresses (the max limit)
    for i in range(20):
        resp = await client.post(
            "/api/v1/users/me/addresses",
            headers=headers,
            json={
                "city": f"City_{i}",
                "street": f"Street_{i}",
                "postal_code": f"1000{i:02d}",
            },
        )
        assert resp.status_code == 201, f"Address {i} failed: {resp.text}"

    # Attempting to add 21st address must fail with 400 (DomainValidationError)
    overflow_resp = await client.post(
        "/api/v1/users/me/addresses",
        headers=headers,
        json={
            "city": "Overflow City",
            "street": "Overflow Street",
            "postal_code": "99999",
        },
    )
    assert overflow_resp.status_code == 400
    assert "User cannot have more than 20 addresses" in overflow_resp.text

    # Test pagination: limit 5, offset 0 -> 5 items
    paged_resp1 = await client.get(
        "/api/v1/users/me/addresses?limit=5&offset=0",
        headers=headers,
    )
    assert paged_resp1.status_code == 200
    assert len(paged_resp1.json()["body"]) == 5

    # Test pagination: limit 10, offset 15 -> remaining 5 items
    paged_resp2 = await client.get(
        "/api/v1/users/me/addresses?limit=10&offset=15",
        headers=headers,
    )
    assert paged_resp2.status_code == 200
    assert len(paged_resp2.json()["body"]) == 5
