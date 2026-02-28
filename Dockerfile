FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY pyproject.toml .
COPY app/ app/
COPY ui/ ui/
COPY evals/ evals/
COPY start.sh .
COPY .env.example .env.example

# Create data directory for runtime
RUN mkdir -p data/observability

# Install Python dependencies
RUN pip install --no-cache-dir .

RUN chmod +x start.sh

# Railway uses PORT env var
EXPOSE 8501 8000

CMD ["./start.sh"]
