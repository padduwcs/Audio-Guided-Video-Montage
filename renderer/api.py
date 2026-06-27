"""RESTful API for Stage 8 Renderer (MVP)."""

from fastapi import FastAPI, BackgroundTasks, UploadFile, File, Form
from pydantic import BaseModel
import uuid
import os
from concurrent.futures import ThreadPoolExecutor
from renderer.core import render_timeline

app = FastAPI(title="Renderer API", description="RESTful API for Stage 8 Renderer")

JOBS = {}
RENDER_EXECUTOR = ThreadPoolExecutor(max_workers=4)

class RenderJobRequest(BaseModel):
    timeline_path: str
    output_path: str = "data/final/api_render.mp4"
    log_path: str = "data/final/api_render_log.json"
    overlay_image: str = None
    overlay_pos: str = "top-right"
    preview: bool = False

@app.post("/render")
def submit_render_job(req: RenderJobRequest, background_tasks: BackgroundTasks):
    job_id = str(uuid.uuid4())
    JOBS[job_id] = {"status": "pending", "output": req.output_path, "log": req.log_path}
    def run_render():
        try:
            render_timeline(
                req.timeline_path,
                req.output_path,
                log_path=req.log_path,
                overlay_image=req.overlay_image,
                overlay_pos=req.overlay_pos,
                preview=req.preview
            )
            JOBS[job_id]["status"] = "done"
        except Exception as e:
            JOBS[job_id]["status"] = f"error: {e}"
    RENDER_EXECUTOR.submit(run_render)
    return {"job_id": job_id, "status": "pending"}

@app.get("/status/{job_id}")
def get_job_status(job_id: str):
    return JOBS.get(job_id, {"status": "not found"})

@app.get("/")
def root():
    return {"message": "Renderer API is running"}