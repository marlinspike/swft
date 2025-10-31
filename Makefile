.PHONY: backend-install backend-test backend-serve frontend-install frontend-dev frontend-build lint

backend-install:
	cd backend && python -m pip install -e .[dev]

backend-test:
	cd backend && python -m pytest

backend-serve:
	cd backend && uvicorn app.main:app --reload --port 8000

frontend-install:
	cd frontend && npm install

frontend-dev:
	cd frontend && npm run dev

frontend-build:
	cd frontend && npm run build

lint:
	ruff check backend/app
