# API

## Обзор

FastAPI слой для работы с пользователями, курсами, рекомендациями и сервисными операциями.
Базовый URL при локальном запуске: `http://localhost:8000`.

## Запуск

```bash
python -m pip install -r requirements.txt -r requirements-dev.txt
python -m src.api
```

## Swagger / OpenAPI

- Swagger UI: `http://localhost:8000/docs`
- OpenAPI JSON: `http://localhost:8000/openapi.json`

## Эндпоинты

### Health

```http
GET /health
```

Ответ:
```json
{"status":"ok"}
```

### DB

```http
POST /db/init
```

Тело запроса:
```json
{
  "drop_existing": false,
  "courses_file": "data/courses.json",
  "skip_courses_seed": false
}
```

Ответ:
```json
{
  "courses_seeded": 0,
  "courses_count": 0,
  "chunks_count": 0,
  "collection_recreated": false
}
```

### Courses

```http
POST /courses/seed
```

Тело запроса:
```json
{"file_path":"data/courses.json"}
```

Ответ:
```json
{"inserted":0}
```

```http
GET /courses
```

Ответ:
```json
[
  {"id":1,"name":"Course name","description":"..."}
]
```

### Users

```http
POST /users
```

Тело запроса:
```json
{"login":"roman","digital_footprints":"{\"events\":[]}"}
```

Ответ:
```json
{"id":1,"login":"roman","updated_at":"2026-02-16T20:00:00+00:00"}
```

```http
GET /users
```

Ответ:
```json
[
  {"id":1,"login":"roman","updated_at":"2026-02-16T20:00:00+00:00"}
]
```

```http
POST /users/seed
```

Тело запроса:
```json
{"file_path":"data/digital-footprints.json"}
```

Ответ:
```json
{"created":0,"updated":0,"skipped":0}
```

### Recommendations

```http
POST /recommendations
```

Тело запроса:
```json
{"login":"roman","text":"Начните с курса по Python"}
```

Ответ:
```json
{"id":1,"text":"...","created_at":"2026-02-16T20:00:00+00:00"}
```

```http
GET /recommendations/{login}
```

Ответ:
```json
[
  {"id":1,"text":"...","created_at":"2026-02-16T20:00:00+00:00"}
]
```

```http
POST /recommendations/generate
```

Тело запроса:
```json
{"login":"alex_dev","top_k":5,"search_k":20}
```

Ответ:
```json
{
  "recommendation": {"id":1,"text":"...","created_at":"2026-02-16T20:00:00+00:00"},
  "debug_file_path": "data/recs/20260216T000000Z_alex_dev.json",
  "query_text": "query: ...",
  "retrieved_courses": [
    {"course_id":1,"name":"...","description":"...","score":0.9}
  ]
}
```
