import io
import threading
import wave
from collections.abc import Callable

import pyaudio

from app.config import AUDIO_CHUNK_SIZE


class AudioPlayer:
    """Plays WAV audio data using PyAudio."""

    def __init__(self):
        self._audio = pyaudio.PyAudio()
        self._playing = False
        self._thread: threading.Thread | None = None
        self._stream = None

    @property
    def is_playing(self) -> bool:
        return self._playing

    def play(self, wav_data: bytes, on_complete: Callable | None = None):
        """Play WAV audio data in a background thread."""
        if self._playing:
            self.stop()

        self._playing = True
        self._thread = threading.Thread(target=self._play_loop, args=(wav_data, on_complete), daemon=True)
        self._thread.start()

    def stop(self):
        """Stop playback."""
        self._playing = False
        if self._thread:
            self._thread.join(timeout=5)
            self._thread = None

    def _play_loop(self, wav_data: bytes, on_complete: Callable | None = None):
        """Background thread that plays audio."""
        try:
            buffer = io.BytesIO(wav_data)
            with wave.open(buffer, "rb") as wf:
                self._stream = self._audio.open(
                    format=self._audio.get_format_from_width(wf.getsampwidth()),
                    channels=wf.getnchannels(),
                    rate=wf.getframerate(),
                    output=True,
                )

                data = wf.readframes(AUDIO_CHUNK_SIZE)
                while data and self._playing:
                    self._stream.write(data)
                    data = wf.readframes(AUDIO_CHUNK_SIZE)

        except Exception as e:
            print(f"[AudioPlayer] Error: {e}")
        finally:
            if self._stream:
                self._stream.stop_stream()
                self._stream.close()
                self._stream = None
            self._playing = False
            if on_complete:
                on_complete()

    def cleanup(self):
        """Release PyAudio resources."""
        if self._playing:
            self.stop()
        self._audio.terminate()
