.PHONY: help install dev-install clean test lint format venv run-journey1 run-journey2 run-journey3 run-journey4

help:
	@echo "Jarvis Trading - Development Commands"
	@echo "===================================="
	@echo "  make venv              - Create virtual environment"
	@echo "  make install           - Install dependencies"
	@echo "  make dev-install       - Install with dev dependencies"
	@echo "  make clean             - Clean build artifacts"
	@echo "  make test              - Run tests"
	@echo "  make lint              - Run linters"
	@echo "  make format            - Format code with black"
	@echo "  make run-journey1      - Run Data Pipeline journey"
	@echo "  make run-journey2      - Run Feature Engineering journey"
	@echo "  make run-journey3      - Run MTF Combination journey"
	@echo "  make run-journey4      - Run RL Training journey"

venv:
	uv venv
	@echo "✓ Virtual environment created"

install: venv
	uv pip install -r requirements.txt
	@echo "✓ Dependencies installed"

dev-install: install
	uv pip install pytest pytest-cov black flake8 mypy isort
	@echo "✓ Dev dependencies installed"

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	@echo "✓ Build artifacts cleaned"

test:
	.venv/bin/pytest tests/ -v --cov=src --cov-report=html

lint:
	.venv/bin/flake8 src/ tests/ --count --statistics
	.venv/bin/mypy src/ --ignore-missing-imports

format:
	.venv/bin/black src/ tests/
	.venv/bin/isort src/ tests/

run-journey1:
	.venv/bin/python scripts/journey_1_data_pipeline.py

run-journey2:
	.venv/bin/python scripts/journey_2_feature_engineering.py

run-journey3:
	.venv/bin/python scripts/journey_3_mtf_combination.py

run-journey4:
	.venv/bin/python scripts/journey_4_rl_training.py
