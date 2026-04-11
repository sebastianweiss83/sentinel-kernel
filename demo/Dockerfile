# Sentinel demo container — built from the root of the repository.
#   docker compose -f demo/docker-compose.yml build
FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml README.md /app/
COPY sentinel /app/sentinel
COPY examples /app/examples
COPY demo /app/demo

RUN pip install --no-cache-dir -e ".[otel]"

ENV PYTHONUNBUFFERED=1

CMD ["python", "-u", "/app/demo/demo_app.py"]
