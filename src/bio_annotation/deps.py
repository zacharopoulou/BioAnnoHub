"""Prompted, on-demand installation of optional annotator dependencies.

Extras in this project share a single universal resolution in ``uv.lock``, so
enabling one only adds packages; versions of already-installed packages do not
change. That makes it safe to install mid-process and keep going, without
restarting the interpreter.
"""

from __future__ import annotations

import importlib
import os
import shutil
import subprocess
import sys
from importlib.util import find_spec
from pathlib import Path
from typing import Callable, Iterable

from bio_annotation.entity_proposal.apollo_proposer import APOLLO_INSTALL_HINT
from bio_annotation.entity_proposal.bent_proposer import DEFAULT_BENT_PROJECT, DEFAULT_BENT_TYPES
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

DISABLE_ENV_VAR = "TOTALANNOTATOR_NO_AUTO_INSTALL"

EXTRA_MODULES: dict[str, tuple[str, ...]] = {
    "flair": ("flair",),
    "clinicalbert": ("transformers", "torch"),
    "apollo": ("transformers", "torch"),
    "d4data": ("transformers", "torch"),
    "stanza": ("stanza",),
    "scispacy": ("scispacy", "spacy"),
    "benchmarks": ("datasets", "pandas", "tabulate"),
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


def uv_project_root() -> Path | None:
    """Return the uv project directory when running inside its own venv."""

    root = Path(sys.prefix).parent
    if (root / "pyproject.toml").exists() and (root / "uv.lock").exists():
        return root
    return None


def ensure_extras(
    annotators: Iterable[str],
    *,
    input_fn: Callable[[str], str] = input,
    output_fn: Callable[[str], None] = print,
) -> None:
    """Offer to install the extras ``annotators`` need.

    Returns without installing when the environment is not uv-managed, the
    session is not interactive, or the user declines; the caller is expected to
    fall back to raising the manual install hint.
    """

    missing = missing_extras(annotators)
    if not missing or os.environ.get(DISABLE_ENV_VAR):
        return
    root = uv_project_root()
    if root is None or shutil.which("uv") is None or not sys.stdin.isatty():
        return

    output_fn("")
    output_fn(f"The selected annotators need optional dependencies: {', '.join(missing)}.")
    output_fn(
        "Installing downloads several GB (PyTorch and model packages) and can take a few minutes."
    )
    if input_fn("Install them now with uv? [Y/n] ").strip().lower() not in ("", "y", "yes"):
        return

    # Every already-installed extra is passed too: uv sync is exact and would
    # otherwise uninstall the extras that are not named here.
    extras = sorted({*missing, *(e for e in EXTRA_MODULES if extra_installed(e))})
    command = ["uv", "sync", "--project", str(root)]
    for extra in extras:
        command += ["--extra", extra]
    output_fn(f"Running: {' '.join(command)}")
    if subprocess.run(command, check=False).returncode != 0:
        output_fn("uv sync failed. Install the extras manually and re-run.")
        return
    importlib.invalidate_caches()


# Annotators provisioned by a setup script instead of a pip extra: they need an
# external repo, their own interpreter, or downloaded resources.
TOOL_SETUP_SCRIPTS: dict[str, str] = {
    "bent": "tools/bent/setup.sh",
}
TOOL_SETUP_NOTES: dict[str, str] = {
    "bent": (
        "Provisions a separate Python <=3.10 environment and downloads BENT's resources. "
        "Needs wget, git, make, g++ and javac on PATH."
    ),
}


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def bent_root(project: str) -> Path | None:
    """Locate the installed bent package inside the tool venv, if provisioned."""

    roots = sorted((Path(project) / ".venv" / "lib").glob("python*/site-packages/bent"))
    return roots[0] if roots else None


def bent_required_kbs(settings: dict[str, object]) -> list[str]:
    """KB dictionaries the configured BENT types link against; none in NER-only mode."""

    if settings.get("mode") == "ner":
        return []
    types = settings.get("types")
    kbs = [kb.strip() for kb in types.values() if isinstance(kb, str) and kb.strip()] if isinstance(types, dict) else []
    return list(dict.fromkeys(kbs or DEFAULT_BENT_TYPES.values()))


def tool_ready(annotator: str, settings: dict[str, object]) -> bool:
    """Whether a setup-script annotator has its environment and resources in place."""

    if annotator == "bent":
        if any(isinstance(settings.get(key), str) and settings[key].strip() for key in ("python", "script")):
            return True
        project = settings.get("project")
        directory = project.strip() if isinstance(project, str) and project.strip() else DEFAULT_BENT_PROJECT

        root = bent_root(directory)
        if root is None:
            return False
        dicts = root / "data" / "kbs" / "dicts"
        return (
            (root / "data" / "NILINKER").exists()
            and (root / "data" / "overlapping_entities").exists()
            and (root / "abbreviation_detector" / "Ab3P" / "identify_abbr").exists()
            and all((dicts / kb).is_dir() for kb in bent_required_kbs(settings))
        )
    return True


def ensure_tool_environments(
    annotators: Iterable[str],
    settings_by_annotator: dict[str, dict[str, object]],
    *,
    input_fn: Callable[[str], str] = input,
    output_fn: Callable[[str], None] = print,
) -> None:
    """Offer to run the setup script for annotators that need one.

    Never raises: a declined or failed setup leaves the annotator unavailable and
    the run continues without it, as it did before this prompt existed.
    """

    pending = [
        annotator
        for annotator in annotators
        if annotator in TOOL_SETUP_SCRIPTS
        and not tool_ready(annotator, settings_by_annotator.get(annotator, {}))
    ]
    for annotator in pending:
        script = repo_root() / TOOL_SETUP_SCRIPTS[annotator]
        skipped = f"The {annotator} step will return no annotations this run."
        if not script.exists() or shutil.which("bash") is None:
            output_fn(f"Warning: {annotator} is not set up and {script} cannot be run here. {skipped}")
            continue
        if os.environ.get(DISABLE_ENV_VAR) or not sys.stdin.isatty():
            output_fn(f"Warning: {annotator} is not set up. Run {script} first. {skipped}")
            continue

        output_fn("")
        output_fn(f"{annotator} needs a one-time setup: {script}")
        output_fn(TOOL_SETUP_NOTES[annotator])
        if input_fn("Run it now? [Y/n] ").strip().lower() not in ("", "y", "yes"):
            output_fn(f"Skipping setup. {skipped}")
            continue
        env = None
        if annotator == "bent" and (kbs := bent_required_kbs(settings_by_annotator.get(annotator, {}))):
            # setup.sh downloads only the KBs in BENT_KBS, so pass the configured ones.
            env = {**os.environ, "BENT_KBS": ",".join(kbs)}
        if subprocess.run(["bash", str(script)], check=False, env=env).returncode != 0:
            output_fn(f"{script} failed. {skipped}")
