import os
import traceback
import wave

import httpx
import numpy as np
import whisper

from app.celery_app import celery_app
from app.config import settings

# Cache the Whisper model at module level (loaded once per worker)
_whisper_model = None

# Whisper expects 16kHz mono float32 audio
WHISPER_SAMPLE_RATE = 16000


def _get_model():
    global _whisper_model
    if _whisper_model is None:
        print(f"[Whisper] Loading model: {settings.WHISPER_MODEL}")
        _whisper_model = whisper.load_model(settings.WHISPER_MODEL)
        print("[Whisper] Model loaded successfully")
    return _whisper_model


def _load_wav_as_float32(file_path: str) -> np.ndarray:
    """Load a WAV file as a float32 numpy array at 16kHz mono, bypassing ffmpeg."""
    with wave.open(file_path, "rb") as wf:
        n_channels = wf.getnchannels()
        sampwidth = wf.getsampwidth()
        framerate = wf.getframerate()
        n_frames = wf.getnframes()
        raw = wf.readframes(n_frames)

    # Convert raw bytes to numpy based on sample width
    if sampwidth == 2:
        audio = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
    elif sampwidth == 4:
        audio = np.frombuffer(raw, dtype=np.int32).astype(np.float32) / 2147483648.0
    elif sampwidth == 1:
        audio = (np.frombuffer(raw, dtype=np.uint8).astype(np.float32) - 128.0) / 128.0
    else:
        raise ValueError(f"Unsupported sample width: {sampwidth}")

    # Convert stereo to mono by averaging channels
    if n_channels > 1:
        audio = audio.reshape(-1, n_channels).mean(axis=1)

    # Resample to 16kHz if needed
    if framerate != WHISPER_SAMPLE_RATE:
        duration = len(audio) / framerate
        target_len = int(duration * WHISPER_SAMPLE_RATE)
        audio = np.interp(
            np.linspace(0, len(audio), target_len, endpoint=False),
            np.arange(len(audio)),
            audio,
        ).astype(np.float32)

    return audio


@celery_app.task(bind=True, name="app.tasks.transcribe_audio")
def transcribe_audio(self, audio_file_path: str, recording_id: int, callback_url: str):
    """Transcribe an audio file using OpenAI Whisper and POST the result to callback_url."""
    self.update_state(state="PROCESSING")

    try:
        model = _get_model()
        print(f"[Whisper] Transcribing: {audio_file_path}")

        # Load WAV directly as numpy array to avoid ffmpeg dependency
        audio_array = _load_wav_as_float32(audio_file_path)
        result = model.transcribe(audio_array)
        transcription_text = result["text"].strip()
        print(f"[Whisper] Transcription complete: {len(transcription_text)} chars")

        # Send result to PrepLogServer
        _send_callback(callback_url, recording_id, transcription_text, "completed")

        # Clean up temp file
        _cleanup_temp_file(audio_file_path)

        return {"status": "completed", "transcription": transcription_text}

    except Exception as e:
        error_msg = f"Transcription failed: {e!s}"
        print(f"[Whisper] Error: {error_msg}")
        traceback.print_exc()

        # Notify server of failure
        _send_callback(callback_url, recording_id, error_msg, "failed")

        # Clean up temp file
        _cleanup_temp_file(audio_file_path)

        return {"status": "failed", "error": error_msg}


def _send_callback(callback_url: str, recording_id: int, transcription: str, status: str):
    """Send transcription result back to PrepLogServer."""
    try:
        with httpx.Client(timeout=settings.CALLBACK_TIMEOUT) as client:
            response = client.post(
                callback_url,
                json={
                    "recording_id": recording_id,
                    "transcription": transcription,
                    "status": status,
                },
            )
            print(f"[Callback] Status {response.status_code} for recording {recording_id}")
    except Exception as e:
        print(f"[Callback] Error sending callback: {e}")


def _cleanup_temp_file(file_path: str):
    """Remove temporary audio file if it's in the temp directory."""
    try:
        if settings.TEMP_AUDIO_DIR in file_path and os.path.exists(file_path):
            os.remove(file_path)
            print(f"[Cleanup] Removed temp file: {file_path}")
    except Exception as e:
        print(f"[Cleanup] Error removing temp file: {e}")
