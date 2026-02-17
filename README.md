# Personalized Educational Course Recommendation System (RAG-based)

## 📌 Описание проекта

Система генерации персонализированных рекомендаций учебных курсов на основе цифрового следа пользователей. Система использует RAG (Retrieval-Augmented Generation) подход для создания релевантных рекомендаций, анализируя поведение пользователей и семантическое сходство курсов.

## 🏗️ Архитектура проекта

```
├── src/
│   ├── rag_core/              # Ядро RAG-системы
│   ├── cli/                   # CLI-клиент (Click)
│   ├── database/              # PostgreSQL + SQLAlchemy ORM
│   ├── vector_db/             # Qdrant интеграция
│   ├── api_client/            # Асинхронный клиент для LLM API
│   ├── preprocessing/         # Модули препроцессинга и чанкирования
│   ├── api/                   # FastAPI слой
│   ├── config/                # Конфигурация приложения
│   ├── prompts/               # Системные промпты для LLM
│   └── utils/                 # Вспомогательные утилиты (логирование и т.д.)
├── data/                      # Mock данные для тестирования при разработке
├── tests/                     # Тесты
├── docs/                      # Документация
├── docker-compose.yml         # Docker Compose конфигурация
├── pyproject.toml             # Единый конфиг Ruff/mypy и метаданные проекта
├── .pre-commit-config.yaml    # Конфигурация pre-commit хуков
└── .env.example               # Шаблон переменных окружения
```

## 🛠️ Технологический стек

- Python 3.12+
- Qdrant
- PostgreSQL
- Docker
- Click CLI
- FastAPI

## 🗄️ Структура базы данных

### `users`

```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    login VARCHAR(150) UNIQUE,
    digital_footprints TEXT,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
```

### `recommendations`

```sql
CREATE TABLE recommendations (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    text VARCHAR(1000),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
```

### `courses`

```sql
CREATE TABLE courses (
    id SERIAL PRIMARY KEY,
    name VARCHAR(150),
    description TEXT
);
```

## Структура Qdrant

- **Коллекция**: `courses_chunks`
- **Тип**: Хранение чанков описаний курсов в виде векторов
- **Метрика расстояния**: Cosine similarity

## 🚀 Быстрый старт

### Предварительные требования

- Docker и Docker Compose
- Python 3.12+ (для локальной разработки)
- Git

### Установка через Docker

1. Клонируйте репозиторий:

```bash
git clone <repository-url>
cd <project-directory>
```

2. Создайте файл `.env` на основе `.env.example`:

```bash
cp .env.example .env
```

3. Запустите приложение:

```bash
docker compose up -d postgresql qdrant
```

4. Проверьте работу контейнеров:

```bash
docker compose ps
```

## 📚 Документация

- `docs/CLI.md` — команды и сценарии CLI
- `docs/API.md` — запуск API и описание эндпоинтов

## 🔧 Конфигурация

```env
# Database
POSTGRES_HOST=
POSTGRES_PORT=
POSTGRES_DB=
POSTGRES_USER=
POSTGRES_PASSWORD=

# Qdrant
QDRANT_HOST=
QDRANT_PORT=
QDRANT_GRPC_PORT=
QDRANT_COLLECTION=

# LLM API
LLM_API_URL=
LLM_API_KEY=
LLM_MODEL=

# Embedding API
EMBEDDING_MODEL_API_URL=
EMBEDDING_MODEL_API_KEY=
EMBEDDING_MODEL=
EMBEDDING_VECTOR_SIZE=

# Timeouts
API_TIMEOUT_SECONDS=

# Application
LOG_LEVEL=INFO
ENVIRONMENT=development
```

## 🔍 Качество кода

```bash
# Запуск Ruff для форматирования и линтинга
python -m ruff check --fix src/ tests/
python -m ruff format src/ tests/

# Проверка типов с mypy
python -m mypy src tests

# Запуск всех pre-commit хуков
python -m pre_commit run --all-files
```

## 📊 Рабочий процесс RAG

1. **Препроцессинг данных**:
    - Загрузка описаний курсов из JSON в PostgreSQL
    - Чанкирование текста на семантически значимые части
    - Генерация эмбеддингов для каждого чанка
    - Сохранение в Qdrant

2. **Генерация рекомендаций**:
    - Получение цифрового следа пользователя
    - Семантический поиск релевантных чанков курсов в Qdrant
    - Формирование контекста для LLM
    - Генерация персонализированных рекомендаций через LLM API
    - Сохранение рекомендаций в PostgreSQL

### Структура коммитов

```
feat: добавление новой функциональности
fix: исправление ошибок
docs: обновление документации
style: изменения форматирования (без влияния на логику)
refactor: рефакторинг кода
test: добавление или исправление тестов
chore: обновление зависимостей, конфигураций
```