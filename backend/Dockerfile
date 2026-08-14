# ── Stage 1: base ────────────────────────────────────────────────────────────
FROM python:3.11-slim AS base

WORKDIR /app

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ── Stage 2: development ──────────────────────────────────────────────────────
FROM base AS development

# Copy application source
COPY . .

EXPOSE 8000

# Run with reload for development
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# ── Stage 3: production (future) ──────────────────────────────────────────────
FROM base AS production

COPY . .

EXPOSE 8000

# Run without reload in production
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
