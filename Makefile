# musicvideo-generator Makefile

.PHONY: build run test lint clean docker-build docker-run

DOCKER_IMAGE := musicvideo-generator
PROJECT_DIR  ?= ./projects/demo

# ── Local development ──────────────────────────────────────────────────────────

install:
	pip install -e ".[dev]" 2>/dev/null || pip install -r requirements.txt && pip install -e .

lint:
	ruff check src tests

test:
	pytest tests/ --cov=mvgen --cov-report=term-missing

run:
	mvgen run $(PROJECT_DIR)

# ── Docker ─────────────────────────────────────────────────────────────────────

docker-build:
	docker build -t $(DOCKER_IMAGE) .

docker-run:
	docker compose run --rm mvgen run /data/$(notdir $(PROJECT_DIR))

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete
	rm -rf .pytest_cache .coverage htmlcov dist build *.egg-info
