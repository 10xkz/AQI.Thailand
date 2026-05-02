# ── Build stage: install deps ────────────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /build

# ติดตั้งเครื่องมือพื้นฐานสำหรับ PostgreSQL
RUN apt-get update && apt-get install -y libpq-dev gcc && rm -rf /var/lib/apt/lists/*

# Install dependencies into an isolated prefix so we can copy them cleanly
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt


# ── Runtime stage ────────────────────────────────────────────────────────────
FROM python:3.12-slim AS runtime

LABEL maintainer="pm25-monitor"
LABEL description="Thailand PM2.5 FastAPI backend — with PostgreSQL database"

# ติดตั้งไลบรารีรันไทม์ให้ PostgreSQL
RUN apt-get update && apt-get install -y libpq5 && rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Create a non-root user for security
RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser

WORKDIR /app
COPY main.py .

# Own the working directory
RUN chown -R appuser:appgroup /app

USER appuser

# Uvicorn listens on 8000 inside the container
EXPOSE 8000

# Healthcheck — Docker / Compose will mark the container healthy after this passes
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]