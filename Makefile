.PHONY: test lint install

install:
	pip install -e ".[dev,meta]"

test:
	python -m pytest tests/ -v

lint:
	python -m ruff check .
	python -m ruff format --check .

format:
	python -m ruff check --fix .
	python -m ruff format .
