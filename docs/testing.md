# Отчёт о тестировании

## Подход к тестированию

### Принципы

Тестовая база проекта ограничена **юнит-тестами** — намеренно:

- Все компоненты, требующие живых инфраструктурных зависимостей (PostgreSQL, Qdrant, Redis, NATS, Ollama, Mautic), изолируются через mock-объекты или полностью выведены за рамки юнит-тестов.
- Каждый тест покрывает **один сценарий** — один `assert` на ветку кода, без комбинированных проверок в одной функции.
- Имена тестов описывают _что_ тестируется и _какой_ ожидается результат: `test_parse_lead_id_whitespace_only_string_raises_validation_error`.

### Структура

```
tests/
├── unit/                                    # Тесты без зависимостей от инфраструктуры
│   ├── test_digital_footprints_profile.py   # preprocessing: build_digital_footprint_profile_text
│   ├── test_generate_worker.py              # workers: NATS-воркер генерации (мок)
│   ├── test_mauitc_activity_reader.py       # mauitc: разбор событий Mautic
│   ├── test_nats_client.py                  # query_client: публикация/подписка NATS (мок)
│   ├── test_rag_core.py                     # rag_core: embedding-input, prompt-builder (курсовой пайплайн)
│   ├── test_rag_core_embeddings.py          # rag_core: extract_embedding, mean_pool, normalize_vector_size
│   ├── test_rag_core_llm.py                 # rag_core: extract_llm_text (все форматы ответа)
│   ├── test_rag_core_parser.py              # rag_core: parse_recommendation_payload
│   ├── test_rag_core_prompt_builder.py      # rag_core: format_available_content, render_typed_prompt
│   ├── test_rag_core_retriever.py           # rag_core: resource_type_for_recommendation, build_resource_type_filter
│   ├── test_recommendation_service_utils.py # services: утилиты RecommendationGenerationService и QueryService
│   └── test_recommendations_filters.py     # services: фильтрация ресурсов и Mautic-сохранение
└── integration/
    ├── test_api_auth.py                     # FastAPI TestClient: JWT-авторизация (без БД)
    ├── test_mautic_client.py                # Живые вызовы к Mautic API (требует Mautic)
    └── test_rag_api_endpoints.py            # FastAPI TestClient: эндпоинты с mock-сервисами
```

### Запуск

```bash
# Только юнит-тесты
python -m pytest tests/unit/ -v

# Все тесты (юнит + интеграционные)
python -m pytest tests/ -v

# Быстрый прогон
python -m pytest tests/ -q
```

---

## Результаты

### Юнит-тесты (`tests/unit/`)

| Файл | Тестов | Статус |
|------|--------|--------|
| `test_digital_footprints_profile.py` | 3 | ✅ PASS |
| `test_generate_worker.py` | 6 | ✅ PASS |
| `test_mauitc_activity_reader.py` | 2 | ✅ PASS |
| `test_nats_client.py` | 3 | ✅ PASS |
| `test_rag_core.py` | 5 | ✅ PASS |
| `test_rag_core_embeddings.py` | 10 | ✅ PASS |
| `test_rag_core_llm.py` | 8 | ✅ PASS |
| `test_rag_core_parser.py` | 8 | ✅ PASS |
| `test_rag_core_prompt_builder.py` | 8 | ✅ PASS |
| `test_rag_core_retriever.py` | 8 | ✅ PASS |
| `test_recommendation_service_utils.py` | 23 | ✅ PASS |
| `test_recommendations_filters.py` | 6 | ✅ PASS |
| **Итого юнит** | **90** | **90/90** |

### Интеграционные тесты (`tests/integration/`)

| Файл | Тестов | Статус |
|------|--------|--------|
| `test_api_auth.py` | 2 | ✅ PASS |
| `test_mautic_client.py` | 7 | ✅ PASS |
| `test_rag_api_endpoints.py` | 24 | ✅ PASS |
| **Итого интеграционных** | **33** | **33/33** |

### Суммарно

**Итого: 123/123** ✅

---

## Покрытые модули и сценарии

### `src/rag_core/parser.py`
_Файл: `test_rag_core_parser.py`_

