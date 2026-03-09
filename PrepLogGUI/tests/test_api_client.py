from unittest.mock import MagicMock, patch

import pytest
import requests

from app.api_client import APIClient


@pytest.fixture
def client():
    return APIClient(base_url="http://test-server:8000")


class TestAPIClientProblems:
    @patch("app.api_client.requests.get")
    def test_get_problems(self, mock_get, client):
        mock_resp = MagicMock()
        mock_resp.json.return_value = [{"id": 1, "title": "Two Sum"}]
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        result = client.get_problems()
        assert result == [{"id": 1, "title": "Two Sum"}]
        mock_get.assert_called_once_with("http://test-server:8000/api/problems", timeout=10)

    @patch("app.api_client.requests.post")
    def test_create_problem(self, mock_post, client):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"id": 1, "title": "New Problem"}
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        result = client.create_problem({"title": "New Problem"})
        assert result["title"] == "New Problem"
        mock_post.assert_called_once()

    @patch("app.api_client.requests.get")
    def test_get_problems_http_error(self, mock_get, client):
        mock_resp = MagicMock()
        mock_resp.raise_for_status.side_effect = requests.HTTPError("500 Server Error")
        mock_get.return_value = mock_resp

        with pytest.raises(requests.HTTPError):
            client.get_problems()


class TestAPIClientAttempts:
    @patch("app.api_client.requests.get")
    def test_get_attempts(self, mock_get, client):
        mock_resp = MagicMock()
        mock_resp.json.return_value = [{"id": 1, "problem_id": 1}]
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        result = client.get_attempts(problem_id=1)
        assert len(result) == 1
        mock_get.assert_called_once_with("http://test-server:8000/api/problems/1/attempts", timeout=10)

    @patch("app.api_client.requests.post")
    def test_create_attempt(self, mock_post, client):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"id": 1, "problem_id": 1}
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        result = client.create_attempt(1, {"notes": "attempt 1"})
        assert result["problem_id"] == 1

    @patch("app.api_client.requests.post")
    def test_create_attempt_no_data(self, mock_post, client):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"id": 1, "problem_id": 1}
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        client.create_attempt(1)
        # Should send empty dict when data is None
        call_kwargs = mock_post.call_args
        assert call_kwargs.kwargs["json"] == {}

    @patch("app.api_client.requests.put")
    def test_update_attempt(self, mock_put, client):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"id": 1, "notes": "updated"}
        mock_resp.raise_for_status = MagicMock()
        mock_put.return_value = mock_resp

        result = client.update_attempt(1, {"notes": "updated"})
        assert result["notes"] == "updated"

    @patch("app.api_client.requests.delete")
    def test_delete_attempt(self, mock_delete, client):
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_delete.return_value = mock_resp

        client.delete_attempt(1)
        mock_delete.assert_called_once_with("http://test-server:8000/api/attempts/1", timeout=10)


class TestAPIClientRecordings:
    @patch("app.api_client.requests.get")
    def test_get_attempt_recordings(self, mock_get, client):
        mock_resp = MagicMock()
        mock_resp.json.return_value = [{"id": 1, "attempt_id": 1}]
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        result = client.get_attempt_recordings(1)
        assert len(result) == 1
        mock_get.assert_called_once_with("http://test-server:8000/api/attempts/1/recordings", timeout=10)

    @patch("app.api_client.requests.post")
    def test_upload_recording(self, mock_post, client):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"id": 1, "attempt_id": 1}
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        result = client.upload_recording(1, b"fake-wav-data", "test.wav")
        assert result["id"] == 1
        mock_post.assert_called_once()

    @patch("app.api_client.requests.get")
    def test_get_recording(self, mock_get, client):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"id": 5, "transcription_status": "pending"}
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        result = client.get_recording(5)
        assert result["id"] == 5

    @patch("app.api_client.requests.get")
    def test_download_audio(self, mock_get, client):
        mock_resp = MagicMock()
        mock_resp.content = b"wav-file-bytes"
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        result = client.download_audio(1)
        assert result == b"wav-file-bytes"

    @patch("app.api_client.requests.get")
    def test_get_transcription(self, mock_get, client):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"recording_id": 1, "status": "completed", "transcription": "hello"}
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        result = client.get_transcription(1)
        assert result["status"] == "completed"
        assert result["transcription"] == "hello"
