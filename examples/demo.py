"""Демо: собрать книги с учебного песочного сайта и сохранить CSV.

Запуск (без поднятия сервера — используется тот же разбор, что и в API):

    python examples/demo.py

books.toscrape.com специально сделан для тренировки парсинга.
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

from selectolax.lexbor import LexborHTMLParser

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.models import FieldRule
from app.scraper import fetch

BASE = "https://books.toscrape.com/catalogue/page-{}.html"
CARD = "article.product_pod"
FIELDS = [
    FieldRule(name="title", selector="h3 a", attr="title"),
    FieldRule(name="price", selector="p.price_color"),
    FieldRule(name="availability", selector="p.instock.availability"),
    FieldRule(name="rating", selector="p.star-rating", attr="class"),
    FieldRule(name="link", selector="h3 a", attr="href"),
]
OUTPUT = Path(__file__).with_name("sample-output.csv")


def row_from_card(card, page: int) -> dict:
    """Разобрать одну карточку: те же правила, но внутри узла карточки."""
    row: dict = {"page": page}
    for rule in FIELDS:
        node = card.css_first(rule.selector)
        if node is None:
            row[rule.name] = None
        elif rule.attr:
            row[rule.name] = node.attributes.get(rule.attr)
        else:
            row[rule.name] = node.text(strip=True)
    return row


def main() -> None:
    rows: list[dict] = []
    for page in range(1, 4):
        html = fetch(BASE.format(page), timeout=20.0)
        for card in LexborHTMLParser(html).css(CARD):
            rows.append(row_from_card(card, page))

    columns = ["page", "title", "price", "availability", "rating", "link"]
    with OUTPUT.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)

    print(f"{len(rows)} rows -> {OUTPUT}")
    print("example:", rows[0] if rows else "no rows")


if __name__ == "__main__":
    main()