| Сценарий | Ожидаемый результат |
|----------|---------------------|
| Чистый JSON-объект | Возвращается как есть |
| JSON, обёрнутый в текст LLM ("Here is the result:\n{...}") | Блок `{...}` извлекается через `find`/`rfind` |
| Вложенный JSON-объект (nested keys) | Структура сохраняется |
| JSON с пробелами по краям | Работает после `strip()` |
| Пустая строка | `ValueError` |
| Строка только из пробелов | `ValueError` |
| Валидный JSON, но список, а не объект | `ValueError` |
| Текст без фигурных скобок | `ValueError` |

---

### `src/rag_core/embeddings.py`
_Файл: `test_rag_core_embeddings.py`_

| Сценарий | Ожидаемый результат |
|----------|---------------------|
| `extract_embedding` — формат OpenAI: `{data: [{embedding: [...]}]}` | Вектор из `data[0].embedding` |
| `extract_embedding` — формат Ollama: `{embedding: [...]}` | Вектор из `embedding` |
| `extract_embedding` — формат `embeddings: [[...]]` | Вектор из `embeddings[0]` |
| `extract_embedding` — прямой список float | Вектор как есть |
| `extract_embedding` — неподдерживаемый формат | `ValueError` |
| `mean_pool` двух векторов | Поэлементное среднее |
| `mean_pool` пустого списка | `[]` |
| `normalize_vector_size` — вектор короче целевого | Дополняется нулями |
| `normalize_vector_size` — вектор длиннее целевого | Обрезается |
| `normalize_vector_size` — вектор точного размера | Возвращается копия без мутации оригинала |

---

### `src/rag_core/llm.py`
_Файл: `test_rag_core_llm.py`_

| Сценарий | Ожидаемый результат |
|----------|---------------------|
| OpenAI chat completion: `choices[0].message.content` | Строка из `content` |
| OpenAI completion: `choices[0].text` | Строка из `text` |
| Ollama generate: `response` | Строка из `response`, пробелы обрезаны |
| HuggingFace top-level: `generated_text` | Строка из `generated_text` |
| HuggingFace list: `[{generated_text: ...}]` | Строка из `[0].generated_text` |
| Пустой словарь `{}` | `ValueError` |
| Целое число `42` | `ValueError` |
| Пробелы по краям в `content` | Обрезаются (`strip()`) |

---

### `src/rag_core/retriever.py`
_Файлы: `test_rag_core_retriever.py`, `test_recommendations_filters.py`_

| Сценарий | Ожидаемый результат |
|----------|---------------------|
| `resource_type_for_recommendation("cold")` | `"article"` |
| `resource_type_for_recommendation("hot")` | `"course"` |
| `resource_type_for_recommendation("warm")` | `None` — без фильтрации |
| `resource_type_for_recommendation("after_sale")` | `None` — без фильтрации |
| `resource_type_for_recommendation("unknown_xyz")` | `None` |
| `build_resource_type_filter("article")` | `Filter` с одним `FieldCondition(key="resource_type", match="article")` |
| `build_resource_type_filter("course")` | `Filter` matching `"course"` |
| `build_resource_type_filter(None)` | `None` |

---

### `src/rag_core/prompt_builder.py`
_Файлы: `test_rag_core_prompt_builder.py`, `test_rag_core.py`_

| Сценарий | Ожидаемый результат |
|----------|---------------------|
| `format_available_content([])` | Пустая строка |
| Ресурс с `url=None` | В выводе появляется `"n/a"` |
| Ресурс с заголовком, типом, фрагментом, оценкой | Всё присутствует в строке |
| Фрагмент длиннее 500 символов | Обрезается с `"..."` |
| Два ресурса | Нумеруются с `1.` и `2.` |
| `render_typed_prompt` — существующий тип | Подстановка `{available_content}` и `{digital_traces}` |
| `render_typed_prompt` — несуществующий тип | `ValueError` |
| `PROMPTS_DIR` — константа пути | Директория существует, содержит `cold.txt` |
| `render_prompt` (курсовой пайплайн) — шаблон без плейсхолдеров | `ValueError` |
| `format_courses_context([])` | `"Похожие курсы не найдены."` |
| `format_courses_context([course])` | Содержит оценку в формате `0.NNN` |

