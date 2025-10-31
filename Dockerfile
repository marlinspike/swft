FROM python:3.11-slim as base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /srv

COPY backend/pyproject.toml backend/setup.cfg ./backend/
RUN python -m ensurepip --upgrade && \
    pip install --upgrade pip

COPY backend/app ./backend/app
RUN pip install ./backend

EXPOSE 8000

WORKDIR /srv/backend

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
