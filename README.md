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
│   ├── api/                   # FastAPI приложение (заглушка)
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

## 🗄️ Структура базы данных

### `users`

```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    login VARCHAR(150),
    digital_footprints TEXT,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
```

### `recommendations`

```sql
CREATE TABLE recommendations (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    text VARCHAR(300),
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
docker-compose up -d
```

4. Проверьте работу контейнеров:

```bash
docker-compose ps
```

## 📖 Использование CLI

### Основные команды

```bash
# Инициализировать таблицы через SQLAlchemy ORM
python -m src.cli init-db

# Пересоздать схему (удалит существующие таблицы)
python -m src.cli init-db --drop-existing

# Заполнить таблицу courses из JSON
python -m src.cli seed-courses --file data/courses.json

# Создать пользователя
python -m src.cli create-user --login roman --digital-footprints '{"events":[]}'

# Добавить рекомендацию пользователю
python -m src.cli add-recommendation --login roman --text "Начните с курса по Python"

# Просмотр данных
python -m src.cli show-users
python -m src.cli show-courses
python -m src.cli show-recommendations --login roman
```

### Полный список команд

```bash
python -m src.cli --help
```

## 🔧 Конфигурация

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

## 🔍 Качество кода

```bash
# Запуск Ruff для форматирования и линтинга
ruff check --fix src/ tests/
ruff format src/ tests/

# Проверка типов с mypy
mypy

# Запуск всех pre-commit хуков
pre-commit run --all-files
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

1. **API Layer**: Реализация полноценного FastAPI приложения для взаимодействия с системой.
2. **Мониторинг**: Интеграция с Prometheus и Grafana.
3. **ML Pipeline**: Автоматическое обновление эмбеддингов курсов.