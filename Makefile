.PHONY: help install test test-cov run dev docker-build docker-run docker-test clean

# Default target
help:
	@echo "OCRion API - Available commands:"
	@echo ""
	@echo "  install      - Install dependencies with uv"
	@echo "  test         - Run unit tests"
	@echo "  test-cov     - Run tests with coverage report"
	@echo "  run          - Run production server"
	@echo "  dev          - Run development server with hot-reload"
	@echo "  docker-build - Build Docker image"
	@echo "  docker-run   - Run Docker container"
	@echo "  docker-test  - Run tests in Docker"
	@echo "  clean        - Clean Python cache and build artifacts"

# Installation
install:
	@echo "Installing dependencies with uv..."
	uv pip install -r requirements.txt

# Testing
test:
	@echo "Running unit tests..."
	source .venv/bin/activate && \
		export OPENROUTER_API_KEY=test_key_12345 && \
		export MODEL_NAME=test/model && \
		export OCR_USE_GPU=false && \
		pytest tests/test_unit_isolated.py tests/test_schemas.py -v

test-cov:
	@echo "Running tests with coverage..."
	source .venv/bin/activate && \
		export OPENROUTER_API_KEY=test_key_12345 && \
		export MODEL_NAME=test/model && \
		export OCR_USE_GPU=false && \
		pytest tests/test_unit_isolated.py tests/test_schemas.py -v --cov=app --cov-report=html --cov-report=term-missing

test-all:
	@echo "Running all tests including integration..."
	source .venv/bin/activate && \
		export OPENROUTER_API_KEY=test_key_12345 && \
		export MODEL_NAME=test/model && \
		export OCR_USE_GPU=false && \
		pytest tests/ -v -m "not integration"

# Running
run:
	@echo "Starting production server..."
	./start.sh

dev:
	@echo "Starting development server..."
	source .venv/bin/activate && \
		uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Docker
docker-build:
	@echo "Building Docker image..."
	docker build -t ocrion:latest .

docker-run:
	@echo "Running Docker container..."
	docker run -p 8000:8000 \
		-e OPENROUTER_API_KEY=$(OPENROUTER_API_KEY) \
		-e MODEL_NAME=$(MODEL_NAME) \
		-e OCR_USE_GPU=false \
		ocrion:latest

docker-test:
	@echo "Running tests in Docker..."
	./test_docker.sh

docker-compose-up:
	@echo "Starting with docker-compose..."
	docker-compose up -d

docker-compose-down:
	@echo "Stopping docker-compose..."
	docker-compose down

# Utilities
clean:
	@echo "Cleaning cache and artifacts..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	rm -rf htmlcov/ .coverage 2>/dev/null || true
	@echo "Clean complete"

format:
	@echo "Formatting code with black..."
	source .venv/bin/activate && \
		pip install black 2>/dev/null || true && \
		black app/ tests/

lint:
	@echo "Linting code..."
	source .venv/bin/activate && \
		pip install ruff 2>/dev/null || true && \
		ruff check app/ tests/

setup: install
	@echo "Setting up environment..."
	@echo "Please create a .env file with your OPENROUTER_API_KEY"
	@if [ ! -f .env ]; then \
		cp .env.example .env; \
		echo "Created .env from .env.example - please edit it"; \
	fi

# Create test image
test-image:
	@echo "Creating test invoice image..."
	source .venv/bin/activate && \
		python create_test_image.py
