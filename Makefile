# Makefile for VM Balancer project

# Variables
PACKAGE_NAME = vm-balancer
PYTHON = python3
PIP = pip3
VENV_DIR = .venv
SRC_DIR = src
DIST_DIR = dist
BUILD_DIR = build

# Colors for output
RED = \033[0;31m
GREEN = \033[0;32m
YELLOW = \033[1;33m
BLUE = \033[0;34m
NC = \033[0m

.PHONY: help install install-dev clean test lint format build upload upload-test check-dist setup-dev all

# Default target
help:
	@echo "$(BLUE)VM Balancer - Makefile Commands$(NC)"
	@echo ""
	@echo "$(GREEN)Setup:$(NC)"
	@echo "  make setup-dev      - Setup development environment"
	@echo "  make install        - Install package in current environment"
	@echo "  make install-dev    - Install package with dev dependencies"
	@echo ""
	@echo "$(GREEN)Development:$(NC)"
	@echo "  make clean          - Clean build artifacts and cache"
	@echo "  make test           - Run tests"
	@echo "  make lint           - Run linting (flake8, mypy)"
	@echo "  make format         - Format code (black, isort)"
	@echo "  make check          - Run all checks (lint + test)"
	@echo ""
	@echo "$(GREEN)Build & Deploy:$(NC)"
	@echo "  make build          - Build package for distribution"
	@echo "  make check-dist     - Check distribution files"
	@echo "  make upload-test    - Upload to TestPyPI"
	@echo "  make upload         - Upload to PyPI"
	@echo ""
	@echo "$(GREEN)Utilities:$(NC)"
	@echo "  make run            - Run the application"
	@echo "  make all            - Run format, lint, test, build"

# Setup development environment
setup-dev:
	@echo "$(YELLOW)Setting up development environment...$(NC)"
	$(PYTHON) -m venv $(VENV_DIR)
	$(VENV_DIR)/bin/pip install --upgrade pip setuptools wheel
	$(VENV_DIR)/bin/pip install -e .[dev,test]
	@echo "$(GREEN)Development environment ready!$(NC)"
	@echo "$(BLUE)Activate with: source $(VENV_DIR)/bin/activate$(NC)"

# Install package
install:
	@echo "$(YELLOW)Installing package...$(NC)"
	$(PIP) install -e .
	@echo "$(GREEN)Package installed!$(NC)"

# Install with development dependencies
install-dev:
	@echo "$(YELLOW)Installing package with dev dependencies...$(NC)"
	$(PIP) install -e .[dev,test]
	@echo "$(GREEN)Package with dev dependencies installed!$(NC)"

# Clean build artifacts
clean:
	@echo "$(YELLOW)Cleaning build artifacts...$(NC)"
	rm -rf $(BUILD_DIR)/
	rm -rf $(DIST_DIR)/
	rm -rf $(SRC_DIR)/*.egg-info/
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	rm -rf .coverage
	rm -rf htmlcov/
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	@echo "$(GREEN)Clean complete!$(NC)"

# Run tests
test:
	@echo "$(YELLOW)Running tests...$(NC)"
	$(PYTHON) -m pytest tests/ -v --tb=short
	@echo "$(GREEN)Tests completed!$(NC)"

# Run tests with coverage
test-cov:
	@echo "$(YELLOW)Running tests with coverage...$(NC)"
	$(PYTHON) -m pytest tests/ -v --cov=$(SRC_DIR)/vm_balancer --cov-report=html --cov-report=term
	@echo "$(GREEN)Tests with coverage completed!$(NC)"
	@echo "$(BLUE)Coverage report: htmlcov/index.html$(NC)"

# Run linting
lint:
	@echo "$(YELLOW)Running linting...$(NC)"
	@echo "$(BLUE)Running flake8...$(NC)"
	$(PYTHON) -m flake8 $(SRC_DIR)/vm_balancer tests/
	@echo "$(BLUE)Running mypy...$(NC)"
	$(PYTHON) -m mypy $(SRC_DIR)/vm_balancer
	@echo "$(GREEN)Linting completed!$(NC)"

# Format code
format:
	@echo "$(YELLOW)Formatting code...$(NC)"
	@echo "$(BLUE)Running isort...$(NC)"
	$(PYTHON) -m isort $(SRC_DIR)/vm_balancer tests/
	@echo "$(BLUE)Running black...$(NC)"
	$(PYTHON) -m black $(SRC_DIR)/vm_balancer tests/
	@echo "$(GREEN)Code formatting completed!$(NC)"

# Check code (lint + format check)
check:
	@echo "$(YELLOW)Running all checks...$(NC)"
	@echo "$(BLUE)Checking format with black...$(NC)"
	$(PYTHON) -m black --check $(SRC_DIR)/vm_balancer tests/
	@echo "$(BLUE)Checking import order with isort...$(NC)"
	$(PYTHON) -m isort --check-only $(SRC_DIR)/vm_balancer tests/
	@$(MAKE) lint
	@$(MAKE) test
	@echo "$(GREEN)All checks passed!$(NC)"

# Build package
build: clean
	@echo "$(YELLOW)Building package...$(NC)"
	$(PYTHON) -m build
	@echo "$(GREEN)Package built successfully!$(NC)"
	@echo "$(BLUE)Files created:$(NC)"
	@ls -la $(DIST_DIR)/

# Check distribution
check-dist: build
	@echo "$(YELLOW)Checking distribution...$(NC)"
	$(PYTHON) -m twine check $(DIST_DIR)/*
	@echo "$(GREEN)Distribution check completed!$(NC)"

# Upload to TestPyPI
upload-test: check-dist
	@echo "$(YELLOW)Uploading to TestPyPI...$(NC)"
	@echo "$(RED)Make sure you have configured your API token in ~/.pypirc$(NC)"
	$(PYTHON) -m twine upload --repository testpypi $(DIST_DIR)/*
	@echo "$(GREEN)Upload to TestPyPI completed!$(NC)"
	@echo "$(BLUE)Test installation with:$(NC)"
	@echo "pip install --index-url https://test.pypi.org/simple/ $(PACKAGE_NAME)"

# Upload to PyPI
upload: check-dist
	@echo "$(YELLOW)Uploading to PyPI...$(NC)"
	@echo "$(RED)Make sure you have configured your API token in ~/.pypirc$(NC)"
	@read -p "Are you sure you want to upload to PyPI? (y/N): " confirm && \
	if [ "$$confirm" = "y" ] || [ "$$confirm" = "Y" ]; then \
		$(PYTHON) -m twine upload $(DIST_DIR)/*; \
		echo "$(GREEN)Upload to PyPI completed!$(NC)"; \
		echo "$(BLUE)Install with: pip install $(PACKAGE_NAME)$(NC)"; \
	else \
		echo "$(YELLOW)Upload cancelled.$(NC)"; \
	fi

# Run the application
run:
	@echo "$(YELLOW)Running VM Balancer...$(NC)"
	$(PYTHON) -m vm_balancer

# Install build tools
install-build-tools:
	@echo "$(YELLOW)Installing build tools...$(NC)"
	$(PIP) install --upgrade pip setuptools wheel build twine
	@echo "$(GREEN)Build tools installed!$(NC)"

# Create release
release: all upload
	@echo "$(GREEN)Release process completed!$(NC)"

# Run all quality checks and build
all: format lint test build
	@echo "$(GREEN)All tasks completed successfully!$(NC)"

# Show package info
info:
	@echo "$(BLUE)Package Information:$(NC)"
	@echo "Name: $(PACKAGE_NAME)"
	@echo "Python: $(shell $(PYTHON) --version)"
	@echo "Pip: $(shell $(PIP) --version)"
	@if [ -f "$(SRC_DIR)/vm_balancer/__init__.py" ]; then \
		echo "Version: $(shell grep -E '^__version__' $(SRC_DIR)/vm_balancer/__init__.py | cut -d'"' -f2)"; \
	fi
	@echo "Source directory: $(SRC_DIR)"
	@echo "Distribution directory: $(DIST_DIR)"

# Show dependencies
deps:
	@echo "$(BLUE)Dependencies:$(NC)"
	$(PIP) list

# Update dependencies
update-deps:
	@echo "$(YELLOW)Updating dependencies...$(NC)"
	$(PIP) install --upgrade pip setuptools wheel
	$(PIP) install --upgrade -r requirements.txt
	@echo "$(GREEN)Dependencies updated!$(NC)"

# Commit hooks setup
setup-hooks:
	@echo "$(YELLOW)Setting up pre-commit hooks...$(NC)"
	$(PIP) install pre-commit
	pre-commit install
	@echo "$(GREEN)Pre-commit hooks installed!$(NC)"
