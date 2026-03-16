FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev && \
    rm -rf /var/lib/apt/lists/*

COPY pyproject.toml .
RUN pip install --no-cache-dir . || true

COPY . .
RUN pip install --no-cache-dir .

ENV PYTHONPATH=/app

RUN chmod +x start.sh

EXPOSE 8000

CMD ["./start.sh"]
