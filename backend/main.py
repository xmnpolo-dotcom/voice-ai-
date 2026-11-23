from __future__ import annotations

import os
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

APP_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = Path(os.getenv("VOICE_AI_UPLOAD_DIR", APP_DIR / "uploads"))
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
MAX_UPLOAD_BYTES = int(os.getenv("VOICE_AI_MAX_UPLOAD_BYTES", str(8 * 1024**3)))

app = FastAPI(title="Voice AI API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("VOICE_AI_ALLOWED_ORIGINS", "http://localhost:8080").split(","),
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# Demo-only in-memory registry. Use a database and durable queue for production.
JOBS: dict[str, dict] = {}


@app.get("/health")
async def health():
    return {"status": "ok", "service": "voice-ai-api"}


@app.post("/api/jobs")
async def create_job(
    file: UploadFile = File(...),
    mode: Literal["automatic", "script"] = Form(...),
    script: str = Form(""),
    language: str = Form("es"),
    voice: str = Form("es-neutral-01"),
    resolution: Literal["original", "1080p", "4k"] = Form("4k"),
    keep_audio: bool = Form(True),
):
    if not file.filename:
        raise HTTPException(400, "Missing filename")
    if mode == "script" and not script.strip():
        raise HTTPException(400, "A script is required for script mode")

    job_id = str(uuid.uuid4())
    suffix = Path(file.filename).suffix.lower()
    if suffix not in {".mp4", ".mov", ".webm", ".m4v"}:
        raise HTTPException(415, "Unsupported video format")
    destination = UPLOAD_DIR / f"{job_id}{suffix}"
    size = 0
    try:
        with destination.open("wb") as output:
            while chunk := await file.read(1024 * 1024):
                size += len(chunk)
                if size > MAX_UPLOAD_BYTES:
                    raise HTTPException(413, "Upload exceeds configured size limit")
                output.write(chunk)
    except Exception:
        destination.unlink(missing_ok=True)
        raise
    finally:
        await file.close()

    job = {
        "id": job_id,
        "status": "queued",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "filename": file.filename,
        "size_bytes": size,
        "mode": mode,
        "language": language,
        "voice": voice,
        "resolution": resolution,
        "keep_audio": keep_audio,
        "script": script if mode == "script" else None,
        "note": "Upload received. AI dubbing pipeline is not integrated yet.",
    }
    JOBS[job_id] = job
    return job


@app.get("/api/jobs/{job_id}")
async def get_job(job_id: str):
    job = JOBS.get(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    return job
