from typing import Any

import requests

from app.config import SERVER_URL


class APIClient:
    """HTTP client for communicating with PrepLogServer."""

    def __init__(self, base_url: str = SERVER_URL):
        self.base_url = base_url.rstrip("/")

    def _url(self, path: str) -> str:
        return f"{self.base_url}{path}"

    # ── Problems ─────────────────────────────────────────────────────

    def get_problems(self) -> list[dict[str, Any]]:
        resp = requests.get(self._url("/api/problems"), timeout=10)
        resp.raise_for_status()
        return resp.json()

    def create_problem(self, data: dict[str, Any]) -> dict[str, Any]:
        resp = requests.post(self._url("/api/problems"), json=data, timeout=10)
        resp.raise_for_status()
        return resp.json()

    # ── Attempts ─────────────────────────────────────────────────────

    def get_attempts(self, problem_id: int) -> list[dict[str, Any]]:
        resp = requests.get(self._url(f"/api/problems/{problem_id}/attempts"), timeout=10)
        resp.raise_for_status()
        return resp.json()

    def create_attempt(self, problem_id: int, data: dict[str, Any] | None = None) -> dict[str, Any]:
        resp = requests.post(
            self._url(f"/api/problems/{problem_id}/attempts"),
            json=data or {},
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json()

    def update_attempt(self, attempt_id: int, data: dict[str, Any]) -> dict[str, Any]:
        resp = requests.put(self._url(f"/api/attempts/{attempt_id}"), json=data, timeout=10)
        resp.raise_for_status()
        return resp.json()

    def delete_attempt(self, attempt_id: int) -> None:
        resp = requests.delete(self._url(f"/api/attempts/{attempt_id}"), timeout=10)
        resp.raise_for_status()

    # ── Recordings ───────────────────────────────────────────────────

    def get_attempt_recordings(self, attempt_id: int) -> list[dict[str, Any]]:
        resp = requests.get(self._url(f"/api/attempts/{attempt_id}/recordings"), timeout=10)
        resp.raise_for_status()
        return resp.json()

    def upload_recording(self, attempt_id: int, audio_data: bytes, filename: str = "recording.wav") -> dict[str, Any]:
        resp = requests.post(
            self._url(f"/api/attempts/{attempt_id}/recordings"),
            files={"audio_file": (filename, audio_data, "audio/wav")},
            timeout=60,
        )
        resp.raise_for_status()
        return resp.json()

    def get_recording(self, recording_id: int) -> dict[str, Any]:
        resp = requests.get(self._url(f"/api/recordings/{recording_id}"), timeout=10)
        resp.raise_for_status()
        return resp.json()

    def download_audio(self, recording_id: int) -> bytes:
        resp = requests.get(self._url(f"/api/recordings/{recording_id}/audio"), timeout=30)
        resp.raise_for_status()
        return resp.content

    def get_transcription(self, recording_id: int) -> dict[str, Any]:
        resp = requests.get(self._url(f"/api/recordings/{recording_id}/transcription"), timeout=10)
        resp.raise_for_status()
        return resp.json()

    def retranscribe_recording(self, recording_id: int) -> dict[str, Any]:
        resp = requests.post(self._url(f"/api/recordings/{recording_id}/retranscribe"), timeout=30)
        resp.raise_for_status()
        return resp.json()
