from __future__ import annotations

import subprocess
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


def test_parse_choice_numbers_ranges_and_all(tmp_path: Path) -> None:
    scripts = _fake_repo(tmp_path, ["biored", "ddi", "ncbi", "radgraph_xl"])
    benchmarks = download.load_benchmarks(scripts)  # BioRED, DDI, NCBI Disease, RadGraph-XL

    assert [b.key for b in download.parse_choice("1, 3", benchmarks)] == ["biored", "ncbi"]
    assert [b.key for b in download.parse_choice("1-3 2", benchmarks)] == ["biored", "ddi", "ncbi"]
    # RadGraph-XL is credentialed data: never part of "all".
    assert [b.key for b in download.parse_choice("all", benchmarks)] == ["biored", "ddi", "ncbi"]


@pytest.mark.parametrize("answer", ["ddi", "NCBI Disease", "99", "nonsense"])
def test_parse_choice_rejects_names_and_unknown_numbers(tmp_path: Path, answer: str) -> None:
    benchmarks = download.load_benchmarks(_fake_repo(tmp_path, ["biored", "ddi", "ncbi"]))
    with pytest.raises(ValueError):
        download.parse_choice(answer, benchmarks)


def _fail_if_called(*args, **kwargs):
    raise AssertionError("no benchmark script should run")


@pytest.mark.parametrize("missing", [["datasets", "bioc", "pandas"], ["bioc"]])
def test_missing_packages_stop_before_downloading_anything(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], missing: list[str]
) -> None:
    scripts = _fake_repo(tmp_path, ["ddi"])
    (scripts / "biored.py").write_text("from datasets import load_dataset\n", encoding="utf-8")
    monkeypatch.setattr(download, "find_repo_root", lambda: tmp_path)
    monkeypatch.setattr(download, "missing_packages", lambda: missing)
    monkeypatch.setattr(download.subprocess, "run", _fail_if_called)

    assert download.download_benchmarks(download_all=True) == 1
    output = " ".join(capsys.readouterr().out.split())  # ignore the console's line wrapping
    assert f"Nothing was downloaded: missing packages {', '.join(missing)}" in output
    assert "needed by 1 of the selected benchmarks" in output
    assert "uv sync --extra benchmarks" in output


def test_missing_packages_do_not_block_direct_downloads(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    benchmarks = download.load_benchmarks(_fake_repo(tmp_path, ["maccrobat", "phaedra"]))  # no Hugging Face
    monkeypatch.setattr(download, "missing_packages", lambda: ["datasets", "bioc", "pandas"])
    assert download.missing_packages_message(benchmarks) is None


def test_radgraph_without_zip_is_reported_and_exit_code_is_1(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    scripts = _fake_repo(tmp_path, [])
    (scripts / "radgraph_xl.py").write_text(
        "from pathlib import Path\n"
        "SPLITS = ('radgraph_xl',)\n"
        "ZIP_NAME = 'radgraph.zip'\n"
        f"def _default_data_dir():\n    return Path({str(tmp_path / 'data')!r})\n"
        "def _split_file(data_dir, split):\n    return data_dir / f'{split}.jsonl'\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(download.Path, "home", lambda: tmp_path)  # no zip in ~/Downloads
    monkeypatch.setattr(download.subprocess, "run", _fail_if_called)

    assert download.run(download.load_benchmarks(scripts), tmp_path) == 1
    output = capsys.readouterr().out
    assert "RadGraph-XL" in output
    assert "zip was not found" in output
    assert "Not everything was downloaded (1 of 1)" in output


def test_failed_script_is_reported_and_exit_code_is_1(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    benchmarks = download.load_benchmarks(_fake_repo(tmp_path, ["biored", "ncbi"]))
    codes = iter([0, 2])  # BioRED succeeds, NCBI Disease fails
    monkeypatch.setattr(download.subprocess, "run", lambda *a, **k: subprocess.CompletedProcess(a, next(codes)))

    assert download.run(benchmarks, tmp_path) == 1
    output = capsys.readouterr().out
    assert "exit code 2" in output
    assert "Not everything was downloaded (1 of 2)" in output


def test_exit_code_is_0_only_when_everything_succeeded(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    benchmarks = download.load_benchmarks(_fake_repo(tmp_path, ["biored", "ncbi"]))
    monkeypatch.setattr(download.subprocess, "run", lambda *a, **k: subprocess.CompletedProcess(a, 0))

    assert download.run(benchmarks, tmp_path) == 0
    assert "All 2 downloaded" in capsys.readouterr().out


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
