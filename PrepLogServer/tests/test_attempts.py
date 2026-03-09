import pytest


@pytest.mark.asyncio
class TestAttempts:
    async def _create_problem(self, client, title="Test Problem"):
        resp = await client.post("/api/problems", json={"title": title})
        return resp.json()["id"]

    async def test_create_attempt(self, client):
        pid = await self._create_problem(client)
        resp = await client.post(
            f"/api/problems/{pid}/attempts",
            json={"notes": "first try"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["problem_id"] == pid
        assert data["notes"] == "first try"

    async def test_list_attempts(self, client):
        pid = await self._create_problem(client)
        await client.post(f"/api/problems/{pid}/attempts", json={})
        await client.post(f"/api/problems/{pid}/attempts", json={})

        resp = await client.get(f"/api/problems/{pid}/attempts")
        assert resp.status_code == 200
        assert len(resp.json()) == 2

    async def test_list_attempts_problem_not_found(self, client):
        resp = await client.get("/api/problems/9999/attempts")
        assert resp.status_code == 404

    async def test_create_attempt_problem_not_found(self, client):
        resp = await client.post("/api/problems/9999/attempts", json={})
        assert resp.status_code == 404

    async def test_get_attempt(self, client):
        pid = await self._create_problem(client)
        create_resp = await client.post(
            f"/api/problems/{pid}/attempts",
            json={"code_submission": "def two_sum(): pass"},
        )
        attempt_id = create_resp.json()["id"]

        resp = await client.get(f"/api/attempts/{attempt_id}")
        assert resp.status_code == 200
        assert resp.json()["code_submission"] == "def two_sum(): pass"

    async def test_get_attempt_not_found(self, client):
        resp = await client.get("/api/attempts/9999")
        assert resp.status_code == 404

    async def test_update_attempt(self, client):
        pid = await self._create_problem(client)
        create_resp = await client.post(f"/api/problems/{pid}/attempts", json={})
        attempt_id = create_resp.json()["id"]

        resp = await client.put(
            f"/api/attempts/{attempt_id}",
            json={"notes": "updated notes", "code_submission": "return x + y"},
        )
        assert resp.status_code == 200
        assert resp.json()["notes"] == "updated notes"
        assert resp.json()["code_submission"] == "return x + y"

    async def test_update_attempt_not_found(self, client):
        resp = await client.put("/api/attempts/9999", json={"notes": "x"})
        assert resp.status_code == 404

    async def test_delete_attempt(self, client):
        pid = await self._create_problem(client)
        create_resp = await client.post(f"/api/problems/{pid}/attempts", json={})
        attempt_id = create_resp.json()["id"]

        resp = await client.delete(f"/api/attempts/{attempt_id}")
        assert resp.status_code == 204

        resp = await client.get(f"/api/attempts/{attempt_id}")
        assert resp.status_code == 404

    async def test_delete_attempt_not_found(self, client):
        resp = await client.delete("/api/attempts/9999")
        assert resp.status_code == 404
