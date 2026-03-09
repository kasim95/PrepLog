from unittest.mock import MagicMock, patch

import numpy as np

from app.tasks import _cleanup_temp_file, _send_callback, transcribe_audio


class TestTranscribeAudioTask:
    @patch("app.tasks._cleanup_temp_file")
    @patch("app.tasks._send_callback")
    @patch("app.tasks._get_model")
    @patch("app.tasks._load_wav_as_float32")
    def test_transcribe_success(self, mock_load, mock_model, mock_callback, mock_cleanup):
        mock_load.return_value = np.zeros(16000, dtype=np.float32)
        model = MagicMock()
        model.transcribe.return_value = {"text": "  Hello world  "}
        mock_model.return_value = model

        # Patch update_state on the Celery task instance to avoid Redis dependency
        with patch.object(transcribe_audio, "update_state"):
            result = transcribe_audio.run("/tmp/audio.wav", 1, "http://localhost/callback")

        assert result["status"] == "completed"
        assert result["transcription"] == "Hello world"
        mock_load.assert_called_once_with("/tmp/audio.wav")
        model.transcribe.assert_called_once()
        mock_callback.assert_called_once_with("http://localhost/callback", 1, "Hello world", "completed")
        mock_cleanup.assert_called_once_with("/tmp/audio.wav")

    @patch("app.tasks._cleanup_temp_file")
    @patch("app.tasks._send_callback")
    @patch("app.tasks._get_model")
    @patch("app.tasks._load_wav_as_float32")
    def test_transcribe_failure(self, mock_load, mock_model, mock_callback, mock_cleanup):
        mock_load.side_effect = ValueError("Bad WAV")

        with patch.object(transcribe_audio, "update_state"):
            result = transcribe_audio.run("/tmp/bad.wav", 2, "http://localhost/callback")

        assert result["status"] == "failed"
        assert "Bad WAV" in result["error"]
        mock_callback.assert_called_once()
        assert mock_callback.call_args[0][3] == "failed"
        mock_cleanup.assert_called_once()


class TestSendCallback:
    @patch("app.tasks.httpx.Client")
    def test_send_callback_success(self, mock_client_cls):
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.return_value = MagicMock(status_code=200)
        mock_client_cls.return_value = mock_client

        _send_callback("http://localhost/api/recordings/1/transcription", 1, "text", "completed")
        mock_client.post.assert_called_once()

    @patch("app.tasks.httpx.Client")
    def test_send_callback_handles_exception(self, mock_client_cls):
        mock_client_cls.side_effect = Exception("connection refused")
        # Should not raise
        _send_callback("http://localhost/bad", 1, "text", "completed")


class TestCleanupTempFile:
    @patch("os.remove")
    @patch("os.path.exists", return_value=True)
    def test_cleanup_removes_temp_file(self, mock_exists, mock_remove):
        from app.config import settings

        temp_path = f"{settings.TEMP_AUDIO_DIR}/test.wav"
        _cleanup_temp_file(temp_path)
        mock_remove.assert_called_once_with(temp_path)

    @patch("os.remove")
    @patch("os.path.exists", return_value=True)
    def test_cleanup_ignores_non_temp_files(self, mock_exists, mock_remove):
        _cleanup_temp_file("/some/other/path/audio.wav")
        mock_remove.assert_not_called()
