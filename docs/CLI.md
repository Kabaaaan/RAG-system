# CLI

## Обзор

CLI предназначен для инициализации БД, загрузки данных и генерации рекомендаций.

## Установка

```bash
python -m pip install -r requirements.txt -r requirements-dev.txt
```

## Команды

```bash
# Инициализировать таблицы через SQLAlchemy ORM
python -m src.cli init-db

# Пересоздать схему (удалит существующие таблицы)
python -m src.cli init-db --drop-existing

# Заполнить таблицу users из digital-footprints.json (create/update)
python -m src.cli seed-users --file data/digital-footprints.json

# Создать пользователя
python -m src.cli create-user --login roman --digital-footprints '{"events":[]}'

# Добавить рекомендацию пользователю
python -m src.cli add-recommendation --login roman --text "Начните с курса по Python"

# Сгенерировать рекомендацию через RAG 
python -m src.cli generate_recommendation --login alex_dev

# Просмотр данных
python -m src.cli show-users
python -m src.cli show-courses
python -m src.cli show-recommendations --login roman
```

## Полный список команд

```bash
python -m src.cli --help
```

## Рекомендуемый MVP-сценарий

```bash
# 1) Инициализация схемы + сид курсов из data/courses.json + индексация в Qdrant
python -m src.cli init-db --drop-existing

# 2) Сид пользователей из цифровых следов
python -m src.cli seed-users --file data/digital-footprints.json

# 3) Генерация рекомендации для конкретного пользователя
python -m src.cli generate_recommendation --login alex_dev
```
