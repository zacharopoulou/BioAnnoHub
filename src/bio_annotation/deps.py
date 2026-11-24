"""Which optional annotators are available in this environment."""

from __future__ import annotations

import os
import tomllib
from importlib.util import find_spec
from pathlib import Path
from typing import Iterable

from bio_annotation.entity_proposal.apollo_proposer import APOLLO_INSTALL_HINT
from bio_annotation.entity_proposal.bent_proposer import DEFAULT_BENT_PROJECT, SETUP_HINT as BENT_SETUP_HINT
from bio_annotation.entity_proposal.clinicalbert_proposer import CLINICALBERT_INSTALL_HINT
from bio_annotation.entity_proposal.d4data_proposer import D4DATA_INSTALL_HINT
from bio_annotation.entity_proposal.flair_proposer import FLAIR_INSTALL_HINT
from bio_annotation.entity_proposal.scispacy_proposer import (
    SCISPACY_INSTALL_HINT,
    SCISPACY_MODEL_BY_ANNOTATOR,
)
from bio_annotation.entity_proposal.stanza_proposer import (
    STANZA_ANNOTATORS,
    STANZA_INSTALL_HINT,
    stanza_model_for_annotator,
)

EXTRA_MODULES: dict[str, tuple[str, ...]] = {
    "flair": ("flair", "pyab3p"),
    "clinicalbert": ("transformers", "torch"),
    "apollo": ("transformers", "torch"),
    "d4data": ("transformers", "torch"),
    "stanza": ("stanza",),
    "scispacy": ("scispacy", "spacy"),
}

ANNOTATOR_EXTRAS: dict[str, str] = {
    "flair": "flair",
    "clinicalbert": "clinicalbert",
    "apollo": "apollo",
    "d4data": "d4data",
    **{annotator: "scispacy" for annotator in SCISPACY_MODEL_BY_ANNOTATOR},
    **{annotator: "stanza" for annotator in STANZA_ANNOTATORS},
}

EXTRA_INSTALL_HINTS: dict[str, str] = {
    "flair": FLAIR_INSTALL_HINT,
    "clinicalbert": CLINICALBERT_INSTALL_HINT,
    "apollo": APOLLO_INSTALL_HINT,
    "d4data": D4DATA_INSTALL_HINT,
    "stanza": STANZA_INSTALL_HINT,
    "scispacy": SCISPACY_INSTALL_HINT,
}


def extra_installed(extra: str) -> bool:
    try:
        return all(find_spec(module) is not None for module in EXTRA_MODULES[extra])
    except (ImportError, ValueError):
        return False


def missing_extras(annotators: Iterable[str]) -> list[str]:
    """Extras required by ``annotators`` that are not installed, in order."""

    missing: list[str] = []
    for annotator in annotators:
        extra = ANNOTATOR_EXTRAS.get(annotator)
        if extra is not None and extra not in missing and not extra_installed(extra):
            missing.append(extra)
    return missing


def model_installed(annotator: str, scispacy_model: str | None = None) -> bool:
    """Whether the local model a scispaCy or Stanza annotator loads is present."""

    if annotator in SCISPACY_MODEL_BY_ANNOTATOR:
        model = scispacy_model or SCISPACY_MODEL_BY_ANNOTATOR[annotator]
        try:
            return Path(model).exists() or find_spec(model) is not None
        except (ImportError, ValueError):
            return False
    if annotator in STANZA_ANNOTATORS:
        resources = Path(os.environ.get("STANZA_RESOURCES_DIR", Path.home() / "stanza_resources"))
        return (resources / "en" / "ner" / f"{stanza_model_for_annotator(annotator)}.pt").is_file()
    return True


def flair_linker_installed(linker: str) -> bool:
    from flair.models import EntityMentionLinker

    try:
        EntityMentionLinker._fetch_model(linker)
    except Exception:
        return False
    return True


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _image_sections() -> list[dict] | None:
    """The images.toml sections of the Docker image in use; None outside an image."""

    image = os.environ.get("BIOANNOHUB_IMAGE")
    if not image:
        return None
    with (repo_root() / "images.toml").open("rb") as handle:
        images = tomllib.load(handle)
    return [images["slim"]] if image == "slim" else [images["slim"], images[image]]


def image_ships(annotator: str) -> bool:
    sections = _image_sections()
    return sections is None or any(annotator in section["annotators"] for section in sections)


def image_ships_flair_linkers() -> bool:
    sections = _image_sections()
    return sections is None or any(section.get("flair_linkers", False) for section in sections)


def bent_root(project: str | Path) -> Path | None:
    """Locate the installed bent package inside the tool venv, if provisioned."""

    roots = sorted((Path(project) / ".venv" / "lib").glob("python*/site-packages/bent"))
    return roots[0] if roots else None


def tool_ready(annotator: str, settings: dict[str, object]) -> bool:
    """Whether an annotator with its own environment, i.e. BENT, is installed."""

    if annotator == "bent":
        if any(isinstance(settings.get(key), str) and settings[key].strip() for key in ("python", "script")):
            return True
        project = settings.get("project")
        directory = project.strip() if isinstance(project, str) and project.strip() else DEFAULT_BENT_PROJECT
        directory = (repo_root() / directory).resolve()
        if directory != repo_root() / DEFAULT_BENT_PROJECT:
            return True
        return bent_root(directory) is not None
    return True

