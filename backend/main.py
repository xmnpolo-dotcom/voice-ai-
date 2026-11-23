from __future__ import annotations

import os
import shutil
import subprocess
import uuid
from pathlib import Path
from datetime import datetime, timezone

import httpx
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

ROOT = Path(__file__).resolve().parent
UPLOADS = Path(os.getenv("VOICE_AI_UPLOAD_DIR", ROOT / "uploads"))
OUTPUTS = Path(os.getenv("VOICE_AI_OUTPUT_DIR", ROOT / "outputs"))
UPLOADS.mkdir(parents=True, exist_ok=True)
OUTPUTS.mkdir(parents=True, exist_ok=True)
API_KEY = os.getenv("ELEVENLABS_API_KEY", "")
API = "https://api.elevenlabs.io/v1"
MAX_BYTES = int(os.getenv("VOICE_AI_MAX_UPLOAD_BYTES", str(3 * 1024**3)))

app = FastAPI(title="Voice AI API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("VOICE_AI_ALLOWED_ORIGINS", "*").split(","),
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

JOBS: dict[str, dict] = {}

def headers():
    if not API_KEY:
        raise HTTPException(503, "Falta configurar ELEVENLABS_API_KEY en el servidor.")
    return {"xi-api-key": API_KEY}

def api_request(method: str, url: str, **kwargs):
    try:
        response = httpx.request(method, url, headers=headers(), timeout=180, **kwargs)
        response.raise_for_status()
        return response.json() if response.content else {}
    except HTTPException:
        raise
    except httpx.HTTPStatusError as exc:
        detail = exc.response.text[:1000]
        raise HTTPException(502, f"El proveedor de doblaje respondió con un error: {detail}")
    except httpx.HTTPError as exc:
        raise HTTPException(502, f"No se pudo contactar con el proveedor de doblaje: {exc}")

@app.get("/health")
async def health():
    return {"status": "ok", "service": "voice-ai-api", "engine": "elevenlabs-dubbing-v2", "configured": bool(API_KEY)}

@app.post("/api/jobs")
async def create_job(
    file: UploadFile = File(...),
    mode: str = Form("automatic"),
    script: str = Form(""),
    language: str = Form("es"),
    voice: str = Form("es-neutral-01"),
    resolution: str = Form("4k"),
    keep_audio: bool = Form(True),
    translate_audio: bool = Form(True),
    target_language: str = Form("es"),
    translate_screen_text: bool = Form(False),
):
    if not API_KEY:
        raise HTTPException(503, "El motor aún no está activado. Falta ELEVENLABS_API_KEY en el servidor.")
    if not file.filename:
        raise HTTPException(400, "Selecciona un vídeo.")
    suffix = Path(file.filename).suffix.lower()
    if suffix not in {".mp4", ".mov", ".webm", ".m4v", ".mkv"}:
        raise HTTPException(415, "Formato no compatible. Usa MP4, MOV, WebM o MKV.")
    if mode == "script":
        raise HTTPException(501, "El modo con guion personalizado todavía no está disponible; usa Doblaje automático.")
    if target_language != "es":
        raise HTTPException(400, "Esta versión está configurada para doblar al español.")

    job_id = str(uuid.uuid4())
    source = UPLOADS / f"{job_id}{suffix}"
    size = 0
    try:
        with source.open("wb") as out:
            while chunk := await file.read(1024 * 1024):
                size += len(chunk)
                if size > MAX_BYTES:
                    raise HTTPException(413, "El vídeo supera el límite de tamaño del servidor.")
                out.write(chunk)
    except Exception:
        source.unlink(missing_ok=True)
        raise
    finally:
        await file.close()

    try:
        with source.open("rb") as media:
            data = api_request(
                "POST",
                f"{API}/dubbing/project",
                data={
                    "target_language": "es",
                    "model_id": "dubbing_v2",
                    "reference": f"Voice AI {job_id}",
                },
                files={"file": (file.filename, media, file.content_type or "video/mp4")},
            )
        language_ids = data.get("language_ids") or []
        if not language_ids:
            raise RuntimeError("El proveedor no devolvió el identificador del doblaje.")
        JOBS[job_id] = {
            "id": job_id,
            "status": "queued",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "filename": file.filename,
            "size_bytes": size,
            "source_path": str(source),
            "project_id": data["project_id"],
            "language_id": language_ids[0],
            "output_path": None,
            "message": "Vídeo enviado. El doblaje al español está en cola.",
            "translate_screen_text": translate_screen_text,
        }
        return public_job(JOBS[job_id])
    except HTTPException:
        source.unlink(missing_ok=True)
        raise
    except Exception as exc:
        source.unlink(missing_ok=True)
        raise HTTPException(502, f"No se pudo iniciar el doblaje: {exc}")

def public_job(job: dict):
    return {k: v for k, v in job.items() if k not in {"source_path", "project_id", "language_id"}}

@app.get("/api/jobs/{job_id}")
async def get_job(job_id: str):
    job = JOBS.get(job_id)
    if not job:
        raise HTTPException(404, "Trabajo no encontrado. Si el servidor se reinició, vuelve a enviar el vídeo.")
    if job["status"] not in {"completed", "failed"}:
        try:
            project = api_request("GET", f"{API}/dubbing/project/{job['project_id']}")
            language = api_request("GET", f"{API}/dubbing/project/{job['project_id']}/language/{job['language_id']}")
            p_status = project.get("status")
            l_status = language.get("status")
            if p_status == "failed" or l_status == "failed":
                job["status"] = "failed"
                job["message"] = str(language.get("error") or project.get("error") or "El proveedor no pudo completar el doblaje.")
            elif l_status == "completed":
                audio_url = (language.get("outputs") or {}).get("lossless_audio")
                if not audio_url:
                    job["status"] = "failed"
                    job["message"] = "El proveedor terminó, pero no devolvió el audio."
                else:
                    audio_path = OUTPUTS / f"{job_id}-dub.wav"
                    video_path = OUTPUTS / f"{job_id}-dubbed.mp4"
                    with httpx.stream("GET", audio_url, timeout=300) as response:
                        response.raise_for_status()
                        with audio_path.open("wb") as out:
                            for chunk in response.iter_bytes():
                                out.write(chunk)
                    cmd = [
                        "ffmpeg", "-y", "-i", job["source_path"], "-i", str(audio_path),
                        "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy",
                        "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart",
                        str(video_path),
                    ]
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=7200)
                    if result.returncode != 0:
                        raise RuntimeError(result.stderr[-1500:])
                    job["output_path"] = str(video_path)
                    job["status"] = "completed"
                    job["message"] = "¡Doblaje terminado! Ya puedes descargar el vídeo."
                    audio_path.unlink(missing_ok=True)
            else:
                job["status"] = "processing" if l_status == "processing" or p_status == "ready" else "queued"
                job["message"] = "Preparando la transcripción y generando el doblaje en español…"
        except Exception as exc:
            job["status"] = "failed"
            job["message"] = f"Error durante el procesamiento: {exc}"
    result = public_job(job)
    if job.get("output_path"):
        result["download_url"] = f"/api/jobs/{job_id}/download"
    return result

@app.get("/api/jobs/{job_id}/download")
async def download_job(job_id: str):
    job = JOBS.get(job_id)
    if not job or not job.get("output_path") or not Path(job["output_path"]).exists():
        raise HTTPException(404, "El vídeo doblado todavía no está disponible.")
    return FileResponse(job["output_path"], media_type="video/mp4", filename=f"voice-ai-{job_id}.mp4")
