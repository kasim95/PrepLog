# PrepLog - Interview Preparation Tracker

A multi-component application for tracking interview preparation, including audio
recording, transcription, and LeetCode problem tracking. Backend services run via
Docker Compose; the GUI runs natively on macOS as a desktop application.

## Architecture

| Component | Technology | Port |
|-----------|-----------|------|
| **PrepLogServer** | FastAPI + SQLAlchemy + SQLite | 8000 |
| **TranscriptionService** | FastAPI + Celery + Whisper | 8001 |
| **PrepLogGUI** | Python Tkinter (macOS desktop) | – |
| **PrepLogChromeExtension** | TypeScript + Chrome MV3 | – |

```
PrepLogGUI ──HTTP──▶ PrepLogServer ──HTTP──▶ TranscriptionService
     │                    ▲                        │
     │  Chrome Extension ─┘                   Celery + Redis
     │
     └── Docker Compose (manage backend from GUI)
```

## Prerequisites

- **Python 3.13+**
- **[uv](https://docs.astral.sh/uv/)** – Python package manager
- **Docker & Docker Compose** – for running backend services
- **Node.js 18+** and npm (for Chrome extension only)
- **PortAudio** – system library for audio recording (`brew install portaudio` on macOS)

## Quick Start

### Option A: Docker Compose (Recommended)

Start all backend services with a single command:

```bash
docker compose up -d --build
```

This launches four services on a shared `preplog` bridge network:

| Service | Description |
|---------|-------------|
| `redis` | Message broker for Celery |
| `preplog-server` | FastAPI backend (port 8000) |
| `transcription-api` | Whisper transcription API (port 8001) |
| `celery-worker` | Async transcription worker |

Verify everything is running:

```bash
docker compose ps
```

API docs: http://localhost:8000/docs

### Option B: Manual Setup

<details>
<summary>Click to expand manual setup instructions</summary>

#### 1. Start Redis

```bash
docker run -d --name preplog-redis -p 6379:6379 redis:alpine
```

#### 2. Start PrepLogServer

```bash
cd PrepLogServer
uv sync
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

#### 3. Start TranscriptionService

```bash
cd TranscriptionService
uv sync

# Start the FastAPI server
uv run uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload

# In another terminal, start the Celery worker
cd TranscriptionService
uv run celery -A app.celery_app:celery_app worker --loglevel=info --concurrency=1
```

</details>

### Launch the GUI

```bash
cd PrepLogGUI
uv sync

# Option 1: Run as module
uv run python -m app.main

# Option 2: Use the installed gui-script entry point
uv run preplog
```

### Load Chrome Extension

```bash
cd PrepLogChromeExtension
npm install
npm run build
```

1. Open Chrome → `chrome://extensions/`
2. Enable "Developer mode"
3. Click "Load unpacked"
4. Select the `PrepLogChromeExtension/dist` folder

## Usage

### Docker Management (GUI)

The Docker panel is located at the bottom of the GUI under the **Advanced Settings** section (collapsed by default). Click the toggle to expand it:

- **Start** / **Stop** – run `docker compose up -d --build` or `docker compose down`
- **Refresh** – check the status of all services
- Status indicator shows ● (running) or ○ (stopped) with per-service details

### Attempt Lifecycle

Each practice session follows a structured attempt lifecycle managed from the **Problem** panel:

1. Select a problem, then click **▶ Start Attempt** to create a new attempt (`in_progress`)
2. Optionally click **⏸ Pause Attempt** / **▶ Resume Attempt** to pause work
3. Click **■ Stop Attempt** to mark the attempt as `completed`

Recordings and code submissions are tied to the currently active attempt.

### Recording Practice Sessions

1. Start an attempt first — the recording panel is only enabled when an attempt is active
2. Click **● Record** to start recording your explanation
3. Use **⏸ Pause** / **▶ Resume** to pause and resume recording mid-session
4. Click **■ Stop** when done — the audio is uploaded and transcription begins automatically
5. A live timer tracks recording duration (paused time excluded)

### Tracking LeetCode Problems

1. Install the Chrome extension
2. Navigate to a LeetCode problem
3. The extension detects the problem automatically
4. Click **Track Problem** to save it to PrepLog
5. After submitting a solution, click **Send Submission** — the code is attached to your current `in_progress` attempt

### Reviewing Attempts

- Select a problem to see all attempts sorted chronologically (oldest first)
- Each attempt row shows status icons: 📝 (has code), 🎤 (has recording), ✓ (transcribed), ⏳ (transcription pending)
- Toggle **View Code** to expand inline code viewer for any attempt
- Click **↻ Retranscribe** to re-run transcription on a recording
- Transcriptions auto-poll and appear when processing completes

## Configuration

### Environment Variables

**PrepLogServer** (prefix: `PREPLOG_`):

| Variable | Default | Description |
|----------|---------|-------------|
| `PREPLOG_DATABASE_URL` | `sqlite+aiosqlite:///./preplog.db` | Database URL |
| `PREPLOG_RECORDINGS_DIR` | `./recordings` | Audio file storage path |
| `PREPLOG_TRANSCRIPTION_SERVICE_URL` | `http://localhost:8001` | Transcription service URL |
| `PREPLOG_CALLBACK_BASE_URL` | `http://localhost:8000` | Base URL for transcription callbacks (set to `http://preplog-server:8000` in Docker) |
| `PREPLOG_HOST` | `0.0.0.0` | Server bind host |
| `PREPLOG_PORT` | `8000` | Server port |

**TranscriptionService** (prefix: `TRANSCRIPTION_`):

| Variable | Default | Description |
|----------|---------|-------------|
| `TRANSCRIPTION_REDIS_URL` | `redis://localhost:6379/0` | Redis broker URL |
| `TRANSCRIPTION_WHISPER_MODEL` | `base` | Whisper model size (`tiny`, `base`, `small`, `medium`, `large`) |
| `TRANSCRIPTION_CALLBACK_TIMEOUT` | `30` | Callback HTTP timeout (seconds) |
| `TRANSCRIPTION_HOST` | `0.0.0.0` | Service bind host |
| `TRANSCRIPTION_PORT` | `8001` | Service port |

### Docker Compose Environment

The `docker-compose.yml` overrides defaults for inter-service networking:

| Setting | Docker Value | Purpose |
|---------|-------------|---------|
| `PREPLOG_TRANSCRIPTION_SERVICE_URL` | `http://transcription-api:8001` | Server → Transcription via Docker DNS |
| `PREPLOG_CALLBACK_BASE_URL` | `http://preplog-server:8000` | Transcription → Server callback via Docker DNS |
| `TRANSCRIPTION_REDIS_URL` | `redis://redis:6379/0` | Workers → Redis via Docker DNS |

## Development

### Running Tests

```bash
# PrepLogServer tests
uv run --project PrepLogServer pytest PrepLogServer/tests/ -q

# PrepLogGUI tests
uv run --project PrepLogGUI pytest PrepLogGUI/tests/ -q
```

### Linting

```bash
# All Python projects
uv run --project PrepLogServer ruff check PrepLogServer/
uv run --project PrepLogGUI ruff check PrepLogGUI/
uv run --project TranscriptionService ruff check TranscriptionService/
```

## Project Structure

```
PrepLog/
├── SPEC.md                        # Top-level architecture spec
├── README.md                      # This file
├── docker-compose.yml             # Full backend orchestration
├── PrepLogServer/                 # FastAPI backend
│   ├── SPEC.md
│   ├── Dockerfile
│   ├── pyproject.toml
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── models.py
│   │   ├── schemas.py
│   │   ├── routers/
│   │   │   ├── problems.py
│   │   │   ├── attempts.py
│   │   │   ├── recordings.py
│   │   │   └── leetcode.py
│   │   └── services/
│   │       └── transcription.py
│   └── tests/
├── TranscriptionService/          # Whisper transcription microservice
│   ├── SPEC.md
│   ├── Dockerfile
│   ├── pyproject.toml
│   └── app/
│       ├── main.py
│       ├── config.py
│       ├── celery_app.py
│       ├── tasks.py
│       ├── schemas.py
│       └── routers/
│           └── transcribe.py
├── icon.svg                       # Application icon (source SVG)
├── PrepLogGUI/                    # Tkinter desktop application
│   ├── SPEC.md
│   ├── pyproject.toml
│   ├── assets/
│   │   └── icon.png               # Window icon (512×512)
│   └── app/
│       ├── main.py
│       ├── config.py
│       ├── api_client.py
│       ├── audio_recorder.py
│       ├── audio_player.py
│       └── components/
│           ├── problem_panel.py
│           ├── recording_panel.py
│           ├── attempts_panel.py
│           ├── transcription_panel.py
│           └── docker_panel.py
└── PrepLogChromeExtension/        # Chrome extension
    ├── SPEC.md
    ├── package.json
    ├── tsconfig.json
    ├── webpack.config.js
    └── src/
        ├── manifest.json
        ├── icons/
        │   ├── icon16.png
        │   ├── icon32.png
        │   ├── icon48.png
        │   └── icon128.png
        ├── background.ts
        ├── content.ts
        ├── popup.html
        ├── popup.ts
        ├── types.ts
        ├── api.ts
        └── styles/
            └── popup.css
```
