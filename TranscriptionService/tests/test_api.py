import io
import wave
from unittest.mock import MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
def mock_celery_task():
    """Mock the celery task delay method."""
    mock_result = MagicMock()
    mock_result.id = "test-task-id-123"
    with patch("app.routers.transcribe.transcribe_audio") as mock_task:
        mock_task.delay.return_value = mock_result
        yield mock_task


def _make_wav_bytes(duration: float = 0.1, sample_rate: int = 44100) -> bytes:
    buf = io.BytesIO()
    n_frames = int(sample_rate * duration)
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(b"\x00\x00" * n_frames)
    return buf.getvalue()


@pytest.mark.asyncio
class TestTranscribeEndpoint:
    async def test_submit_transcription(self, mock_celery_task, tmp_path):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            wav = _make_wav_bytes()
            resp = await client.post(
                "/api/transcribe",
                files={"audio_file": ("test.wav", wav, "audio/wav")},
                data={"recording_id": "1", "callback_url": "http://localhost/callback"},
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["task_id"] == "test-task-id-123"
        assert data["status"] == "queued"
        mock_celery_task.delay.assert_called_once()


@pytest.mark.asyncio
class TestTaskStatusEndpoint:
    async def test_get_task_pending(self):
        mock_result = MagicMock()
        mock_result.state = "PENDING"
        mock_result.ready.return_value = False

        with patch("app.routers.transcribe.celery_app") as mock_app:
            mock_app.AsyncResult.return_value = mock_result
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/api/tasks/some-task-id")

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "pending"
        assert data["result"] is None

    async def test_get_task_completed(self):
        mock_result = MagicMock()
        mock_result.state = "SUCCESS"
        mock_result.ready.return_value = True
        mock_result.successful.return_value = True
        mock_result.result = {"transcription": "Hello world"}

        with patch("app.routers.transcribe.celery_app") as mock_app:
            mock_app.AsyncResult.return_value = mock_result
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/api/tasks/some-task-id")

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "completed"
        assert data["result"] == "Hello world"


@pytest.mark.asyncio
class TestHealthEndpoint:
    async def test_health(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"
