FROM python:3.12-slim-bookworm

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
    TOTALANNOTATOR_NO_AUTO_INSTALL=1 \
    PATH=/app/.venv/bin:$PATH

WORKDIR /app

COPY tools/bent/pyproject.toml tools/bent/uv.lock tools/bent/setup.sh tools/bent/
RUN --mount=type=cache,target=/root/.cache/uv \
    bash tools/bent/setup.sh \
    && chmod -R a+rwX tools/bent/.venv

COPY pyproject.toml uv.lock .python-version ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --extra all --no-install-project

RUN python - <<'PY' && chmod -R a+rwX /opt/models/huggingface
from transformers import pipeline
for model in ("samrawal/bert-base-uncased_clinical-ner", "Clinical-AI-Apollo/Medical-NER", "d4data/biomedical-ner-all"):
    pipeline("ner", model=model, tokenizer=model)
PY

RUN python - <<'PY' && chmod -R a+rwX /opt/models/flair /opt/models/huggingface
from flair.nn import Classifier
Classifier.load("hunflair2")
PY

RUN python - <<'PY' && chmod -R a+rwX /opt/models/stanza
import stanza
models = ("bc5cdr", "bionlp13cg", "jnlpba", "i2b2", "radiology", "anatem", "bc4chemd", "linnaeus", "ncbi_disease", "s800")
packages = {"i2b2": "mimic", "radiology": "mimic"}
for model in models:
    stanza.download("en", package=None, processors={"tokenize": packages.get(model, "craft"), "ner": model}, verbose=False)
PY

RUN python - <<'PY' && chmod -R a+rwX /opt/models/scispacy
import scispacy.linking  # noqa: F401
import spacy
spacy.load("en_core_sci_md").add_pipe("scispacy_linker", config={"linker_name": "umls"})
PY

COPY . .
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --extra all

ENV UV_FROZEN=1 \
    UV_NO_SYNC=1 \
    UV_PYTHON_DOWNLOADS=never \
    UV_CACHE_DIR=/tmp/uv-cache \
    MPLCONFIGDIR=/tmp/matplotlib

ENTRYPOINT ["bioannohub"]
CMD ["--help"]
