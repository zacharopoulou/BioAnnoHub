from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from bio_annotation import deps
from bio_annotation.entity_proposal.bent_proposer import DEFAULT_BENT_TYPES


@pytest.fixture
def uv_environment(monkeypatch) -> list[list[str]]:
    """Pretend we run interactively inside a uv-managed project venv."""

    commands: list[list[str]] = []
    monkeypatch.delenv(deps.DISABLE_ENV_VAR, raising=False)
    monkeypatch.setattr(deps, "uv_project_root", lambda: Path("/proj"))
    monkeypatch.setattr(deps.shutil, "which", lambda name: "/usr/bin/uv")
    monkeypatch.setattr(deps.sys.stdin, "isatty", lambda: True, raising=False)
    monkeypatch.setattr(
        deps.subprocess,
        "run",
        lambda command, check=False, env=None: commands.append(command) or SimpleNamespace(returncode=0),
    )
    return commands


def test_missing_extras_maps_annotators_and_skips_remote_ones(monkeypatch) -> None:
    monkeypatch.setattr(deps, "extra_installed", lambda extra: False)

    assert deps.missing_extras(["scispacy_bc5cdr", "stanza_i2b2", "bern2", "pubtator3"]) == [
        "scispacy",
        "stanza",
    ]


def test_ensure_extras_syncs_missing_and_already_installed_extras(monkeypatch, uv_environment) -> None:
    # uv sync is exact, so an installed extra must be re-declared or it is pruned.
    monkeypatch.setattr(deps, "extra_installed", lambda extra: extra == "benchmarks")

    deps.ensure_extras(["flair"], input_fn=lambda prompt: "", output_fn=lambda line: None)

    assert uv_environment == [
        ["uv", "sync", "--project", "/proj", "--extra", "benchmarks", "--extra", "flair"]
    ]


def test_ensure_extras_does_nothing_when_declined(monkeypatch, uv_environment) -> None:
    monkeypatch.setattr(deps, "extra_installed", lambda extra: False)

    deps.ensure_extras(["flair"], input_fn=lambda prompt: "n", output_fn=lambda line: None)

    assert uv_environment == []


def test_ensure_extras_respects_opt_out(monkeypatch, uv_environment) -> None:
    monkeypatch.setattr(deps, "extra_installed", lambda extra: False)
    monkeypatch.setenv(deps.DISABLE_ENV_VAR, "1")

    def refuse(prompt: str) -> str:
        raise AssertionError("should not prompt")

    deps.ensure_extras(["flair"], input_fn=refuse, output_fn=lambda line: None)

    assert uv_environment == []


def test_ensure_extras_skips_when_not_uv_managed(monkeypatch, uv_environment) -> None:
    monkeypatch.setattr(deps, "extra_installed", lambda extra: False)
    monkeypatch.setattr(deps, "uv_project_root", lambda: None)

    def refuse(prompt: str) -> str:
        raise AssertionError("should not prompt")

    deps.ensure_extras(["flair"], input_fn=refuse, output_fn=lambda line: None)

    assert uv_environment == []


@pytest.fixture
def tool_environment(monkeypatch) -> list[list[str]]:
    """Interactive session where a setup script exists and can be run."""

    commands: list[list[str]] = []
    monkeypatch.delenv(deps.DISABLE_ENV_VAR, raising=False)
    monkeypatch.setattr(deps, "tool_ready", lambda annotator, settings: False)
    monkeypatch.setattr(deps.Path, "exists", lambda self: True)
    monkeypatch.setattr(deps.shutil, "which", lambda name: "/usr/bin/bash")
    monkeypatch.setattr(deps.sys.stdin, "isatty", lambda: True, raising=False)
    monkeypatch.setattr(
        deps.subprocess,
        "run",
        lambda command, check=False, env=None: commands.append(command) or SimpleNamespace(returncode=0),
    )
    return commands


def test_ensure_tool_environments_runs_setup_script(tool_environment) -> None:
    unavailable = deps.ensure_tool_environments(
        ["bent", "bern2"], {}, input_fn=lambda prompt: "", output_fn=lambda line: None
    )

    assert unavailable == {}
    assert tool_environment == [["bash", str(deps.repo_root() / "tools/bent/setup.sh")]]


def test_ensure_tool_environments_warns_and_continues_when_declined(tool_environment) -> None:
    messages: list[str] = []

    unavailable = deps.ensure_tool_environments(
        ["bent"], {}, input_fn=lambda prompt: "n", output_fn=messages.append
    )

    assert unavailable == {"bent": "bent setup was skipped."}
    assert tool_environment == []
    assert any("no annotations this run" in message for message in messages)


