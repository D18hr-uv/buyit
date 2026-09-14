FROM python:3.11-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

# Seed only if the DB is empty (non-destructive), then launch the API.
# $PORT is provided by the host (e.g. Render); defaults to 8000 locally.
CMD ["sh", "-c", "python -m app.db.ensure_seed && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