---

### `src/services/recommendations.py`
_Файлы: `test_recommendations_filters.py`, `test_recommendation_service_utils.py`_

#### Фильтрация ресурсов
| Сценарий | Ожидаемый результат |
|----------|---------------------|
| `_resource_type_for_recommendation("cold")` через класс | `"article"` |
| `_resource_type_for_recommendation("hot")` через класс | `"course"` |
| `_resource_type_for_recommendation("warm"/"after_sale")` | `None` |
| `_build_resource_type_filter("article")` через класс | `Filter` с правильным `must` |
| `_build_resource_type_filter(None)` | `None` |

#### Нормализация типа рекомендации
| Сценарий | Ожидаемый результат |
|----------|---------------------|
| Известный тип строчными буквами | Тип возвращается как есть |
| Тип в верхнем регистре | Приводится к нижнему |
| Тип с дефисом (`after-sale`) | Заменяется на `after_sale` |
| Тип с пробелами по краям | Обрезается |
| `None` при `allow_empty=True` | `None` |
| `None` при `allow_empty=False` | `""` |
| Пустая строка при `allow_empty=True` | `None` |
| Пустая строка при `allow_empty=False` | `""` |
| Несуществующий тип | `ValidationError` |

#### Парсинг `lead_id`
| Сценарий | Ожидаемый результат |
|----------|---------------------|
| Целое число строкой | `int` |
| Число с пробелами по краям | Обрезается, затем парсится |
| `"0"` | `0` |
| Пустая строка | `ValidationError` |
| Только пробелы | `ValidationError` |
| Буквенная строка | `ValidationError` |
| Float-строка (`"12.5"`) | `ValidationError` |

#### Десериализация payload рекомендации
| Сценарий | Ожидаемый результат |
|----------|---------------------|
| Валидный JSON-словарь | Возвращается как есть |
| Вложенный словарь | Структура сохраняется |
| JSON-список | Оборачивается в `{"value": [...]}` |
| JSON-число | Оборачивается в `{"value": 42}` |
| Пустая строка | `{"text": ""}` |
| Только пробелы | `{"text": ""}` |
| Невалидный JSON (текст) | `{"text": <оригинальная строка>}` |

#### Подготовка текста для Mautic
| Сценарий | Ожидаемый результат |
|----------|---------------------|
| Длинный текст при `max_length=32` | Обрезается до 32 символов с `"..."` |

---

### `src/preprocessing/digital_footprints.py`
_Файл: `test_digital_footprints_profile.py`_

| Сценарий | Ожидаемый результат |
|----------|---------------------|
| Payload с `page_hit` (URL с русскими slug-ами) и `segment_membership_change` | Профиль содержит `lead_id`, топики из URL, название сегмента |
| Сегмент с цифровым кодом (`"931 Дошкольное образование"`) | Числовой код удаляется; тема сохраняется |
| URL на изображение `.gif` как заголовок страницы | Не попадает в топики профиля |

---

### `src/query_client/nats_client.py`
_Файл: `test_nats_client.py`_

| Сценарий | Ожидаемый результат |
|----------|---------------------|
| `connect()` вызван дважды | NATS-соединение создаётся один раз; стрим создаётся один раз |
| `publish_index(resource_id=42)` | Публикует в топик `tasks.rag.index` с корректным JSON |
| `subscribe(...)` | Передаёт правильный `ConsumerConfig` в `js.subscribe` |

---

### `src/workers/generate_worker.py`
_Файл: `test_generate_worker.py`_

| Сценарий | Ожидаемый результат |
|----------|---------------------|
| Устаревшая задача (Redis-статус отсутствует при mark_processing) | `msg.ack()` без ретрая |
| Временная ошибка генерации (timeout LLM) | `msg.nak(delay=...)` — retry |
| Невалидный JSON в сообщении | Немедленный `msg.ack()`, без mark_processing |
| Невалидный тип рекомендации (ValidationError при mark_processing) | `mark_failed` + `msg.ack()` |
| ValidationError при mark_failed с невалидным типом | Повторная попытка mark_failed с `type=None` |
| Успешная генерация задачи | mark_processing → generate → mark_completed → ack |

