# Penaltyblog Development Makefile

.PHONY: help setup install install-dev clean test lint format check demo docs

# Default target
help:
	@echo "Available commands:"
	@echo "  setup         - Complete development environment setup"
	@echo "  install       - Install package in development mode"
	@echo "  install-dev   - Install with development dependencies"
	@echo "  test          - Run all tests"
	@echo "  lint          - Run linting with ruff"
	@echo "  format        - Format code with black"
	@echo "  check         - Run all code quality checks"
	@echo "  demo          - Run the demo pipeline"
	@echo "  clean         - Clean build artifacts"
	@echo "  docs          - Build documentation"

# Complete setup for new environment
setup:
	@echo "🔧 Setting up penaltyblog development environment..."
	python3 -m venv venv
	venv/bin/pip install --upgrade pip setuptools wheel
	venv/bin/pip install -e ".[dev]"
	venv/bin/pip install ruff mypy black pytest
	@echo "✅ Setup complete! Activate with: source venv/bin/activate"

# Install package in development mode
install:
	pip install -e .

# Install with development dependencies
install-dev:
	pip install -e ".[dev]"
	pip install ruff mypy black pytest

# Run tests
test:
	pytest test/ -v

# Run quick tests
test-quick:
	pytest test/ -q

# Run linting
lint:
	ruff check penaltyblog/
	mypy penaltyblog/ --ignore-missing-imports

# Format code
format:
	black penaltyblog/ test/ examples/
	ruff check penaltyblog/ --fix

# Run all quality checks
check: format lint test-quick

# Run the demo pipeline
demo:
	python -m examples.demo_pipeline

# Clean build artifacts
clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -name "*.pyc" -delete

# Build documentation
docs:
	cd docs && make html

# Build package
build: clean
	python -m build

# Upload to PyPI (requires authentication)
upload: build
	python -m twine upload dist/*
