.PHONY: setup run test

setup:
	python3 -m venv .venv
	.venv/bin/pip install -r requirements-dev.txt

run:
	.venv/bin/uvicorn app.main:app --app-dir backend --reload

test:
	.venv/bin/python -m pytest
