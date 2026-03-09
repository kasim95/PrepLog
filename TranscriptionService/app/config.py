from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    REDIS_URL: str = "redis://localhost:6379/0"
    WHISPER_MODEL: str = "base"
    CALLBACK_TIMEOUT: int = 30
    TEMP_AUDIO_DIR: str = str(Path(__file__).parent.parent / "temp_audio")
    HOST: str = "0.0.0.0"
    PORT: int = 8001

    model_config = {"env_prefix": "TRANSCRIPTION_"}


settings = Settings()

# Ensure temp audio directory exists
Path(settings.TEMP_AUDIO_DIR).mkdir(parents=True, exist_ok=True)
