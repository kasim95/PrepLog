from unittest.mock import AsyncMock, patch

import pytest

from tests.conftest import make_wav_bytes


@pytest.mark.asyncio
class TestRecordings:
    async def _create_attempt(self, client):
        """Helper: create a problem and an attempt, returning (problem_id, attempt_id)."""
        p_resp = await client.post("/api/problems", json={"title": "TestP"})
        pid = p_resp.json()["id"]
        a_resp = await client.post(f"/api/problems/{pid}/attempts", json={})
        aid = a_resp.json()["id"]
        return pid, aid

    @patch("app.routers.recordings.request_transcription", new_callable=AsyncMock)
    async def test_upload_recording(self, mock_transcribe, client, tmp_path):
        mock_transcribe.return_value = {"task_id": "fake-task"}
        _, aid = await self._create_attempt(client)

        wav = make_wav_bytes()
        resp = await client.post(
            f"/api/attempts/{aid}/recordings",
            files={"audio_file": ("test.wav", wav, "audio/wav")},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["attempt_id"] == aid
        assert data["transcription_status"] == "pending"
        mock_transcribe.assert_awaited_once()

    @patch("app.routers.recordings.request_transcription", new_callable=AsyncMock)
    async def test_upload_recording_attempt_not_found(self, mock_transcribe, client):
        wav = make_wav_bytes()
        resp = await client.post(
            "/api/attempts/9999/recordings",
            files={"audio_file": ("test.wav", wav, "audio/wav")},
        )
        assert resp.status_code == 404
        mock_transcribe.assert_not_awaited()

    @patch("app.routers.recordings.request_transcription", new_callable=AsyncMock)
    async def test_list_recordings(self, mock_transcribe, client):
        mock_transcribe.return_value = None
        _, aid = await self._create_attempt(client)

        wav = make_wav_bytes()
        await client.post(
            f"/api/attempts/{aid}/recordings",
            files={"audio_file": ("r1.wav", wav, "audio/wav")},
        )
        await client.post(
            f"/api/attempts/{aid}/recordings",
            files={"audio_file": ("r2.wav", wav, "audio/wav")},
        )

        resp = await client.get(f"/api/attempts/{aid}/recordings")
        assert resp.status_code == 200
        assert len(resp.json()) == 2

    async def test_list_recordings_attempt_not_found(self, client):
        resp = await client.get("/api/attempts/9999/recordings")
        assert resp.status_code == 404

    @patch("app.routers.recordings.request_transcription", new_callable=AsyncMock)
    async def test_get_recording(self, mock_transcribe, client):
        mock_transcribe.return_value = None
        _, aid = await self._create_attempt(client)

        wav = make_wav_bytes()
        upload_resp = await client.post(
            f"/api/attempts/{aid}/recordings",
            files={"audio_file": ("test.wav", wav, "audio/wav")},
        )
        rid = upload_resp.json()["id"]

        resp = await client.get(f"/api/recordings/{rid}")
        assert resp.status_code == 200
        assert resp.json()["id"] == rid

    async def test_get_recording_not_found(self, client):
        resp = await client.get("/api/recordings/9999")
        assert resp.status_code == 404

    @patch("app.routers.recordings.request_transcription", new_callable=AsyncMock)
    async def test_get_transcription(self, mock_transcribe, client):
        mock_transcribe.return_value = None
        _, aid = await self._create_attempt(client)

        wav = make_wav_bytes()
        upload_resp = await client.post(
            f"/api/attempts/{aid}/recordings",
            files={"audio_file": ("test.wav", wav, "audio/wav")},
        )
        rid = upload_resp.json()["id"]

        resp = await client.get(f"/api/recordings/{rid}/transcription")
        assert resp.status_code == 200
        data = resp.json()
        assert data["recording_id"] == rid
        assert data["status"] == "pending"

    async def test_get_transcription_not_found(self, client):
        resp = await client.get("/api/recordings/9999/transcription")
        assert resp.status_code == 404

    @patch("app.routers.recordings.request_transcription", new_callable=AsyncMock)
    async def test_receive_transcription_callback(self, mock_transcribe, client):
        mock_transcribe.return_value = None
        _, aid = await self._create_attempt(client)

        wav = make_wav_bytes()
        upload_resp = await client.post(
            f"/api/attempts/{aid}/recordings",
            files={"audio_file": ("test.wav", wav, "audio/wav")},
        )
        rid = upload_resp.json()["id"]

        callback_payload = {
            "recording_id": rid,
            "transcription": "Hello world, this is a test.",
            "status": "completed",
        }
        resp = await client.post(
            f"/api/recordings/{rid}/transcription", json=callback_payload
        )
        assert resp.status_code == 200

        # Verify transcription was stored
        resp = await client.get(f"/api/recordings/{rid}/transcription")
        data = resp.json()
        assert data["status"] == "completed"
        assert data["transcription"] == "Hello world, this is a test."

    async def test_receive_transcription_recording_not_found(self, client):
        resp = await client.post(
            "/api/recordings/9999/transcription",
            json={"recording_id": 9999, "transcription": "x", "status": "completed"},
        )
        assert resp.status_code == 404
