# Personalized Educational Course Recommendation System (RAG-based)

## 📌 Project Overview

Система генерации персонализированных рекомендаций учебных курсов на основе цифрового следа пользователей. Система использует RAG (Retrieval-Augmented Generation) подход для создания релевантных рекомендаций, анализируя поведение пользователей и семантическое сходство курсов.

## 🏗️ Архитектура проекта

```
├── src/
│   ├── rag_core/              # Ядро RAG-системы
│   ├── cli/                   # CLI-клиент (Click)
│   ├── database/              # PostgreSQL + SQLAlchemy ORM
│   │   ├── models.py          # Модели БД
│   │   └── repositories.py    # Репозитории для работы с БД
│   ├── vector_db/             # Qdrant интеграция
│   ├── api_client/            # Асинхронный клиент для LLM API
│   ├── preprocessing/         # Модули препроцессинга и чанкирования
│   ├── api/                   # FastAPI приложение (заглушка)
│   ├── config/                # Конфигурация приложения
│   ├── prompts/               # Системные промпты для LLM
│   └── utils/                 # Вспомогательные утилиты (логирование и т.д.)
├── tests/                     # Тесты
├── docs/                      # Документация
├── migrations/                # Миграции БД
├── docker-compose.yml         # Docker Compose конфигурация
├── pyproject.toml             # Единый конфиг Ruff/mypy и метаданные проекта
├── .pre-commit-config.yaml    # Конфигурация pre-commit хуков
├── .env.example               # Шаблон переменных окружения
└── .env.dev                   # Локальная dev-конфигурация окружения
```

## 🛠️ Технологический стек

- **Python 3.10+**
- **RAG Core**: Семантический поиск и генерация рекомендаций
- **Vector Database**: Qdrant для хранения векторных представлений курсов
- **Relational Database**: PostgreSQL для хранения пользователей и рекомендаций
- **ORM**: SQLAlchemy 2.0+
- **CLI Framework**: Click
- **API Framework**: FastAPI (Будет реализован позже)
- **HTTP Client**: httpx (асинхронный)
- **Code Quality**: pre-commit, Ruff, mypy
- **Containerization**: Docker, Docker Compose

## 🗄️ Структура базы данных

### PostgreSQL Tables

#### `users`
```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    digital_footprints TEXT,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
```

#### `recommendations`
```sql
CREATE TABLE recommendations (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    text VARCHAR(300),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
```

#### `courses`
```sql
CREATE TABLE courses (
    id SERIAL PRIMARY KEY,
    description TEXT
);
```

### Qdrant Collection

- **Collection Name**: `courses_chunks`
- **Type**: Хранение чанков описаний курсов в виде векторов
- **Distance Metric**: Cosine similarity

## 🚀 Быстрый старт

### Предварительные требования

- Docker и Docker Compose
- Python 3.10+ (для локальной разработки)
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
docker-compose up -d
```

4. Проверьте работу контейнеров:
```bash
docker-compose ps
```


## 📖 Использование CLI

### Основные команды

```bash
Опишу позже
```

### Полный список команд

```bash
python -m src.cli --help
```

## 🔧 Конфигурация

### Переменные окружения (.env)

```env
# Database
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=rag_recommendations
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres

# Qdrant
QDRANT_HOST=localhost
QDRANT_PORT=6333
QDRANT_COLLECTION=courses_chunks

# LLM API
LLM_API_URL=https://api.llm-provider.com/v1
LLM_API_KEY=your_api_key_here
EMBEDDING_MODEL=text-embedding-ada-002

# Application
LOG_LEVEL=INFO
ENVIRONMENT=development
```

### Структура конфигурационного класса

```python
# src/config/settings.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Настройки БД
    postgres_host: str
    postgres_port: int
    # ... остальные настройки
```


## 🔍 Code Quality Tools

### Pre-commit хуки

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.1.6
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.7.0
    hooks:
      - id: mypy
```

### Проверка кода

```bash
# Запуск Ruff для форматирования и линтинга
ruff check --fix src/ tests/
ruff format src/ tests/

# Проверка типов с mypy
mypy

# Запуск всех pre-commit хуков
pre-commit run --all-files
```

## 🐳 Docker Compose сервисы

```yaml
version: '3.8'

services:
  postgresql:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: rag_recommendations
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  qdrant:
    image: qdrant/qdrant:latest
    ports:
      - "6333:6333"
      - "6334:6334"
    volumes:
      - qdrant_data:/qdrant/storage

  rag-app:
    build: .
    depends_on:
      - postgresql
      - qdrant
    environment:
      - ENVIRONMENT=production
    ports:
      - "8000:8000"
    volumes:
      - .:/app

  backend-app:
    build:
      context: .
    ports:
      - "8080:8080"
    depends_on:
      - rag-app

volumes:
  postgres_data:
  qdrant_data:
```

## 📊 Рабочий процесс RAG

1. **Препроцессинг данных**:
   - Загрузка описаний курсов из PostgreSQL
   - Чанкирование текста на семантически значимые части
   - Генерация эмбеддингов для каждого чанка
   - Сохранение в Qdrant

2. **Генерация рекомендаций**:
   - Получение цифрового следа пользователя
   - Семантический поиск релевантных чанков курсов в Qdrant
   - Формирование контекста для LLM
   - Генерация персонализированных рекомендаций через LLM API
   - Сохранение рекомендаций в PostgreSQL

## 🔄 Разработка

### Установка для разработки

```bash
# 1. Клонируйте репозиторий
git clone <repo-url>
cd <project-name>

# 2. Создайте виртуальное окружение
python -m venv venv
source venv/bin/activate  # Linux/Mac
# или
venv\Scripts\activate  # Windows

# 3. Установите зависимости
pip install -r requirements.txt
pip install -r requirements-dev.txt

# 4. Настройте pre-commit
pre-commit install

# 5. Запустите инфраструктуру
docker-compose up -d postgresql qdrant

# 6. Запустите миграции и инициализацию
python -m src.cli init-db
python -m src.cli init-vector-db
```

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

## 📈 Планы развития

1. **API Layer**: Реализация полноценного FastAPI приложения
2. **Мониторинг**: Интеграция с Prometheus и Grafana
3. **ML Pipeline**: Автоматическое обновление эмбеддингов курсов



**Примечание**: Это README будет обновляться по мере развития проекта. Актуальная информация всегда доступна в документации кода и комментариях.
