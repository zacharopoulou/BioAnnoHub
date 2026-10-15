from __future__ import annotations

from pathlib import Path

import pytest

import bio_annotation.cli as cli
from bio_annotation.benchmarking import download
from bio_annotation.cli import main


def _fake_repo(tmp_path: Path, keys: list[str]) -> Path:
    scripts = tmp_path / "benchmarks" / "scripts"
    scripts.mkdir(parents=True)
    for key in keys:
        (scripts / f"{key}.py").write_text('"""Fake benchmark script."""\n', encoding="utf-8")
    return scripts


def test_find_repo_root_finds_benchmarks_scripts(tmp_path: Path) -> None:
    _fake_repo(tmp_path, ["biored"])
    nested = tmp_path / "src" / "pkg"
    nested.mkdir(parents=True)
    assert download.find_repo_root(nested) == tmp_path


def test_load_benchmarks_sorts_by_name_with_umls_list_last(tmp_path: Path) -> None:
    scripts = _fake_repo(tmp_path, ["umls_semantic_types", "ncbi", "biored", "_helper"])
    keys = [b.key for b in download.load_benchmarks(scripts)]
    assert keys == ["biored", "ncbi", "umls_semantic_types"]


def test_parse_choice_numbers_ranges_names_and_all(tmp_path: Path) -> None:
    scripts = _fake_repo(tmp_path, ["biored", "ddi", "ncbi", "radgraph_xl"])
    benchmarks = download.load_benchmarks(scripts)  # BioRED, DDI, NCBI Disease, RadGraph-XL

    assert [b.key for b in download.parse_choice("1, 3", benchmarks)] == ["biored", "ncbi"]
    assert [b.key for b in download.parse_choice("1-3 2", benchmarks)] == ["biored", "ddi", "ncbi"]
    assert [b.key for b in download.parse_choice("ddi", benchmarks)] == ["ddi"]
    # RadGraph-XL is credentialed data: never part of "all".
    assert [b.key for b in download.parse_choice("all", benchmarks)] == ["biored", "ddi", "ncbi"]
    with pytest.raises(ValueError):
        download.parse_choice("nonsense", benchmarks)


def test_cli_download_benchmarks_passes_flags(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = []
    monkeypatch.setattr(cli, "download_benchmarks", lambda **kwargs: calls.append(kwargs) or 0)

    assert main(["download-benchmarks", "--all"]) == 0
    assert main(["download-benchmarks", "--list"]) == 0
    assert calls == [
        {"download_all": True, "list_only": False},
        {"download_all": False, "list_only": True},
    ]


def test_cli_download_benchmarks_list_runs_on_the_repository() -> None:
    assert main(["download-benchmarks", "--list"]) == 0
