import pytest
import httpx

@pytest.mark.asyncio
async def test_full_integration():
    base_url = "http://localhost:8000"

    async with httpx.AsyncClient(base_url=base_url) as client:

        # 1. Register new user
        register_payload = {
            "username": "test_user",
            "email": "test_user@example.com",
            "password": "testpassword"
        }
        r = await client.post("/api/register", json=register_payload)
        assert r.status_code == 201, f"Register не прошёл: {r.text}"
        user = r.json()
        assert "id" in user

        # 2. User login
        login_payload = {
            "username": "test_user",
            "password": "testpassword"
        }
        r = await client.post("/api/login", data=login_payload)
        assert r.status_code == 200, f"Login не прошёл: {r.text}"
        token_data = r.json()
        jwt_token = token_data["access_token"]
        print(jwt_token)
        jwt_headers = {"Authorization": f"Bearer {jwt_token}"}

        # 3. Get user profile
        r = await client.get("/api/me", headers=jwt_headers)
        assert r.status_code == 200, f"GET /api/me не прошёл: {r.text}"
        me = r.json()
        assert me["username"] == "test_user"

        # 4. Create vault using JWT
        vault_payload = {"name": "My Test Vault"}
        r = await client.post("/api/vaults", json=vault_payload, headers=jwt_headers)
        assert r.status_code == 201, f"Создание Vault не прошло: {r.text}"
        vault = r.json()
        vault_id = vault["id"]
        vault_token = vault["token"]
        assert vault_token.startswith("vault_")
        vault_headers = {"Authorization": f"Bearer {vault_token}"}

        # 5. Get vault data
        r = await client.get(f"/api/vaults/{vault_id}", headers=jwt_headers)
        assert r.status_code == 200, f"Получение Vault не прошло: {r.text}"
        vault_details = r.json()
        assert vault_details["name"] == "My Test Vault"

        # 6. Update vault
        update_payload = {"name": "Updated Vault"}
        r = await client.put(f"/api/vaults/{vault_id}", json=update_payload, headers=jwt_headers)
        assert r.status_code == 200, f"Обновление Vault не прошло: {r.text}"
        updated_vault = r.json()
        assert updated_vault["name"] == "Updated Vault"

        # 7. Create note in vault
        note_payload = {
            "external_id": "ext_001",
            "title": "Integration Test Note",
            "content": "This is the content of the integration test note."
        }
        r = await client.post("/api/notes", json=note_payload, headers=vault_headers)
        assert r.status_code == 201, f"Создание заметки не прошло: {r.text}"
        note = r.json()
        note_id = note["id"]
        assert note["state"] == "PENDING"

        # 8. Get pending notes
        r = await client.get("/api/notes?state=PENDING&limit=10&offset=0", headers=vault_headers)
        assert r.status_code == 200, f"Список заметок не получен: {r.text}"
        pending_notes = r.json()
        assert any(n["id"] == note_id for n in pending_notes), "Заметка не найдена среди PENDING"

        # 9. Claim note
        claim_payload = {"client_id": "integration_client_1"}
        r = await client.post(f"/api/notes/{note_id}/claim", json=claim_payload, headers=vault_headers)
        assert r.status_code == 200, f"Claim заметки не прошёл: {r.text}"
        claimed_note = r.json()
        assert claimed_note["state"] == "CLAIMED"
        assert claimed_note["claim_owner"] == "integration_client_1"

        # 10. Download note
        r = await client.get(f"/api/notes/{note_id}/download", headers=vault_headers)
        assert r.status_code == 200, f"Download заметки не прошёл: {r.text}"
        downloaded_note = r.json()
        assert downloaded_note["id"] == note_id
        assert downloaded_note["content"] == "This is the content of the integration test note."

        # 11. Confirm downloading
        r = await client.post(f"/api/notes/{note_id}/confirm", headers=vault_headers)
        assert r.status_code == 200, f"Confirm заметки не прошёл: {r.text}"
        confirmed_note = r.json()
        assert confirmed_note["state"] == "DELIVERED"

        # 12. Note is no longer pending
        r = await client.get("/api/notes?state=PENDING&limit=10&offset=0", headers=vault_headers)
        assert r.status_code == 200, f"Запрос PENDING заметок не прошёл: {r.text}"
        pending_after = r.json()
        assert not any(n["id"] == note_id for n in pending_after), "Заметка всё ещё находится в списке PENDING"

        # 13. Remove vault with everything it contains
        r = await client.delete(f"/api/vaults/{vault_id}", headers=jwt_headers)
        assert r.status_code == 204, f"Удаление Vault не прошло: {r.text}"
