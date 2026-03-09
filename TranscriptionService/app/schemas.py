from pydantic import BaseModel


class TranscribeRequest(BaseModel):
    recording_id: int
    callback_url: str


class TranscribeResponse(BaseModel):
    task_id: str
    status: str = "queued"


class TaskStatusResponse(BaseModel):
    task_id: str
    status: str
    result: str | None = None
