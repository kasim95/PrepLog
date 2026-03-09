import io
import wave

import numpy as np

from app.tasks import WHISPER_SAMPLE_RATE, _load_wav_as_float32


def _make_wav(sample_rate: int = 44100, channels: int = 1, sampwidth: int = 2, duration: float = 0.1) -> str:
    """Create a temporary WAV file and return its path."""
    import tempfile

    n_frames = int(sample_rate * duration)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(sampwidth)
        wf.setframerate(sample_rate)
        if sampwidth == 2:
            data = np.zeros(n_frames * channels, dtype=np.int16).tobytes()
        elif sampwidth == 4:
            data = np.zeros(n_frames * channels, dtype=np.int32).tobytes()
        elif sampwidth == 1:
            data = np.full(n_frames * channels, 128, dtype=np.uint8).tobytes()
        else:
            raise ValueError(f"Unsupported sampwidth: {sampwidth}")
        wf.writeframes(data)

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp.write(buf.getvalue())
        tmp.flush()
        return tmp.name


class TestLoadWavAsFloat32:
    def test_16bit_mono_44100(self):
        path = _make_wav(sample_rate=44100, channels=1, sampwidth=2, duration=0.5)
        audio = _load_wav_as_float32(path)
        assert audio.dtype == np.float32
        # Should be resampled to 16kHz
        expected_len = int(0.5 * WHISPER_SAMPLE_RATE)
        assert abs(len(audio) - expected_len) <= 1

    def test_16bit_stereo(self):
        path = _make_wav(sample_rate=44100, channels=2, sampwidth=2, duration=0.5)
        audio = _load_wav_as_float32(path)
        assert audio.dtype == np.float32
        expected_len = int(0.5 * WHISPER_SAMPLE_RATE)
        assert abs(len(audio) - expected_len) <= 1

    def test_8bit_mono(self):
        path = _make_wav(sample_rate=16000, channels=1, sampwidth=1, duration=0.5)
        audio = _load_wav_as_float32(path)
        assert audio.dtype == np.float32
        expected_len = int(0.5 * WHISPER_SAMPLE_RATE)
        assert abs(len(audio) - expected_len) <= 1

    def test_32bit_mono(self):
        path = _make_wav(sample_rate=16000, channels=1, sampwidth=4, duration=0.5)
        audio = _load_wav_as_float32(path)
        assert audio.dtype == np.float32
        expected_len = int(0.5 * WHISPER_SAMPLE_RATE)
        assert abs(len(audio) - expected_len) <= 1

    def test_already_16khz_no_resample(self):
        path = _make_wav(sample_rate=16000, channels=1, sampwidth=2, duration=0.5)
        audio = _load_wav_as_float32(path)
        expected_len = int(0.5 * 16000)
        assert len(audio) == expected_len

    def test_values_in_range(self):
        path = _make_wav(sample_rate=44100, channels=1, sampwidth=2, duration=0.1)
        audio = _load_wav_as_float32(path)
        assert np.all(audio >= -1.0)
        assert np.all(audio <= 1.0)
