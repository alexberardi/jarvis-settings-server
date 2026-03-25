FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl git \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies from pyproject.toml (includes jarvis client libs)
COPY pyproject.toml .
COPY app/ ./app/
RUN pip install --no-cache-dir .

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:7708/health || exit 1

EXPOSE 7708

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7708"]
