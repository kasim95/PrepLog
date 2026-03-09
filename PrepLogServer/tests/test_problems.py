import pytest


@pytest.mark.asyncio
class TestProblems:
    async def test_list_problems_empty(self, client):
        resp = await client.get("/api/problems")
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_create_problem(self, client):
        payload = {"title": "Two Sum", "difficulty": "Easy", "source": "leetcode"}
        resp = await client.post("/api/problems", json=payload)
        assert resp.status_code == 201
        data = resp.json()
        assert data["title"] == "Two Sum"
        assert data["difficulty"] == "Easy"
        assert data["source"] == "leetcode"
        assert data["id"] is not None

    async def test_list_problems_after_create(self, client):
        await client.post("/api/problems", json={"title": "P1"})
        await client.post("/api/problems", json={"title": "P2"})

        resp = await client.get("/api/problems")
        assert resp.status_code == 200
        problems = resp.json()
        assert len(problems) == 2

    async def test_get_problem(self, client):
        create_resp = await client.post("/api/problems", json={"title": "Binary Search"})
        problem_id = create_resp.json()["id"]

        resp = await client.get(f"/api/problems/{problem_id}")
        assert resp.status_code == 200
        assert resp.json()["title"] == "Binary Search"

    async def test_get_problem_not_found(self, client):
        resp = await client.get("/api/problems/9999")
        assert resp.status_code == 404

    async def test_update_problem(self, client):
        create_resp = await client.post(
            "/api/problems", json={"title": "Old Title", "difficulty": "Easy"}
        )
        problem_id = create_resp.json()["id"]

        resp = await client.put(
            f"/api/problems/{problem_id}",
            json={"title": "New Title", "difficulty": "Hard"},
        )
        assert resp.status_code == 200
        assert resp.json()["title"] == "New Title"
        assert resp.json()["difficulty"] == "Hard"

    async def test_update_problem_partial(self, client):
        create_resp = await client.post(
            "/api/problems", json={"title": "Title", "difficulty": "Easy"}
        )
        problem_id = create_resp.json()["id"]

        resp = await client.put(f"/api/problems/{problem_id}", json={"difficulty": "Medium"})
        assert resp.status_code == 200
        assert resp.json()["title"] == "Title"
        assert resp.json()["difficulty"] == "Medium"

    async def test_update_problem_not_found(self, client):
        resp = await client.put("/api/problems/9999", json={"title": "X"})
        assert resp.status_code == 404

    async def test_delete_problem(self, client):
        create_resp = await client.post("/api/problems", json={"title": "Delete Me"})
        problem_id = create_resp.json()["id"]

        resp = await client.delete(f"/api/problems/{problem_id}")
        assert resp.status_code == 204

        resp = await client.get(f"/api/problems/{problem_id}")
        assert resp.status_code == 404

    async def test_delete_problem_not_found(self, client):
        resp = await client.delete("/api/problems/9999")
        assert resp.status_code == 404

    async def test_create_problem_with_all_fields(self, client):
        payload = {
            "title": "LRU Cache",
            "description": "Design an LRU cache.",
            "difficulty": "Medium",
            "source": "leetcode",
            "leetcode_slug": "lru-cache",
        }
        resp = await client.post("/api/problems", json=payload)
        assert resp.status_code == 201
        data = resp.json()
        assert data["description"] == "Design an LRU cache."
        assert data["leetcode_slug"] == "lru-cache"
