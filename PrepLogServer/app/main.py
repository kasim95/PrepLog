from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import engine
from app.models import Base
from app.routers import attempts, leetcode, problems, recordings


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables on startup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


app = FastAPI(
    title="PrepLog Server",
    description="Backend API for PrepLog interview preparation tracker",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS - allow GUI and Chrome extension
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(problems.router)
app.include_router(attempts.router)
app.include_router(recordings.router)
app.include_router(leetcode.router)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "PrepLogServer"}


if __name__ == "__main__":
    import uvicorn

    from app.config import settings

    uvicorn.run("app.main:app", host=settings.HOST, port=settings.PORT, reload=True)
