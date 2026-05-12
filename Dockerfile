# =============================================================================
# Dockerfile — Discord Trello Bug Bot
# =============================================================================
#
# Builds a minimal container image based on python:3.12-slim.
#
# Build:
#   docker build -t arcascian-bugbot:latest .
#
# Run:
#   docker run --env-file .env arcascian-bugbot:latest
#
# The image does NOT include .env or any secrets. Environment variables
# must be injected at runtime via --env-file, -e flags, or orchestrator
# mechanisms (Docker Compose env_file, Kubernetes envFrom, etc.).
# =============================================================================

FROM python:3.12-slim
LABEL org.opencontainers.image.source="https://github.com/Piledriver-Playhouse/Discord-Trello-Bug-Bot"

# Set the working directory inside the container.
WORKDIR /app

# Copy and install Python dependencies first (layer caching optimisation).
# Changes to bot.py won't invalidate the pip install layer.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the bot package (includes code and templates).
COPY bugbot/ bugbot/
COPY templates/ bugbot/templates/

# Run the bot as a module.
CMD ["python", "-m", "bugbot.main"]
