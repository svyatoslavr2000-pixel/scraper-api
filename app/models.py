"""Pydantic-схемы запросов и ответов API."""

from pydantic import BaseModel, Field, HttpUrl


class FieldRule(BaseModel):
    """Правило извлечения одного поля из HTML."""

    name: str = Field(..., min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")
    selector: str = Field(..., min_length=1, max_length=300)
    attr: str | None = Field(
        default=None,
        max_length=64,
        description="Имя атрибута (href, src, data-price). Если не задан — берётся текст.",
    )


class JobRequest(BaseModel):
    """Задание на сбор данных."""

    urls: list[HttpUrl] = Field(..., min_length=1, max_length=50)
    fields: list[FieldRule] = Field(..., min_length=1, max_length=30)
    timeout: float = Field(default=10.0, ge=1.0, le=60.0)


class JobCreated(BaseModel):
    id: str
    status: str


class JobStatus(BaseModel):
    id: str
    status: str
    total: int
    done: int
    rows: list[dict]
    errors: list[dict]
    duration_ms: int | None = None
