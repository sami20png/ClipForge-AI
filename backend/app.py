import uuid
import subprocess
import shutil
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

BASE = Path("/tmp/clipforge")
INBOX = BASE / "inbox"
OUT = BASE / "out"

INBOX.mkdir(parents=True, exist_ok=True)
OUT.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="ClipForge AI MVP")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

def run(cmd):
    p = subprocess.run(
        cmd, capture_output=True, text=True
    )
    if p.returncode:
        raise RuntimeError(p.stderr[-1500:])
    return p.stdout

def duration(path):
    result = run([
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(path)
    ])
    return max(1.0, float(result.strip()))

@app.get("/api/health")
def health():
    return {"ok": True, "service": "ClipForge AI MVP"}

@app.post("/api/jobs/upload")
async def upload_video(video: UploadFile = File(...)):
    suffix = Path(video.filename or "video.mp4").suffix or ".mp4"
    job = uuid.uuid4().hex[:10]
    source = INBOX / f"{job}{suffix}"

    with source.open("wb") as f:
        shutil.copyfileobj(video.file, f)

    try:
        total = duration(source)
        clip_len = min(35, max(12, total / 3))
        starts = [
            max(0, min(total - clip_len, total * x))
            for x in (0.12, 0.42, 0.70)
        ]

        clips = []

        for i, start in enumerate(starts, 1):
            target = OUT / f"{job}_{i}.mp4"

            run([
                "ffmpeg", "-y", "-ss", str(start),
                "-i", str(source), "-t", str(clip_len),
                "-vf",
                "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920",
                "-r", "30", "-c:v", "libx264",
                "-preset", "veryfast", "-crf", "24",
                "-c:a", "aac", "-b:a", "128k",
                "-movflags", "+faststart", str(target)
            ])

            clips.append({
                "id": f"{job}_{i}",
                "url": f"/api/clips/{job}_{i}.mp4",
                "title": f"Must-Watch Moment #{i}",
                "description": "A standout moment from your video!",
                "hashtags": ["#Shorts", "#ClipForgeAI"],
                "potential_score": 60 + i * 5,
                "upload_time": None,
                "upload_time_note":
                "Connect channel analytics for personalized upload timing."
            })

        return {
            "job_id": job,
            "duration_seconds": round(total, 1),
            "clips": clips,
            "note": "Potential score is a placeholder, not a viral prediction."
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/clips/{filename}")
def get_clip(filename: str):
    path = OUT / Path(filename).name

    if not path.exists():
        raise HTTPException(status_code=404, detail="Clip not found")

    return FileResponse(
        path,
        media_type="video/mp4",
        filename=path.name
    )

@app.post("/api/jobs/youtube")
def youtube_placeholder():
    raise HTTPException(
        status_code=501,
        detail="YouTube URL processing is not implemented yet."
    )

@app.post("/api/jobs/live")
def live_placeholder():
    raise HTTPException(
        status_code=501,
        detail="YouTube Live processing is not implemented yet."
)
