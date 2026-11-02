"""Тесты API. Сеть не используется: загрузка страниц подменяется."""

import pytest
from fastapi.testclient import TestClient

from app import jobs
from app.main import app

HTML = """
<html><body>
  <div class="card">
    <h2 class="title">Кофемашина</h2>
    <span class="price">49 990</span>
    <a class="link" href="/item/1">Открыть</a>
  </div>
</body></html>
"""

FIELDS = [
    {"name": "title", "selector": "h2.title"},
    {"name": "price", "selector": "span.price"},
    {"name": "link", "selector": "a.link", "attr": "href"},
    {"name": "missing", "selector": "div.no-such-thing"},
]


@pytest.fixture()
def client():
    jobs.reset()
    return TestClient(app)


@pytest.fixture()
def fake_fetch(monkeypatch):
    def _fake(url: str, timeout: float = 10.0) -> str:
        return HTML

    monkeypatch.setattr(jobs, "_fetch", _fake)
    return _fake


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_job_extracts_fields(client, fake_fetch):
    created = client.post(
        "/v1/jobs",
        json={"urls": ["https://shop.example/item/1"], "fields": FIELDS},
    )
    assert created.status_code == 202
    job_id = created.json()["id"]

    job = client.get(f"/v1/jobs/{job_id}").json()
    assert job["status"] == "done"
    assert job["total"] == 1
    assert job["done"] == 1
    assert job["errors"] == []

    row = job["rows"][0]
    assert row["title"] == "Кофемашина"
    assert row["price"] == "49 990"
    assert row["link"] == "/item/1"
    assert row["missing"] is None
    assert row["url"].startswith("https://shop.example/item/1")


def test_failed_page_goes_to_errors(client, monkeypatch):
    def _boom(url: str, timeout: float = 10.0) -> str:
        raise ConnectionError("host is down")

    monkeypatch.setattr(jobs, "_fetch", _boom)

    created = client.post(
        "/v1/jobs",
        json={"urls": ["https://broken.example/"], "fields": FIELDS},
    )
    job_id = created.json()["id"]

    job = client.get(f"/v1/jobs/{job_id}").json()
    assert job["status"] == "done"
    assert job["rows"] == []
    assert len(job["errors"]) == 1
    assert "ConnectionError" in job["errors"][0]["error"]


def test_csv_export(client, fake_fetch):
    created = client.post(
        "/v1/jobs",
        json={"urls": ["https://shop.example/item/1"], "fields": FIELDS},
    )
    job_id = created.json()["id"]

    response = client.get(f"/v1/jobs/{job_id}/csv")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    body = response.text
    assert body.splitlines()[0] == "url,title,price,link,missing"
    assert "Кофемашина" in body
    assert "49 990" in body


def test_unknown_job_returns_404(client):
    assert client.get("/v1/jobs/nope").status_code == 404
    assert client.get("/v1/jobs/nope/csv").status_code == 404


@pytest.mark.parametrize(
    "payload",
    [
        {"urls": [], "fields": FIELDS},
        {"urls": ["https://a.example/"], "fields": []},
        {"urls": ["not-a-url"], "fields": FIELDS},
        {"urls": ["https://a.example/"], "fields": [{"name": "bad name!", "selector": "h1"}]},
    ],
)
def test_validation_rejects_bad_input(client, payload):
    assert client.post("/v1/jobs", json=payload).status_code == 422
