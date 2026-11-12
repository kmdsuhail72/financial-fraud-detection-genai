.PHONY: help setup install venv lint format test clean run-backend run-frontend docker-up docker-down

PYTHON ?= python3
VENV ?= .venv

help:
	@echo "FinGuard AI - Developer Command Center"
	@echo "======================================"
	@echo "make setup          - Initialize virtualenv and install dependencies"
	@echo "make install        - Install python dependencies"
	@echo "make lint           - Run flake8, black check, and isort check"
	@echo "make format         - Auto-format code using black and isort"
	@echo "make test           - Run all unit, integration, and security tests"
	@echo "make docker-up      - Start local Postgres and dependencies"
	@echo "make docker-down    - Tear down local containers and volumes"
	@echo "make run-backend    - Start FastAPI backend locally"
	@echo "make run-frontend   - Start React frontend development server"
	@echo "make tf-validate    - Validate Terraform configurations"

venv:
	$(PYTHON) -m venv $(VENV)
	@echo "Virtual environment created at $(VENV)."

setup: venv install

install:
	$(VENV)/bin/python -m pip install --upgrade pip
	$(VENV)/bin/pip install -r backend/requirements.txt
	@if [ -f data_engineering/requirements.txt ]; then $(VENV)/bin/pip install -r data_engineering/requirements.txt; fi
	@if [ -f ml/requirements.txt ]; then $(VENV)/bin/pip install -r ml/requirements.txt; fi

lint:
	flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
	black --check .
	isort --check-only .

format:
	black .
	isort .

test:
	pytest tests/unit -v --cov=backend/app --cov=ml --cov=ingestion

test-all:
	pytest tests/ -v

docker-up:
	docker compose up -d

docker-down:
	docker compose down -v

run-backend:
	cd backend && uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

run-frontend:
	cd frontend && npm run dev

tf-validate:
	cd infrastructure/terraform/environments/dev && terraform init -backend=false && terraform validate

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".coverage" -delete
