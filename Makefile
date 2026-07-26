.PHONY: build validate test lint all clean help

build:
	python3 scripts/build_berlin_data.py

validate:
	python3 validate/validate_schema.py

test:
	pytest tests/ -v

lint:
	ruff check scripts/ validate/ experiments/ tests/

all: build validate test lint

clean:
	rm -rf __pycache__ .pytest_cache .ruff_cache

help:
	@echo "make build|validate|test|lint|all|clean"
