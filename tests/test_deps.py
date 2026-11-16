from __future__ import annotations

from pathlib import Path

import pytest

from bio_annotation import deps


def test_missing_extras_maps_annotators_and_skips_remote_ones(monkeypatch) -> None:
    monkeypatch.setattr(deps, "extra_installed", lambda extra: False)

    assert deps.missing_extras(["scispacy_bc5cdr", "stanza_i2b2", "bern2", "pubtator3"]) == [
        "scispacy",
        "stanza",
    ]


def _install_bent(project: Path) -> None:
    (project / ".venv" / "lib" / "python3.10" / "site-packages" / "bent").mkdir(parents=True)


@pytest.fixture
def bent_project(tmp_path, monkeypatch) -> Path:
    """The repository's own tools/bent, i.e. the folder the image installs BENT into."""

    root = tmp_path.resolve()
    monkeypatch.chdir(root)
    monkeypatch.setattr(deps, "repo_root", lambda: root)
    return root / "tools" / "bent"


def test_tool_ready_checks_bent_project(bent_project) -> None:
    assert deps.tool_ready("bent", {}) is False

    _install_bent(bent_project)

    assert deps.tool_ready("bent", {}) is True
    assert deps.tool_ready("bent", {"project": str(bent_project)}) is True


def test_tool_ready_trusts_custom_bent_project(bent_project) -> None:
    assert deps.tool_ready("bent", {"project": "custom"}) is True


@pytest.mark.parametrize("key", ["python", "script"])
def test_tool_ready_trusts_custom_bent_installation(bent_project, key) -> None:
    assert deps.tool_ready("bent", {key: "/opt/bent/bin/python"}) is True
    assert deps.tool_ready("bent", {key: "  "}) is False



def test_model_installed_checks_stanza_resources(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("STANZA_RESOURCES_DIR", str(tmp_path))
    assert deps.model_installed("stanza_bc5cdr") is False

    (tmp_path / "en" / "ner").mkdir(parents=True)
    (tmp_path / "en" / "ner" / "bc5cdr.pt").touch()

    assert deps.model_installed("stanza_bc5cdr") is True


def test_model_installed_checks_scispacy_package() -> None:
    assert deps.model_installed("scispacy_md", "en_core_sci_not_a_model") is False
    assert deps.model_installed("bern2") is True
