.PHONY: help install-dev lint test

help:
	@echo "Targets:"
	@echo "  install-dev  Install package + dev deps (ruff/pytest)"
	@echo "  lint         Run ruff"
	@echo "  test         Run pytest"

install-dev:
	python3 -m pip install -e '.[dev]'

lint:
	python3 -m ruff check .

test:
	python3 -m pytest
