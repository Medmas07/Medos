# Hospital Node container image (HC-220, ADR-0015).
#
# One image for every hospital: it holds the Node's code and pinned dependencies only.
# Each hospital's configuration and data are mounted at runtime, read-only, under
# /etc/hospital-node/, so no hospital's records are ever baked into the image.
#
# Build from this directory:  docker build -t hackcure/hospital-node:dev .

FROM python:3.12.12-slim-bookworm@sha256:593bd06efe90efa80dc4eee3948be7c0fde4134606dd40d8dd8dbcade98e669c

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Code is owned by root and read-only for the Node's unprivileged user.
COPY . .

# storage_dir target; nothing writes it yet (persistence is OPEN).
RUN useradd --system --uid 10001 --no-create-home --shell /usr/sbin/nologin hospital-node \
    && mkdir -p /var/lib/hospital-node /etc/hospital-node \
    && chown hospital-node:hospital-node /var/lib/hospital-node

USER hospital-node

# The configuration file is mounted here; the Node refuses to start without it.
ENV HOSPITAL_NODE_CONFIG=/etc/hospital-node/node.json \
    HOSPITAL_NODE_HOST=0.0.0.0

# Listens on the port set in the mounted configuration (8101 for Hospital A).
CMD ["python", "main.py"]
