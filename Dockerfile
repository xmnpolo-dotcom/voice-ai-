FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY backend ./backend
WORKDIR /app/backend
ENV VOICE_AI_UPLOAD_DIR=/var/data/uploads
ENV VOICE_AI_OUTPUT_DIR=/var/data/outputs
RUN mkdir -p /var/data/uploads /var/data/outputs
EXPOSE 8000
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
