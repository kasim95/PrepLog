import uuid
from pathlib import Path

from fastapi import APIRouter, File, Form, UploadFile

from app.celery_app import celery_app
from app.config import settings
from app.schemas import TaskStatusResponse, TranscribeResponse
from app.tasks import transcribe_audio

router = APIRouter(prefix="/api", tags=["transcription"])


@router.post("/transcribe", response_model=TranscribeResponse)
async def submit_transcription(
    audio_file: UploadFile = File(...),
    recording_id: int = Form(...),
    callback_url: str = Form(...),
):
    """Accept an audio file and queue it for transcription."""
    # Save audio to temp directory
    file_ext = Path(audio_file.filename or "audio.wav").suffix or ".wav"
    temp_filename = f"{uuid.uuid4()}{file_ext}"
    temp_path = str(Path(settings.TEMP_AUDIO_DIR) / temp_filename)

    content = await audio_file.read()
    with open(temp_path, "wb") as f:
        f.write(content)

    # Queue Celery task
    task = transcribe_audio.delay(
        audio_file_path=temp_path,
        recording_id=recording_id,
        callback_url=callback_url,
    )

    return TranscribeResponse(task_id=task.id, status="queued")


@router.get("/tasks/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(task_id: str):
    """Check the status of a transcription task."""
    result = celery_app.AsyncResult(task_id)

    status_map = {
        "PENDING": "pending",
        "STARTED": "processing",
        "PROCESSING": "processing",
        "SUCCESS": "completed",
        "FAILURE": "failed",
    }

    status = status_map.get(result.state, result.state.lower())
    transcription = None

    if result.ready() and result.successful():
        task_result = result.result
        if isinstance(task_result, dict):
            transcription = task_result.get("transcription")

    return TaskStatusResponse(task_id=task_id, status=status, result=transcription)