---

### `src/mauitc/activity_reader.py`
_Файл: `test_mauitc_activity_reader.py`_

| Сценарий | Ожидаемый результат |
|----------|---------------------|
| Список событий с фильтрацией по типу | Возвращаются только события нужного типа; нормализованы `activity_kind`, `entities` |
| Payload с событиями как маппинг (словарь по ID) | Обрабатывается как список |

---

---

## Интеграционные тесты

### `src/api/` — авторизация (JWT)
_Файл: `test_api_auth.py`_

Тесты используют `fastapi.testclient.TestClient` — реальный FastAPI-апп без сети и без внешних зависимостей.

| Сценарий | Ожидаемый результат |
|----------|---------------------|
| `POST /auth/key` с правильным секретом | 200 + поле `api-key` со значением |
| `GET /recommendations/status` без `Authorization` | 401 + `{"detail": "Missing API key."}` |

---

### `src/mauitc/` — клиент Mautic (живые вызовы)
_Файл: `test_mautic_client.py`_

Тесты обращаются к реальному Mautic API. Требуют настроенные `MAUTIC_*` переменные в `.env`.

| Сценарий | Ожидаемый результат |
|----------|---------------------|
| `get_contact_activity(lead_id)` | HTTP 200, payload содержит `events` |
| `find_contacts_by_email(email)` | HTTP 200, непустой словарь |
| `get_stages()` | Список словарей, не пустой |
| `get_contact_stage(contact_id)` и `get_contact_stage(email)` | Результаты по ID и по email совпадают |
| `get_contact_stage(email)` | `None` или `dict` |
| `get_emails()` | Список словарей email |
| `get_emails(email_id=29)` | Словарь с полем `id=29` и `clean_text` |

---

### `src/api/routers/` — эндпоинты API
_Файл: `test_rag_api_endpoints.py`_

Тесты используют `TestClient` с `monkeypatch` для изоляции сервисов. Зависимости от БД/Redis/Qdrant нет.

| Сценарий | Ожидаемый результат |
|----------|---------------------|
| `GET /staging-area/resources/type` | 200 со списком типов |
| `POST /staging-area/resources/type` с дубликатом | 409 Conflict |
| `GET /staging-area/{resource_id}` | 200 с полеями ресурса |
| `POST /staging-area` (индексация) | 202 с `resource_id` и запуском задачи |
| `POST /staging-area` с дубликатом | 409 Conflict |
| `POST /staging-area/email` | 200 со статусом импорта |
| `GET /recommendations/{lead_id}` | 200 со списком рекомендаций |
| `GET /recommendations/actions/{lead_id}` | 200 со списком действий лида |
| `GET /prompt?lead_type=cold` | 200 с полем `prompt` |
| `PUT /prompt` | 200 с обновлённым `prompt` |
| `POST /mautic/field` (мок) | 201 с полями поля |
| `GET /system/health` — все компоненты healthy | `status: "healthy"` |
| `GET /system/health` — один unhealthy | `status: "unhealthy"`, latency > 0 |
| `GET /system/health` — таймаут компонента | таймаут не зависает систему |
| `GET /vector-db/status` — есть активные задачи | `status: "updating"` |
| `GET /vector-db/status` — задач нет | `status: "ready"` |
| `GET /vector-db/status` — Redis недоступен | 503 |
| `GET /vector-db/resource-status/{id}` — ресурс в Qdrant | `status: "created"` |
| `GET /vector-db/resource-status/{id}` — индексация в процессе | `status: "processing"` |
| `GET /vector-db/resource-status/{id}?index=true` | запуск индексации, `status: "queued"` |
| `GET /recommendations/tasks/{lead_id}` | 200 со списком задач |
| `GET /recommendations/tasks/{lead_id}` — пусто хранилище | 200 + `tasks: []` |
| `GET /recommendations/tasks/{lead_id}` — Redis недоступен | 503 |
| `PATCH /mautic/field` (мок) | 200 с `status: "updated"` |
