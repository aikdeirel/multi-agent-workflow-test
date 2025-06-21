# Multi-Agent System Makefile
.PHONY: help test test-unit test-integration test-fast test-cov clean install lint format

# Default target
help:
	@echo "Multi-Agent System - Available Commands:"
	@echo ""
	@echo "Testing:"
	@echo "  test          - Run all tests"
	@echo "  test-unit     - Run unit tests only"
	@echo "  test-integration - Run integration tests only" 
	@echo "  test-fast     - Run tests excluding slow ones"
	@echo "  test-cov      - Run tests with coverage report"
	@echo "  test-cov-html - Run tests with HTML coverage report"
	@echo ""
	@echo "Development:"
	@echo "  install       - Install dependencies"
	@echo "  lint          - Run linting checks"
	@echo "  format        - Format code"
	@echo "  clean         - Clean generated files"
	@echo ""
	@echo "Examples:"
	@echo "  make test-unit"
	@echo "  make test-cov-html"

# Testing targets
test:
	cd src && python -m pytest ../tests/ -v

test-unit:
	cd src && python -m pytest ../tests/ -m unit -v

test-integration:
	cd src && python -m pytest ../tests/ -m integration -v

test-fast:
	cd src && python -m pytest ../tests/ -m "not slow" -v

test-cov:
	cd src && python -m pytest ../tests/ --cov=. --cov-report=term-missing --cov-fail-under=85

test-cov-html:
	cd src && python -m pytest ../tests/ --cov=. --cov-report=html --cov-report=term-missing
	@echo "Coverage report generated in src/htmlcov/index.html"

test-parallel:
	cd src && python -m pytest ../tests/ -n auto -v

# Development targets
install:
	cd src && pip install -r requirements.txt

lint:
	cd src && python -m flake8 . --max-line-length=88 --extend-ignore=E203,W503
	cd src && python -m black --check .
	cd src && python -m isort --check-only .

format:
	cd src && python -m black .
	cd src && python -m isort .

# Cleanup
clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -rf src/htmlcov/
	rm -rf src/.coverage
	rm -rf src/.pytest_cache/
	rm -rf .coverage.*

# Quick development workflow
dev-setup: install
	@echo "Development environment set up successfully!"
	@echo "Run 'make test' to run all tests"

# CI/CD targets
ci-test:
	cd src && python -m pytest ../tests/ --cov=. --cov-report=xml --cov-fail-under=85 --junitxml=test-results.xml

# Security checks
security:
	cd src && python -m bandit -r . -f json -o bandit-report.json || true
	cd src && python -m safety check --json || true

# Docker targets (if needed)
docker-test:
	docker-compose -f docker-compose.yml -f docker-compose.test.yml run --rm test

# Documentation
docs:
	@echo "Opening test documentation..."
	@echo "See tests/README.md for comprehensive testing guide"