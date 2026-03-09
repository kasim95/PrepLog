import os

SERVER_URL = "http://localhost:8000"
AUDIO_SAMPLE_RATE = 44100
AUDIO_CHANNELS = 1
AUDIO_FORMAT_WIDTH = 2  # 16-bit = 2 bytes
AUDIO_CHUNK_SIZE = 1024
TRANSCRIPTION_POLL_INTERVAL_MS = 5000  # Poll every 5 seconds
PROBLEMS_POLL_INTERVAL_MS = 3000  # Poll for new problems every 3 seconds
ATTEMPTS_POLL_INTERVAL_MS = 3000  # Poll for attempt updates every 3 seconds

# Path to docker-compose.yml (one level up from PrepLogGUI/)
DOCKER_COMPOSE_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "..", "docker-compose.yml")
