# ARIA Backend Dockerfile
# Multi-stage build with Oracle Instant Client (ARM64 + AMD64)

# ── Builder Stage ─────────────────────────────────────────────────────
FROM python:3.12-slim-bookworm AS builder

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies (cache-friendly layer)
RUN uv sync --no-dev --no-editable

# spaCy lemmatizer model for mem0 2.x hybrid retrieval. The model is not on PyPI,
# so install the wheel matching the locked spaCy 3.8.x directly into the venv
# (avoids a fragile runtime `spacy download`). Lands in /app/.venv → copied to runtime.
RUN uv pip install --python /app/.venv/bin/python \
    "en_core_web_sm @ https://github.com/explosion/spacy-models/releases/download/en_core_web_sm-3.8.0/en_core_web_sm-3.8.0-py3-none-any.whl"

# ── Oracle Instant Client Stage ───────────────────────────────────────
FROM python:3.12-slim-bookworm AS oracle-client

ARG TARGETARCH

# Download Oracle Instant Client based on architecture
# ARM64: aarch64, AMD64: x86_64
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl unzip ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && mkdir -p /opt/oracle

# Oracle Instant Client 23.6 (latest as of 2024)
# Download URLs differ by architecture
RUN if [ "$TARGETARCH" = "arm64" ]; then \
        echo "Downloading Oracle Instant Client for ARM64..." && \
        curl -fSL "https://download.oracle.com/otn_software/linux/instantclient/2360000/instantclient-basic-linux.arm64-23.6.0.24.10.zip" \
            -o /tmp/instantclient.zip; \
    else \
        echo "Downloading Oracle Instant Client for AMD64..." && \
        curl -fSL "https://download.oracle.com/otn_software/linux/instantclient/2360000/instantclient-basic-linux.x64-23.6.0.24.10.zip" \
            -o /tmp/instantclient.zip; \
    fi \
    && unzip /tmp/instantclient.zip -d /opt/oracle \
    && rm /tmp/instantclient.zip \
    && mv /opt/oracle/instantclient_* /opt/oracle/instantclient

# ── Runtime Stage ─────────────────────────────────────────────────────
FROM python:3.12-slim-bookworm AS runtime

WORKDIR /app

# System deps including Oracle client runtime dependencies + Chromium for
# Kaleido 1.x (Plotly static PNG export needs a real browser at render time;
# the `chromium` package pulls in the headless shared-lib + font deps).
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    curl \
    libaio1 \
    chromium \
    fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

# Copy Oracle Instant Client from oracle-client stage
COPY --from=oracle-client /opt/oracle/instantclient /opt/oracle/instantclient

# Configure Oracle client library path
RUN echo "/opt/oracle/instantclient" > /etc/ld.so.conf.d/oracle-instantclient.conf \
    && ldconfig

# Create non-root user WITH a real home directory. Headless Chromium (Kaleido)
# writes crashpad/config under $HOME; without an existing writable /home/aria it
# crashes immediately ("browser seemed to close immediately after starting").
RUN groupadd -r aria && useradd -r -g aria -m -d /home/aria aria

# Copy virtualenv from builder
COPY --from=builder /app/.venv /app/.venv

# Copy application code
COPY backend/ ./backend/
COPY agents/ ./agents/
COPY alembic.ini ./

# Set ownership
RUN chown -R aria:aria /app
USER aria

# Environment
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV ORACLE_CLIENT_LIB_DIR=/opt/oracle/instantclient
ENV LD_LIBRARY_PATH=/opt/oracle/instantclient:$LD_LIBRARY_PATH
# Kaleido/choreographer picks the browser from BROWSER_PATH; point it at the
# system chromium installed above (launched headless + --no-sandbox by default).
ENV BROWSER_PATH=/usr/bin/chromium

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
