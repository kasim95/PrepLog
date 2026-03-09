from datetime import datetime

from pydantic import BaseModel

# ── Problem ──────────────────────────────────────────────────────────

class ProblemCreate(BaseModel):
    title: str
    description: str | None = None
    difficulty: str | None = None
    source: str = "custom"
    leetcode_slug: str | None = None


class ProblemUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    difficulty: str | None = None


class ProblemResponse(BaseModel):
    id: int
    title: str
    description: str | None
    difficulty: str | None
    source: str
    leetcode_slug: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Attempt ──────────────────────────────────────────────────────────

class AttemptCreate(BaseModel):
    code_submission: str | None = None
    notes: str | None = None
    status: str = "in_progress"


class AttemptUpdate(BaseModel):
    code_submission: str | None = None
    notes: str | None = None
    status: str | None = None
    ended_at: datetime | None = None


class AttemptResponse(BaseModel):
    id: int
    problem_id: int
    code_submission: str | None
    notes: str | None
    status: str
    started_at: datetime
    ended_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Recording ────────────────────────────────────────────────────────

class RecordingResponse(BaseModel):
    id: int
    attempt_id: int
    file_path: str
    duration_seconds: float | None
    transcription: str | None
    transcription_status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class TranscriptionCallback(BaseModel):
    recording_id: int
    transcription: str
    status: str  # "completed" or "failed"


class TranscriptionResponse(BaseModel):
    recording_id: int
    transcription: str | None
    status: str


# ── LeetCode ─────────────────────────────────────────────────────────

class LeetCodeProblem(BaseModel):
    title: str
    description: str | None = None
    difficulty: str | None = None
    leetcode_slug: str


class LeetCodeSubmission(BaseModel):
    leetcode_slug: str
    code: str
    language: str | None = None
