# For more information, please refer to https://aka.ms/vscode-docker-python
FROM python:3.10-slim

EXPOSE 8000

# Keeps Python from generating .pyc files in the container
ENV PYTHONDONTWRITEBYTECODE=1
# Turns off buffering for easier container logging
ENV PYTHONUNBUFFERED=1

# Install system dependencies
# Combined install and cleanup
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        ffmpeg \
        libsm6 \
        libxext6 \
        poppler-utils \
        tesseract-ocr \
        ghostscript \
        libgl1-mesa-glx \
        libglib2.0-0 && \
    rm -rf /var/lib/apt/lists/*

# Install pip requirements
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Define the working directory
WORKDIR /app

# Create application directories (these will be overlaid by named volumes if used in compose)
RUN mkdir -p /app/uploads && \
    mkdir -p /app/outputs && \
    mkdir -p /app/img/pages && \
    mkdir -p /app/img/figures && \
    mkdir -p /app/weights/detect

COPY . /app

# Non-root user setup (from your Dockerfile)
RUN adduser -u 5678 --disabled-password --gecos "" appuser && chown -R appuser /app
USER appuser

# CMD
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]