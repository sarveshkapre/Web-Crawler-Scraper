.PHONY: help install-dev lint test smoke

help:
	@echo "Targets:"
	@echo "  install-dev  Install package + dev deps (ruff/pytest)"
	@echo "  lint         Run ruff"
	@echo "  test         Run pytest"
	@echo "  smoke        Run a local crawler smoke test"

install-dev:
	python3 -m pip install -e '.[dev]'

lint:
	python3 -m ruff check .

test:
	python3 -m pytest

smoke:
	python3 scripts/smoke_local.py
