.PHONY: help venv install lint test api docker-up docker-down clean-venv

VENV_DIR := venv
PYTHON := $(VENV_DIR)/bin/python
PIP := $(PYTHON) -m pip

help:
	@echo "  venv        - создать виртуальное окружение (если ещё нет)"
	@echo "  install     - создать venv + установить все зависимости"
	@echo "  lint        - запустить линтеры"
	@echo "  test        - запустить тесты"
	@echo "  api         - запустить API"
	@echo "  docker-up   - поднять docker контейнеры"
	@echo "  docker-down - остановить docker контейнеры"
	@echo "  clean-venv  - полностью удалить venv"


$(VENV_DIR)/bin/python:
	python3 -m venv $(VENV_DIR)
	@echo "Virtual environment created in $(VENV_DIR)"

venv: $(VENV_DIR)/bin/python


install lint test api: $(VENV_DIR)/bin/python

install:
	$(PIP) install -r requirements.txt -r requirements-dev.txt

lint:
	$(PYTHON) -m ruff check src tests
	$(PYTHON) -m ruff format --check src tests
	$(PYTHON) -m mypy src tests

test:
	$(PYTHON) -m pytest -q

api:
	$(PYTHON) -m src.api

docker-up:
	docker compose up -d

docker-down:
	docker compose down

clean-venv:
	rm -rf $(VENV_DIR)
	@echo "Virtual environment removed"