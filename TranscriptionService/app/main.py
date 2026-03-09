from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import transcribe

app = FastAPI(
    title="PrepLog Transcription Service",
    description="Audio transcription microservice using OpenAI Whisper",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(transcribe.router)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "TranscriptionService"}


if __name__ == "__main__":
    import uvicorn

    from app.config import settings

    uvicorn.run("app.main:app", host=settings.HOST, port=settings.PORT, reload=True)
