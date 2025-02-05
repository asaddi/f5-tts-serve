FROM python:3.12-slim

# Quell pydub warning...
RUN --mount=type=cache,target=/var/cache/apt <<EOF
export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y \
    espeak-ng
rm -rf /var/lib/apt/lists/*
EOF

WORKDIR /app

COPY requirements.txt .

ARG PIP_INDEX_URL=https://pypi.org/simple
ARG PIP_EXTRA_INDEX_URL=https://download.pytorch.org/whl/cu124

ENV PIP_INDEX_URL=$PIP_INDEX_URL
ENV PIP_EXTRA_INDEX_URL=$PIP_EXTRA_INDEX_URL

RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements.txt

VOLUME ["/app/data"]
ENV HF_HOME=/app/data

COPY server.py .
COPY --chmod=755 docker-entrypoint.sh .

EXPOSE 8000/tcp

ENTRYPOINT ["/app/docker-entrypoint.sh"]
