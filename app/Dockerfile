# FastAPI / Uvicorn image
FROM python:3.11-slim

# Create and set working directory
RUN mkdir -p /app
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

# Install system dependencies required for PyAudio and other audio processing
RUN apt-get update && apt-get install -y \
    build-essential \
    portaudio19-dev \
    libasound2-dev \
    libportaudio2 \
    libportaudiocpp0 \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Copy Python deps and install
# Use minimal requirements for production to reduce size and startup time
COPY requirements-minimal.txt requirements.txt ./
RUN pip install --no-cache-dir -r requirements-minimal.txt || \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY api/ ./api/
COPY config.py ./config.py
COPY config/ ./config/
COPY domain/ ./domain/
COPY ai/ ./ai/
COPY services/ ./services/
COPY repos/ ./repos/
COPY security/ ./security/
COPY storage/ ./storage/
COPY util/ ./util/
COPY __init__.py .
COPY test_api.py .

# Copy startup script
COPY simple_start.py ./

EXPOSE 8000

# Use simple startup script for Container Apps
CMD ["python", "simple_start.py"]