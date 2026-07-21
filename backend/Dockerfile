# ──────────────────────────────────────────────────────────────────
# Stage 1: base — shared Python environment
# ──────────────────────────────────────────────────────────────────
FROM python:3.12-slim AS base

# System dependencies for psycopg2, ReportLab, and PDF generation
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Non-root user for security
RUN groupadd -r appuser && useradd -r -g appuser appuser

WORKDIR /app

# Copy and install Python dependencies first (layer cache optimization)
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# ──────────────────────────────────────────────────────────────────
# Stage 2: development — includes dev tools, hot-reload
# ──────────────────────────────────────────────────────────────────
FROM base AS development

COPY requirements-dev.txt .
RUN pip install --no-cache-dir -r requirements-dev.txt

# Create storage directories
RUN mkdir -p /app/storage/uploads /app/storage/reports \
    && chown -R appuser:appuser /app/storage

# Switch to non-root
USER appuser

# Source code is mounted as a volume in dev
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# ──────────────────────────────────────────────────────────────────
# Stage 3: production — minimal image, no dev tools
# ──────────────────────────────────────────────────────────────────
FROM base AS production

# Copy application source
COPY --chown=appuser:appuser app/ ./app/
COPY --chown=appuser:appuser alembic.ini .
COPY --chown=appuser:appuser docker-entrypoint.sh .
RUN chmod +x docker-entrypoint.sh

# Create storage directories
RUN mkdir -p /app/storage/uploads /app/storage/reports \
    && chown -R appuser:appuser /app/storage

# Switch to non-root
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

ENTRYPOINT ["./docker-entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
