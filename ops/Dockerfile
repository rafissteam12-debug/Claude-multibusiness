# syntax=docker/dockerfile:1
# Belegbrücke app image. Build from the repository root:
#   docker build -f ops/Dockerfile -t ablaufwerk-app .
# The ignore file is ops/Dockerfile.dockerignore (BuildKit picks it up next to this Dockerfile).
# Base image: pin by digest once CI prints it (job "docker", step "Base image digest").
ARG PYTHON_IMAGE=python:3.12-slim-trixie

# ---------------------------------------------------------------- tools: KoSIT + config + Mustang
FROM ${PYTHON_IMAGE} AS tools
COPY ops/pins.txt /build/pins.txt
COPY ops/scripts/fetch_tools.py /build/fetch_tools.py
# Downloads over HTTPS and verifies every file against ops/pins.txt; a mismatch fails the build.
# --strict: an image is never built from an unpinned file.
RUN python /build/fetch_tools.py --pins /build/pins.txt --dest /opt/tools --strict

# ---------------------------------------------------------------- runtime
FROM ${PYTHON_IMAGE}

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

# Headless JRE for KoSIT and Mustang (trixie: OpenJDK 21). The man1 dir works around the
# openjdk postinst on slim images.
RUN mkdir -p /usr/share/man/man1 \
 && apt-get update \
 && apt-get install -y --no-install-recommends default-jre-headless \
 && rm -rf /var/lib/apt/lists/*

RUN groupadd --system --gid 10001 app \
 && useradd --system --uid 10001 --gid app --home-dir /srv/app --shell /usr/sbin/nologin app

WORKDIR /srv/app

# Runtime dependencies only (no site/, no pytest).
COPY engine/requirements.txt engine/requirements.txt
COPY mapping/requirements.txt mapping/requirements.txt
COPY app/requirements.txt app/requirements.txt
RUN pip install -r engine/requirements.txt -r mapping/requirements.txt -r app/requirements.txt

COPY --from=tools /opt/tools /opt/tools
COPY contracts/ contracts/
COPY engine/ engine/
COPY mapping/ mapping/
COPY app/ app/
COPY content/emails/ content/emails/
COPY content/help/ content/help/
COPY --chmod=0755 ops/scripts/purge.sh /opt/ops/purge.sh

# Data volume: SQLite DB and temp files (uploads, outputs; purged after RETENTION_HOURS).
RUN mkdir -p /data/tmp && chown -R app:app /data
VOLUME ["/data"]

ENV APP_ENV=staging \
    DATABASE_PATH=/data/app.db \
    TEMP_DIR=/data/tmp \
    RETENTION_HOURS=24 \
    KOSIT_VALIDATOR_JAR=/opt/tools/kosit-validator.jar \
    KOSIT_CONFIG_DIR=/opt/tools/kosit-config \
    MUSTANG_JAR=/opt/tools/mustang-cli.jar \
    JAVA_TOOL_OPTIONS="-Xmx1g -Dfile.encoding=UTF-8"

USER app
EXPOSE 8000

# Cheap liveness endpoint provided by the app (requested: GET /healthz -> 200, no DB writes, no auth).
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
  CMD ["python", "-c", "import sys, urllib.request; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/healthz', timeout=4).status == 200 else 1)"]

# --no-access-log: access lines contain query strings (magic-link/opt-in tokens). The reverse proxy
# logs requests with tokens and IPs filtered (ops/Caddyfile). One worker: SQLite + in-process jobs.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log", "--no-server-header", "--proxy-headers", "--forwarded-allow-ips", "*"]
