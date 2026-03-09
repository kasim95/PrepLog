import httpx

from app.config import settings


async def request_transcription(recording_id: int, audio_file_path: str) -> dict | None:
    """Send an audio file to the TranscriptionService for background processing."""
    callback_url = f"{settings.CALLBACK_BASE_URL}/api/recordings/{recording_id}/transcription"
    url = f"{settings.TRANSCRIPTION_SERVICE_URL}/api/transcribe"

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            with open(audio_file_path, "rb") as f:
                response = await client.post(
                    url,
                    files={"audio_file": ("recording.wav", f, "audio/wav")},
                    data={
                        "recording_id": str(recording_id),
                        "callback_url": callback_url,
                    },
                )
            if response.status_code == 200:
                return response.json()
    except Exception as e:
        print(f"[TranscriptionClient] Error requesting transcription: {e}")
    return None
