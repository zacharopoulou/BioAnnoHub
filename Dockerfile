# Build the slim image (default) or the full one:
#   docker build -t bioannohub .
#   docker build --build-arg IMAGE=full -t bioannohub:full .
ARG IMAGE=slim

FROM python:3.12-slim-bookworm AS base

COPY --from=ghcr.io/astral-sh/uv:0.13.1 /uv /uvx /usr/local/bin/

RUN apt-get update \
    && apt-get install -y --no-install-recommends wget git make g++ default-jdk-headless ca-certificates \
    && rm -rf /var/lib/apt/lists/*

ENV UV_LINK_MODE=copy \
    UV_PYTHON_INSTALL_DIR=/opt/uv/python \
    HF_HOME=/opt/models/huggingface \
    FLAIR_CACHE_ROOT=/opt/models/flair \
    STANZA_RESOURCES_DIR=/opt/models/stanza \
    SCISPACY_CACHE=/opt/models/scispacy \
    PATH=/repository/.venv/bin:$PATH

WORKDIR /repository

COPY pyproject.toml uv.lock .python-version ./
COPY images.toml ./
COPY tools/fetch_models.py tools/

FROM base AS slim-env
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --extra slim --no-install-project
RUN python tools/fetch_models.py slim

FROM slim-env AS full-env
COPY tools/bent/pyproject.toml tools/bent/uv.lock tools/bent/setup.sh tools/bent/
RUN --mount=type=cache,target=/root/.cache/uv \
    bash tools/bent/setup.sh \
    && chmod -R a+rwX tools/bent/.venv
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --extra full --no-install-project
RUN python tools/fetch_models.py full

FROM ${IMAGE}-env
ARG IMAGE
COPY . .
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --extra ${IMAGE}

ENV UV_FROZEN=1 \
    UV_NO_SYNC=1 \
    UV_PYTHON_DOWNLOADS=never \
    UV_CACHE_DIR=/tmp/uv-cache \
    MPLCONFIGDIR=/tmp/matplotlib \
    HF_HUB_OFFLINE=1 \
    USER=bioannohub

WORKDIR /work

ENTRYPOINT ["bioannohub"]
CMD ["--help"]
