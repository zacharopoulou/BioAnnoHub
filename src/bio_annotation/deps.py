"""Which optional annotators are available in this environment."""

from __future__ import annotations

from importlib.util import find_spec
from pathlib import Path
from typing import Callable, Iterable

from bio_annotation.entity_proposal.apollo_proposer import APOLLO_INSTALL_HINT
from bio_annotation.entity_proposal.bent_proposer import DEFAULT_BENT_PROJECT
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


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


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


def unavailable_tools(
    annotators: Iterable[str],
    settings_by_annotator: dict[str, dict[str, object]],
    *,
    output_fn: Callable[[str], None] = print,
) -> dict[str, str]:
    """Annotators with their own environment that are not installed, with the reason for each."""

    unavailable: dict[str, str] = {}
    for annotator in annotators:
        if annotator == "bent" and not tool_ready(annotator, settings_by_annotator.get(annotator, {})):
            unavailable[annotator] = f"{annotator} is not installed in this environment."
            output_fn(f"Warning: {unavailable[annotator]} The {annotator} step will return no annotations this run.")
    return unavailable