def test_ensure_tool_environments_warns_when_non_interactive(monkeypatch, tool_environment) -> None:
    monkeypatch.setattr(deps.sys.stdin, "isatty", lambda: False, raising=False)
    messages: list[str] = []

    def refuse(prompt: str) -> str:
        raise AssertionError("should not prompt")

    unavailable = deps.ensure_tool_environments(["bent"], {}, input_fn=refuse, output_fn=messages.append)

    assert list(unavailable) == ["bent"]
    assert "setup.sh" in unavailable["bent"]
    assert tool_environment == []
    assert any("setup.sh" in message for message in messages)


def _install_bent(project: Path, kbs: list[str]) -> None:
    root = project / ".venv" / "lib" / "python3.10" / "site-packages" / "bent"
    (root / "data" / "NILINKER").mkdir(parents=True)
    (root / "data" / "overlapping_entities").mkdir()
    (root / "abbreviation_detector" / "Ab3P").mkdir(parents=True)
    (root / "abbreviation_detector" / "Ab3P" / "identify_abbr").touch()
    for kb in kbs:
        kb_dir = root / "data" / "kbs" / "dicts" / kb
        kb_dir.mkdir(parents=True)
        for name in deps.BENT_KB_FILES:
            (kb_dir / name).write_text("{}", encoding="utf-8")


@pytest.fixture
def bent_project(tmp_path, monkeypatch) -> Path:
    """The repository's own tools/bent, i.e. the folder setup.sh provisions."""

    root = tmp_path.resolve()
    monkeypatch.chdir(root)
    monkeypatch.setattr(deps, "repo_root", lambda: root)
    return root / "tools" / "bent"


def test_tool_ready_checks_setup_bent_project(bent_project) -> None:
    assert deps.tool_ready("bent", {}) is False

    _install_bent(bent_project, list(DEFAULT_BENT_TYPES.values()))

    assert deps.tool_ready("bent", {}) is True
    assert deps.tool_ready("bent", {"project": str(bent_project)}) is True


def test_tool_ready_trusts_custom_bent_project(bent_project) -> None:
    assert deps.tool_ready("bent", {"project": "custom"}) is True


def test_tool_ready_requires_every_default_bent_kb(bent_project) -> None:
    _install_bent(bent_project, ["medic"])

    assert deps.tool_ready("bent", {}) is False


def test_tool_ready_checks_only_configured_bent_kbs(bent_project) -> None:
    _install_bent(bent_project, ["medic"])

    assert deps.tool_ready("bent", {"types": {"disease": "medic"}}) is True
    assert deps.tool_ready("bent", {"types": {"chemical": "chebi"}}) is False


def test_tool_ready_skips_bent_kbs_in_ner_mode(bent_project) -> None:
    _install_bent(bent_project, [])

    assert deps.tool_ready("bent", {"mode": "ner"}) is True
    assert deps.tool_ready("bent", {}) is False


def test_ensure_tool_environments_passes_configured_bent_kbs(monkeypatch, tool_environment) -> None:
    envs: list[dict[str, str] | None] = []
    monkeypatch.setattr(
        deps.subprocess,
        "run",
        lambda command, check=False, env=None: envs.append(env) or SimpleNamespace(returncode=0),
    )

    deps.ensure_tool_environments(
        ["bent"],
        {"bent": {"types": {"disease": "medic", "chemical": "chebi"}}},
        input_fn=lambda prompt: "",
        output_fn=lambda line: None,
    )

    assert envs[0]["BENT_KBS"] == "medic,chebi"


@pytest.mark.parametrize("key", ["python", "script"])
def test_tool_ready_trusts_custom_bent_installation(bent_project, key) -> None:
    assert deps.tool_ready("bent", {key: "/opt/bent/bin/python"}) is True
    assert deps.tool_ready("bent", {key: "  "}) is False


def test_ensure_tool_environments_skips_custom_bent_installation(monkeypatch, tmp_path) -> None:
    monkeypatch.chdir(tmp_path)
    messages: list[str] = []

    def refuse(prompt: str) -> str:
        raise AssertionError("should not prompt")

    deps.ensure_tool_environments(
        ["bent"], {"bent": {"python": "/opt/bent/bin/python"}}, input_fn=refuse, output_fn=messages.append
    )

    assert messages == []
