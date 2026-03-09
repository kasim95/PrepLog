import io
import wave
from unittest.mock import MagicMock, patch

from app.audio_recorder import AudioRecorder


class TestAudioRecorder:
    @patch("app.audio_recorder.pyaudio.PyAudio")
    def test_init(self, mock_pyaudio_cls):
        recorder = AudioRecorder()
        assert not recorder.is_recording
        mock_pyaudio_cls.assert_called_once()

    @patch("app.audio_recorder.pyaudio.PyAudio")
    def test_start_sets_recording_flag(self, mock_pyaudio_cls):
        recorder = AudioRecorder()
        # Mock the stream to avoid real audio
        mock_pa = mock_pyaudio_cls.return_value
        mock_stream = MagicMock()
        mock_stream.read.return_value = b"\x00" * 2048
        mock_pa.open.return_value = mock_stream

        recorder.start()
        assert recorder.is_recording

        # Cleanup
        recorder._recording = False
        if recorder._thread:
            recorder._thread.join(timeout=2)

    @patch("app.audio_recorder.pyaudio.PyAudio")
    def test_stop_returns_wav_bytes(self, mock_pyaudio_cls):
        recorder = AudioRecorder()
        # Simulate some recorded frames
        recorder._frames = [b"\x00\x00" * 1024, b"\x00\x00" * 1024]

        wav_data = recorder.stop()
        assert isinstance(wav_data, bytes)
        assert len(wav_data) > 44  # WAV header is 44 bytes

        # Validate it's a proper WAV
        buf = io.BytesIO(wav_data)
        with wave.open(buf, "rb") as wf:
            assert wf.getnchannels() == 1
            assert wf.getsampwidth() == 2

    @patch("app.audio_recorder.pyaudio.PyAudio")
    def test_stop_without_start(self, mock_pyaudio_cls):
        recorder = AudioRecorder()
        wav_data = recorder.stop()
        # Should return valid empty WAV
        assert isinstance(wav_data, bytes)

    @patch("app.audio_recorder.pyaudio.PyAudio")
    def test_double_start_ignored(self, mock_pyaudio_cls):
        recorder = AudioRecorder()
        mock_pa = mock_pyaudio_cls.return_value
        mock_stream = MagicMock()
        mock_stream.read.return_value = b"\x00" * 2048
        mock_pa.open.return_value = mock_stream

        recorder.start()
        first_thread = recorder._thread

        recorder.start()  # Should be a no-op
        assert recorder._thread is first_thread

        recorder._recording = False
        if recorder._thread:
            recorder._thread.join(timeout=2)
