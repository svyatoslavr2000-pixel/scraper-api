"""Хранилище заданий и их выполнение.

Намеренное упрощение: задания живут в памяти процесса. Для одного сервера и
демо этого достаточно; в README честно написано, чем это плохо и что делать
дальше (Redis/Postgres + отдельный воркер).
"""

from __future__ import annotations

import csv
import io
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor

from .models import JobRequest
from .scraper import extract, fetch

# Отдельная переменная, чтобы тесты могли подменить загрузку страниц.
_fetch = fetch

_jobs: dict[str, dict] = {}
_lock = threading.Lock()
MAX_WORKERS = 4


def reset() -> None:
    """Очистить хранилище (используется в тестах)."""
    with _lock:
        _jobs.clear()


def create(request: JobRequest) -> str:
    job_id = uuid.uuid4().hex[:12]
    with _lock:
        _jobs[job_id] = {
            "id": job_id,
            "status": "queued",
            "total": len(request.urls),
            "done": 0,
            "rows": [],
            "errors": [],
            "started": time.perf_counter(),
            "duration_ms": None,
        }
    return job_id


def get(job_id: str) -> dict | None:
    with _lock:
        job = _jobs.get(job_id)
        if job is None:
            return None
        snapshot = {
            "id": job["id"],
            "status": job["status"],
            "total": job["total"],
            "done": job["done"],
            "rows": list(job["rows"]),
            "errors": list(job["errors"]),
            "duration_ms": job["duration_ms"],
        }
    return snapshot


def run(job_id: str, request: JobRequest) -> None:
    """Собрать все страницы задания. Никогда не падает наружу: ошибки идут в errors."""
    with _lock:
        if job_id not in _jobs:
            return
        _jobs[job_id]["status"] = "running"

    def one(url) -> tuple[str, dict]:
        target = str(url)
        try:
            html = _fetch(target, request.timeout)
            return "row", {**extract(html, request.fields), "url": target}
        except Exception as exc:  # noqa: BLE001 — одна страница не должна ронять задание
            message = f"{type(exc).__name__}: {exc}"[:200]
            return "error", {"url": target, "error": message}

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        for kind, payload in pool.map(one, request.urls):
            with _lock:
                if kind == "row":
                    _jobs[job_id]["rows"].append(payload)
                else:
                    _jobs[job_id]["errors"].append(payload)
                _jobs[job_id]["done"] += 1

    with _lock:
        job = _jobs[job_id]
        job["status"] = "done"
        job["duration_ms"] = int((time.perf_counter() - job["started"]) * 1000)


def to_csv(job: dict) -> str:
    """Собрать CSV: колонка url, затем все поля, затем error."""
    columns: list[str] = ["url"]
    for row in job["rows"]:
        for key in row:
            if key not in columns:
                columns.append(key)
    if job["errors"]:
        columns.append("error")

    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=columns, extrasaction="ignore")
    writer.writeheader()
    for row in job["rows"]:
        writer.writerow(row)
    for row in job["errors"]:
        writer.writerow({"url": row["url"], "error": row["error"]})
    return buffer.getvalue()
