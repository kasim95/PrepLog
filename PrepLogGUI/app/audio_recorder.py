import io
import threading
import wave

import pyaudio

from app.config import AUDIO_CHANNELS, AUDIO_CHUNK_SIZE, AUDIO_FORMAT_WIDTH, AUDIO_SAMPLE_RATE


class AudioRecorder:
    """Records audio from the microphone using PyAudio with pause/resume support."""

    def __init__(self):
        self._audio = pyaudio.PyAudio()
        self._stream = None
        self._frames: list[bytes] = []
        self._recording = False
        self._paused = False
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()

    @property
    def is_recording(self) -> bool:
        return self._recording

    @property
    def is_paused(self) -> bool:
        return self._paused

    def start(self):
        """Start recording audio in a background thread."""
        if self._recording:
            return

        self._frames = []
        self._recording = True
        self._paused = False
        self._thread = threading.Thread(target=self._record_loop, daemon=True)
        self._thread.start()

    def pause(self):
        """Pause recording (keeps stream open, stops capturing frames)."""
        if self._recording and not self._paused:
            self._paused = True

    def resume(self):
        """Resume recording after pause."""
        if self._recording and self._paused:
            self._paused = False

    def stop(self) -> bytes:
        """Stop recording and return WAV data as bytes."""
        self._recording = False
        self._paused = False
        if self._thread:
            self._thread.join(timeout=5)
            self._thread = None

        return self._build_wav()

    def _record_loop(self):
        """Background thread that captures audio frames."""
        try:
            self._stream = self._audio.open(
                format=pyaudio.paInt16,
                channels=AUDIO_CHANNELS,
                rate=AUDIO_SAMPLE_RATE,
                input=True,
                frames_per_buffer=AUDIO_CHUNK_SIZE,
            )
            while self._recording:
                data = self._stream.read(AUDIO_CHUNK_SIZE, exception_on_overflow=False)
                if not self._paused:
                    with self._lock:
                        self._frames.append(data)
        except Exception as e:
            print(f"[AudioRecorder] Error: {e}")
            self._recording = False
        finally:
            if self._stream:
                self._stream.stop_stream()
                self._stream.close()
                self._stream = None

    def _build_wav(self) -> bytes:
        """Build a WAV file from recorded frames."""
        buffer = io.BytesIO()
        with wave.open(buffer, "wb") as wf:
            wf.setnchannels(AUDIO_CHANNELS)
            wf.setsampwidth(AUDIO_FORMAT_WIDTH)
            wf.setframerate(AUDIO_SAMPLE_RATE)
            with self._lock:
                wf.writeframes(b"".join(self._frames))
        return buffer.getvalue()

    def cleanup(self):
        """Release PyAudio resources."""
        if self._recording:
            self.stop()
        self._audio.terminate()
