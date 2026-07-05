# syntax=docker/dockerfile:1
# LiveKit Cloud production image for the voice agent worker.
ARG PYTHON_VERSION=3.13
FROM python:${PYTHON_VERSION}-slim-bookworm

ENV PYTHONUNBUFFERED=1
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml main.py ./
COPY clinic ./clinic

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir .

COPY . .

RUN python main.py download-files

CMD ["python", "main.py", "start"]
