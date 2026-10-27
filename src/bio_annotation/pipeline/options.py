from __future__ import annotations

from typing import Any

from bio_annotation.annotators.apollo import DEFAULT_APOLLO_MODEL
from bio_annotation.annotators.clinicalbert import DEFAULT_CLINICALBERT_MODEL
from bio_annotation.annotators.d4data import DEFAULT_D4DATA_MODEL
from bio_annotation.annotators.scispacy import (
    SCISPACY_LINKER_NAME_BY_ANNOTATOR,
    SCISPACY_MODEL_BY_ANNOTATOR,
)
from bio_annotation.entity_proposal.stanza_proposer import STANZA_ANNOTATORS
from bio_annotation.entity_types import normalize_entity_type

SCISPACY_ANNOTATORS = tuple(SCISPACY_MODEL_BY_ANNOTATOR)


SCISPACY_ANNOTATOR_SET = frozenset(SCISPACY_ANNOTATORS)


SUPPORTED_ANNOTATORS = {
    "bern2",
    "flair",
    "pubtator3",
    "bent",
    "clinicalbert",
    "apollo",
    "d4data",
    "medcat",
    *SCISPACY_ANNOTATORS,
    *STANZA_ANNOTATORS,
}


DEFAULT_FLAIR_LINKERS = {
    "gene": "gene-linker",
    "disease": "disease-linker",
    "drug": "chemical-linker",
    "species": "species-linker",
}


RUN_CONFIG_NAME = "config.toml"


RUN_MANIFEST_NAME = "run_manifest.json"


RUN_INPUTS_DIR = "inputs"


RUN_RESULTS_DIR = "results"





def _validate_annotators(annotators: list[str]) -> None:
    unsupported = [annotator for annotator in annotators if annotator not in SUPPORTED_ANNOTATORS]
    if unsupported:
        raise ValueError(f"Unsupported annotators requested: {', '.join(unsupported)}")


def _read_bern2_options(settings: dict[str, object]) -> dict[str, Any]:
    endpoint = settings.get("endpoint")
    base_url = settings.get("base_url")

    cleaned_endpoint = None
    if isinstance(endpoint, str) and endpoint.strip():
        cleaned_endpoint = endpoint.strip()
    elif isinstance(base_url, str) and base_url.strip():
        cleaned_endpoint = base_url.strip()

    return {
        "endpoint": cleaned_endpoint,
    }


def _read_medcat_options(settings: dict[str, object]) -> dict[str, Any]:
    endpoint = settings.get("endpoint")
    base_url = settings.get("base_url")

    cleaned_endpoint = None
    if isinstance(endpoint, str) and endpoint.strip():
        cleaned_endpoint = endpoint.strip()
    elif isinstance(base_url, str) and base_url.strip():
        cleaned_endpoint = base_url.strip()

    min_acc_raw = settings.get("min_acc")
    min_acc = None
    if isinstance(min_acc_raw, (int, float)) and float(min_acc_raw) > 0.0:
        min_acc = float(min_acc_raw)

    return {
        "endpoint": cleaned_endpoint,
        "min_acc": min_acc,
    }


def _read_flair_options(settings: dict[str, object]) -> dict[str, Any]:
    model = settings.get("model")
    linking = settings.get("linking")
    raw_linkers = settings.get("linkers")
    linkers: list[str] = []
    if isinstance(raw_linkers, list):
        linkers = [item.strip() for item in raw_linkers if isinstance(item, str) and item.strip()]
    elif isinstance(raw_linkers, dict):
        for entity_type, linker_name in raw_linkers.items():
            if not isinstance(entity_type, str) or not isinstance(linker_name, str):
                continue
            if normalize_entity_type(entity_type) in DEFAULT_FLAIR_LINKERS and linker_name.strip():
                linkers.append(linker_name.strip())
    else:
        linkers = list(DEFAULT_FLAIR_LINKERS.values())

    return {
        "model": model.strip()
        if isinstance(model, str) and model.strip()
        else None,
        "linking": linking if isinstance(linking, bool) else False,
        "linkers": tuple(dict.fromkeys(linkers)),
    }


def _read_stanza_options(settings: dict[str, object]) -> dict[str, Any]:
    package = settings.get("package")
    # Leave package unset (None) when the config omits it, so annotate_with_stanza
    # can apply the model-specific default (mimic for i2b2/radiology, craft
    # otherwise). Defaulting to craft here would override that per-model choice.
    return {
        "package": package.strip()
        if isinstance(package, str) and package.strip()
        else None,
    }


def _read_bent_options(settings: dict[str, object]) -> dict[str, Any]:
    def _clean_str(key: str, default: str | None = None) -> str | None:
        value = settings.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
        return default

    raw_types = settings.get("types")
    types: dict[str, str] = {}
    if isinstance(raw_types, dict):
        for entity_type, kb in raw_types.items():
            if isinstance(entity_type, str) and entity_type.strip() and isinstance(kb, str):
                types[entity_type.strip()] = kb.strip()

    mode = _clean_str("mode", "ner_nel")
    if mode not in {"ner", "ner_nel"}:
        raise ValueError("annotators.bent.mode must be one of: 'ner', 'ner_nel'.")

    timeout = settings.get("timeout")
    return {
        "mode": mode,
        "project": _clean_str("project", "tools/bent"),
        "script": _clean_str("script"),
        "python": _clean_str("python"),
        "timeout": int(timeout) if isinstance(timeout, int) and timeout > 0 else 900,
        "types": types or None,
    }


def _read_scispacy_options(annotator: str, settings: dict[str, object]) -> dict[str, Any]:
    model = settings.get("model")
    linker_name = settings.get("linker_name")
    return {
        "model": model.strip()
        if isinstance(model, str) and model.strip()
        else SCISPACY_MODEL_BY_ANNOTATOR[annotator],
        "linker_name": linker_name.strip()
        if isinstance(linker_name, str) and linker_name.strip()
        else SCISPACY_LINKER_NAME_BY_ANNOTATOR.get(annotator),
    }


def _read_clinicalbert_options(settings: dict[str, object]) -> dict[str, Any]:
    model = settings.get("model")
    return {
        "model": model.strip()
        if isinstance(model, str) and model.strip()
        else DEFAULT_CLINICALBERT_MODEL,
    }


def _read_apollo_options(settings: dict[str, object]) -> dict[str, Any]:
    model = settings.get("model")
    return {
        "model": model.strip()
        if isinstance(model, str) and model.strip()
        else DEFAULT_APOLLO_MODEL,
    }


def _read_d4data_options(settings: dict[str, object]) -> dict[str, Any]:
    model = settings.get("model")
    return {
        "model": model.strip()
        if isinstance(model, str) and model.strip()
        else DEFAULT_D4DATA_MODEL,
    }


def _read_pubtator3_options(settings: dict[str, object]) -> dict[str, Any]:
    endpoint = settings.get("endpoint")
    timeout = settings.get("timeout")
    export_format = settings.get("format")

    return {
        "endpoint": endpoint if isinstance(endpoint, str) and endpoint.strip() else None,
        "timeout": timeout if isinstance(timeout, int) and timeout > 0 else 60,
        "format": export_format if isinstance(export_format, str) and export_format.strip() else "biocjson",
    }
