import io
import wave
from unittest.mock import MagicMock, patch

from app.audio_player import AudioPlayer


def _make_wav_bytes(duration: float = 0.05, sample_rate: int = 44100) -> bytes:
    n_frames = int(sample_rate * duration)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(b"\x00\x00" * n_frames)
    return buf.getvalue()


class TestAudioPlayer:
    @patch("app.audio_player.pyaudio.PyAudio")
    def test_init(self, mock_pyaudio_cls):
        player = AudioPlayer()
        assert not player.is_playing
        mock_pyaudio_cls.assert_called_once()

    @patch("app.audio_player.pyaudio.PyAudio")
    def test_play_starts_playback(self, mock_pyaudio_cls):
        mock_pa = mock_pyaudio_cls.return_value
        mock_stream = MagicMock()
        mock_pa.open.return_value = mock_stream
        mock_pa.get_format_from_width.return_value = 8  # paInt16

        player = AudioPlayer()
        wav_data = _make_wav_bytes()

        player.play(wav_data)
        assert player._thread is not None

        # Wait for playback to finish
        player._thread.join(timeout=5)

    @patch("app.audio_player.pyaudio.PyAudio")
    def test_stop(self, mock_pyaudio_cls):
        player = AudioPlayer()
        player._playing = True

        player.stop()
        assert not player._playing

    @patch("app.audio_player.pyaudio.PyAudio")
    def test_play_calls_on_complete(self, mock_pyaudio_cls):
        mock_pa = mock_pyaudio_cls.return_value
        mock_stream = MagicMock()
        mock_pa.open.return_value = mock_stream
        mock_pa.get_format_from_width.return_value = 8

        player = AudioPlayer()
        wav_data = _make_wav_bytes()

        callback = MagicMock()
        player.play(wav_data, on_complete=callback)
        player._thread.join(timeout=5)
        callback.assert_called_once()

    @patch("app.audio_player.pyaudio.PyAudio")
    def test_cleanup(self, mock_pyaudio_cls):
        mock_pa = mock_pyaudio_cls.return_value
        player = AudioPlayer()
        player.cleanup()
        mock_pa.terminate.assert_called_once()
