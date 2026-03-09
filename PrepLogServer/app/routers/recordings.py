import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models import Attempt, Recording
from app.schemas import RecordingResponse, TranscriptionCallback, TranscriptionResponse
from app.services.transcription import request_transcription

router = APIRouter(tags=["recordings"])


@router.get("/api/attempts/{attempt_id}/recordings", response_model=list[RecordingResponse])
async def list_recordings(attempt_id: int, db: AsyncSession = Depends(get_db)):
    attempt = await db.get(Attempt, attempt_id)
    if not attempt:
        raise HTTPException(status_code=404, detail="Attempt not found")
    result = await db.execute(
        select(Recording).where(Recording.attempt_id == attempt_id).order_by(Recording.created_at.desc())
    )
    return result.scalars().all()


@router.post("/api/attempts/{attempt_id}/recordings", response_model=RecordingResponse, status_code=201)
async def upload_recording(
    attempt_id: int,
    audio_file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    attempt = await db.get(Attempt, attempt_id)
    if not attempt:
        raise HTTPException(status_code=404, detail="Attempt not found")

    # Save audio file
    file_ext = Path(audio_file.filename or "recording.wav").suffix or ".wav"
    filename = f"{uuid.uuid4()}{file_ext}"
    file_path = str(Path(settings.RECORDINGS_DIR) / filename)

    content = await audio_file.read()
    with open(file_path, "wb") as f:
        f.write(content)

    # Calculate approximate duration for WAV files
    duration = None
    if file_ext.lower() == ".wav":
        # WAV header: 44 bytes, 16-bit mono 44100Hz
        data_size = len(content) - 44
        if data_size > 0:
            duration = data_size / (44100 * 2 * 1)  # sample_rate * bytes_per_sample * channels

    recording = Recording(
        attempt_id=attempt_id,
        file_path=file_path,
        duration_seconds=duration,
        transcription_status="pending",
    )
    db.add(recording)
    await db.commit()
    await db.refresh(recording)

    # Request transcription in background
    await request_transcription(recording.id, file_path)

    return recording


@router.get("/api/recordings/{recording_id}", response_model=RecordingResponse)
async def get_recording(recording_id: int, db: AsyncSession = Depends(get_db)):
    recording = await db.get(Recording, recording_id)
    if not recording:
        raise HTTPException(status_code=404, detail="Recording not found")
    return recording


@router.get("/api/recordings/{recording_id}/audio")
async def get_audio(recording_id: int, db: AsyncSession = Depends(get_db)):
    recording = await db.get(Recording, recording_id)
    if not recording:
        raise HTTPException(status_code=404, detail="Recording not found")
    if not Path(recording.file_path).exists():
        raise HTTPException(status_code=404, detail="Audio file not found")
    return FileResponse(recording.file_path, media_type="audio/wav")


@router.get("/api/recordings/{recording_id}/transcription", response_model=TranscriptionResponse)
async def get_transcription(recording_id: int, db: AsyncSession = Depends(get_db)):
    recording = await db.get(Recording, recording_id)
    if not recording:
        raise HTTPException(status_code=404, detail="Recording not found")
    return TranscriptionResponse(
        recording_id=recording.id,
        transcription=recording.transcription,
        status=recording.transcription_status,
    )


@router.post("/api/recordings/{recording_id}/retranscribe", response_model=RecordingResponse)
async def retranscribe_recording(recording_id: int, db: AsyncSession = Depends(get_db)):
    """Reset transcription and re-submit for processing."""
    recording = await db.get(Recording, recording_id)
    if not recording:
        raise HTTPException(status_code=404, detail="Recording not found")
    if not Path(recording.file_path).exists():
        raise HTTPException(status_code=404, detail="Audio file not found on disk")

    recording.transcription = None
    recording.transcription_status = "pending"
    await db.commit()
    await db.refresh(recording)

    await request_transcription(recording.id, recording.file_path)
    return recording


@router.post("/api/recordings/{recording_id}/transcription")
async def receive_transcription(
    recording_id: int,
    data: TranscriptionCallback,
    db: AsyncSession = Depends(get_db),
):
    recording = await db.get(Recording, recording_id)
    if not recording:
        raise HTTPException(status_code=404, detail="Recording not found")

    recording.transcription_status = data.status
    if data.status == "completed":
        recording.transcription = data.transcription
    await db.commit()
    return {"status": "ok"}
