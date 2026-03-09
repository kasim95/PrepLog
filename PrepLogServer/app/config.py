from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite+aiosqlite:///./preplog.db"
    RECORDINGS_DIR: str = str(Path(__file__).parent.parent / "recordings")
    TRANSCRIPTION_SERVICE_URL: str = "http://localhost:8001"
    CALLBACK_BASE_URL: str = "http://localhost:8000"  # Base URL for transcription callbacks
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    model_config = {"env_prefix": "PREPLOG_"}


settings = Settings()

# Ensure recordings directory exists
Path(settings.RECORDINGS_DIR).mkdir(parents=True, exist_ok=True)
