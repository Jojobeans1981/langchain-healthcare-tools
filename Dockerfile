# ---- Build stage: install dependencies ----
FROM python:3.12-slim AS builder

WORKDIR /build

COPY pyproject.toml .
RUN pip install --no-cache-dir --prefix=/install ".[server]"

# ---- Runtime stage: lean production image ----
FROM python:3.12-slim

WORKDIR /app

# Install only runtime system deps (curl for health checks)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy application code
COPY app/ app/
COPY ui/ ui/
COPY start.sh .
COPY .env.example .env.example

# Create data directory for runtime (SQLite, observability)
RUN mkdir -p data/observability && chmod +x start.sh

# Railway uses PORT env var
EXPOSE 8501 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["./start.sh"]
