"""Загрузка страниц и извлечение полей по CSS-селекторам."""

from __future__ import annotations

import httpx
from selectolax.lexbor import LexborHTMLParser

from .models import FieldRule

USER_AGENT = "scraper-api/1.0 (+https://github.com/svyatoslavr2000-pixel/scraper-api)"
MAX_ATTEMPTS = 2


def fetch(url: str, timeout: float = 10.0) -> str:
    """Скачать страницу. Транспортные ошибки повторяются один раз."""
    last: Exception | None = None
    for _ in range(MAX_ATTEMPTS):
        try:
            with httpx.Client(
                headers={"User-Agent": USER_AGENT},
                follow_redirects=True,
                timeout=timeout,
            ) as client:
                response = client.get(url)
                response.raise_for_status()
                return response.text
        except (httpx.TransportError, httpx.TimeoutException) as exc:  # сеть/таймаут — пробуем ещё
            last = exc
        except httpx.HTTPStatusError:
            raise
    raise last  # type: ignore[misc]


def extract(html: str, fields: list[FieldRule]) -> dict:
    """Вытащить значения полей. Отсутствующий элемент даёт None, а не падение."""
    tree = LexborHTMLParser(html)
    row: dict[str, str | None] = {}
    for rule in fields:
        node = tree.css_first(rule.selector)
        if node is None:
            row[rule.name] = None
        elif rule.attr:
            row[rule.name] = node.attributes.get(rule.attr)
        else:
            row[rule.name] = node.text(strip=True)
    return row
