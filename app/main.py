"""HTTP API: создать задание, забрать результат, скачать CSV."""

from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.responses import PlainTextResponse

from . import jobs
from .models import JobCreated, JobRequest, JobStatus

app = FastAPI(
    title="Scraper API",
    version="1.0.0",
    description=(
        "Небольшой сервис сбора данных: передаёте список URL и правила "
        "(CSS-селектор + атрибут), получаете строки JSON или CSV."
    ),
)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/v1/jobs", response_model=JobCreated, status_code=202)
def create_job(request: JobRequest, background: BackgroundTasks) -> JobCreated:
    job_id = jobs.create(request)
    background.add_task(jobs.run, job_id, request)
    return JobCreated(id=job_id, status="queued")


@app.get("/v1/jobs/{job_id}", response_model=JobStatus)
def get_job(job_id: str) -> JobStatus:
    job = jobs.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job not found")
    return JobStatus(**job)


@app.get("/v1/jobs/{job_id}/csv", response_class=PlainTextResponse)
def get_job_csv(job_id: str) -> PlainTextResponse:
    job = jobs.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job not found")
    return PlainTextResponse(
        jobs.to_csv(job),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{job_id}.csv"'},
    )
