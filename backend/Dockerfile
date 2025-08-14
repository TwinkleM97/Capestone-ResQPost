# --- Base image ---
FROM python:3.11-slim

# Prevent Python from writing .pyc files & make logs unbuffered
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# System deps (Postgres client headers, build tools, curl for HEALTHCHECK)
RUN apt-get update && apt-get install -y --no-install-recommends \
      gcc \
      libpq-dev \
      curl \
    && rm -rf /var/lib/apt/lists/*

# --- Python deps layer (cache-friendly) ---
# Copy only requirements first to maximize Docker layer caching
COPY requirements.txt ./requirements.txt
# Optional: upgrade pip to a modern version
RUN python -m pip install --upgrade pip \
 && pip install -r requirements.txt
# If you plan to serve via Gunicorn (recommended), make sure 'gunicorn' is in requirements.txt

# --- App code ---
COPY . .

# Drop root for better security
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 5000

# Basic container health check (tweak path if you have /health)
HEALTHCHECK --interval=30s --timeout=5s --retries=5 CMD curl -fsS http://127.0.0.1:5000/ >/dev/null || exit 1

# Use Gunicorn in prod; ensure `app:app` points to your Flask instance
# If you don't have gunicorn in requirements.txt yet, either add it OR
# temporarily switch the CMD to: ["python", "app.py"]
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "app:app"]
