# Helios A2 continuous collector — runs the shadow-mode loop 24/7 in the cloud.
#
# Minimal dependencies — only what scripts.a2_run_continuous + its imports need.
# (Does NOT install xgboost / scipy / sklearn / fastapi — those are for other
# strategies and would slow the build by minutes for no runtime benefit.)

FROM python:3.12-slim

WORKDIR /app

# Build deps for native wheels (polars, duckdb, pyarrow, numpy)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc curl \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir --upgrade pip

# Pin runtime deps — keep this list tight. Install pyarrow first since it's the
# slowest wheel; failing fast helps debug.
RUN pip install --no-cache-dir \
    "pydantic>=2.7" \
    "loguru>=0.7" \
    "anyio>=4.4" \
    "httpx>=0.27" \
    "orjson>=3.10" \
    "numpy>=1.26" \
    "polars>=1.0" \
    "duckdb>=1.0" \
    "pyarrow>=16" \
    "python-dotenv>=1.0" \
    "websockets>=12" \
    "solders>=0.21" \
    "base58>=2.1"

# Copy only what the A2 collector needs (excludes legacy backend, frontend, etc.)
COPY helios /app/helios
COPY scripts /app/scripts
COPY pyproject.toml /app/

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONPATH=/app

# Logs go to /data/logs so a Railway volume mounted at /data persists them.
# IMPORTANT: do NOT symlink /app/logs -> /data/logs. The runtime volume mount
# replaces the build-time /data, leaving any symlink dangling, which causes
# Python's mkdir(exist_ok=True) to raise FileExistsError. Instead, point the
# code at the absolute path via env vars.
ENV HELIOS_LOGS_DIR=/data/logs
ENV HELIOS_LOG_JSON=/data/logs/helios.jsonl
RUN mkdir -p /data/logs

# Smoke-check the import path on build so we fail fast if Python pathing is wrong.
RUN python -c "from helios.strategies.a2_meme_snipe.enricher import SnapshotEnricher; print('helios imports OK')"

CMD ["python", "-m", "scripts.a2_run_continuous"]
