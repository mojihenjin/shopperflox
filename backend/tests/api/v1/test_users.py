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
