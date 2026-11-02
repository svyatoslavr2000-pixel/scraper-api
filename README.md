# Scraper API — сбор данных по запросу

Небольшой HTTP-сервис: передаёте список URL и правила извлечения (CSS-селектор + атрибут),
получаете строки в JSON и готовый CSV. Одна задача — один вызов, ничего не надо ставить клиенту.

Написан как рабочая база для типовой задачи агентства: «соберите цены/товары/контакты с N страниц
и отдайте таблицей». 60 реальных строк в [`examples/sample-output.csv`](examples/sample-output.csv)
собраны этим кодом с учебного сайта `books.toscrape.com`.

## Быстрый старт

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Swagger: <http://127.0.0.1:8000/docs>

Через Docker:

```bash
docker build -t scraper-api .
docker run -p 8000:8000 scraper-api
```

## Пример запроса

```bash
curl -s -X POST http://127.0.0.1:8000/v1/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "urls": ["https://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html"],
    "fields": [
      {"name": "title",  "selector": "h1"},
      {"name": "price",  "selector": "p.price_color"},
      {"name": "cover",  "selector": "div.item.active img", "attr": "src"}
    ]
  }'
```

Ответ `202 Accepted`:

```json
{"id": "9f2c1a7b4d31", "status": "queued"}
```

Результат:

```bash
curl -s http://127.0.0.1:8000/v1/jobs/9f2c1a7b4d31
```

```json
{
  "id": "9f2c1a7b4d31",
  "status": "done",
  "total": 1,
  "done": 1,
  "rows": [
    {"title": "A Light in the Attic", "price": "£51.77", "cover": "../../media/cache/…jpg",
     "url": "https://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html"}
  ],
  "errors": [],
  "duration_ms": 412
}
```

CSV на ту же задачу:

```bash
curl -s http://127.0.0.1:8000/v1/jobs/9f2c1a7b4d31/csv -o result.csv
```

## Эндпоинты

| Метод | Путь | Что делает |
|---|---|---|
| `GET` | `/health` | проверка живости |
| `POST` | `/v1/jobs` | создать задание: `urls` (1–50), `fields` (1–30), `timeout` (1–60 с) |
| `GET` | `/v1/jobs/{id}` | статус и строки |
| `GET` | `/v1/jobs/{id}/csv` | тот же результат файлом |

Правило поля: `{"name": "price", "selector": "span.price", "attr": null}` — без `attr` берётся текст,
с `attr` — значение атрибута (`href`, `src`, `data-price`). Если элемента нет, поле будет `null`,
а задание не падает.

## Что сделано для надёжности

- одна упавшая страница не роняет задание: ошибка уходит в `errors`, остальные строки собираются;
- двухпопыточный повтор на сетевые сбои и таймауты;
- ограничение размеров запроса (50 URL / 30 полей) — чтобы один клиент не положил сервис;
- 4 параллельных запроса на задание;
- строгая валидация через Pydantic (имена полей, URL, таймауты).

## Честные ограничения

- задания хранятся **в памяти процесса**: перезапуск сервиса их стирает;
- нет очереди и ретраев между воркерами — для объёмов «сотни страниц в сутки» этого хватает,
  для «миллион страниц» нужен Redis + отдельный воркер;
- нет авторизации: сервис рассчитан на запуск в закрытом контуре или за API-шлюзом;
- JS-страницы (бесконечный скролл, SPA) этим парсером не берутся — там нужен Playwright,
  см. [playwright-scraper-template](https://github.com/svyatoslavr2000-pixel/playwright-scraper-template).

## Проверка

```bash
pip install -r requirements-dev.txt
ruff check .
pytest -q
```

9 тестов, сеть в тестах не используется (загрузка страниц подменяется).
CI: GitHub Actions, Python 3.12.

## Структура

```
app/
  main.py      HTTP-слой (FastAPI)
  jobs.py      хранилище заданий, параллельный сбор, CSV
  scraper.py   загрузка страницы и разбор по селекторам
  models.py    схемы запросов и ответов
tests/         тесты API
examples/      демо-скрипт и пример результата
```

## English

A small FastAPI service for structured web scraping: POST a list of URLs plus CSS rules,
get JSON rows and a CSV export. Includes retries, per-URL error isolation, request size limits
and 9 tests. Not production-hardened on purpose — jobs live in memory (see limitations above).

## Лицензия

MIT
