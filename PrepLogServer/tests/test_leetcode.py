import pytest


@pytest.mark.asyncio
class TestLeetCode:
    async def test_track_leetcode_problem_create(self, client):
        payload = {
            "title": "Two Sum",
            "description": "Given an array ...",
            "difficulty": "Easy",
            "leetcode_slug": "two-sum",
        }
        resp = await client.post("/api/leetcode/problem", json=payload)
        assert resp.status_code == 201
        data = resp.json()
        assert data["title"] == "Two Sum"
        assert data["source"] == "leetcode"
        assert data["leetcode_slug"] == "two-sum"

    async def test_track_leetcode_problem_update_existing(self, client):
        payload = {
            "title": "Two Sum",
            "difficulty": "Easy",
            "leetcode_slug": "two-sum",
        }
        await client.post("/api/leetcode/problem", json=payload)

        updated = {
            "title": "Two Sum (Updated)",
            "difficulty": "Medium",
            "description": "new desc",
            "leetcode_slug": "two-sum",
        }
        resp = await client.post("/api/leetcode/problem", json=updated)
        assert resp.status_code == 201
        data = resp.json()
        assert data["title"] == "Two Sum (Updated)"
        assert data["difficulty"] == "Medium"
        assert data["description"] == "new desc"

    async def test_track_submission(self, client):
        # First track the problem
        await client.post(
            "/api/leetcode/problem",
            json={"title": "Two Sum", "leetcode_slug": "two-sum"},
        )

        # Submit code
        resp = await client.post(
            "/api/leetcode/submission",
            json={
                "leetcode_slug": "two-sum",
                "code": "class Solution:\n    def twoSum(self): pass",
                "language": "python3",
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["code_submission"] == "class Solution:\n    def twoSum(self): pass"
        assert "python3" in data["notes"].lower()

    async def test_submission_problem_not_found(self, client):
        resp = await client.post(
            "/api/leetcode/submission",
            json={"leetcode_slug": "nonexistent", "code": "x = 1"},
        )
        assert resp.status_code == 404

    async def test_submission_without_language(self, client):
        await client.post(
            "/api/leetcode/problem",
            json={"title": "Add Two Numbers", "leetcode_slug": "add-two-numbers"},
        )
        resp = await client.post(
            "/api/leetcode/submission",
            json={"leetcode_slug": "add-two-numbers", "code": "print('hello')"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["notes"] is None
