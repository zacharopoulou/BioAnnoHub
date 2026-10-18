"""Every benchmark script must write its output so that an interrupted download leaves no file
that looks complete: rows go to <name>.part, which is renamed only once all rows are written."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "benchmarks" / "scripts"
WRITING_SCRIPTS = sorted(p for p in SCRIPTS_DIR.glob("*.py") if "def _write_jsonl" in p.read_text(encoding="utf-8"))


def _load(path: Path):
    spec = importlib.util.spec_from_file_location(f"benchmark_script_{path.stem}", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _rows_then_crash(good_rows: int):
    for index in range(good_rows):
        yield {"id": str(index)}
    raise ConnectionError("download stopped halfway")


def test_every_corpus_script_is_covered() -> None:
    assert len(WRITING_SCRIPTS) == 40


@pytest.mark.parametrize("script", WRITING_SCRIPTS, ids=lambda p: p.stem)
def test_interrupted_write_leaves_no_file(script: Path, tmp_path: Path) -> None:
    module = _load(script)
    target = tmp_path / "test.jsonl"

    with pytest.raises(ConnectionError):
        module._write_jsonl(target, _rows_then_crash(good_rows=2))

    assert not target.exists()  # nothing that looks complete
    assert not target.with_name("test.jsonl.part").exists()  # and no leftover partial file


@pytest.mark.parametrize("script", WRITING_SCRIPTS, ids=lambda p: p.stem)
def test_interrupted_write_keeps_an_existing_complete_file(script: Path, tmp_path: Path) -> None:
    module = _load(script)
    target = tmp_path / "test.jsonl"
    target.write_text('{"id": "complete"}\n', encoding="utf-8")

    with pytest.raises(ConnectionError):
        module._write_jsonl(target, _rows_then_crash(good_rows=2))

    assert target.read_text(encoding="utf-8") == '{"id": "complete"}\n'


@pytest.mark.parametrize("script", WRITING_SCRIPTS, ids=lambda p: p.stem)
def test_complete_write_renames_the_part_file(script: Path, tmp_path: Path) -> None:
    module = _load(script)
    target = tmp_path / "sub" / "test.jsonl"

    module._write_jsonl(target, iter([{"id": "a"}, {"id": "b"}]))

    assert [json.loads(line)["id"] for line in target.read_text(encoding="utf-8").splitlines()] == ["a", "b"]
    assert not target.with_name("test.jsonl.part").exists()


def test_umls_semantic_types_interrupted_write_leaves_no_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    module = _load(SCRIPTS_DIR / "umls_semantic_types.py")
    lines = [f"abcd|T{index:03d}|Type {index}" for index in range(module.EXPECTED_TYPES)]

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def read(self):
            return ("\n".join(lines) + "\n").encode("utf-8")

    monkeypatch.setattr(module.urllib.request, "urlopen", lambda *a, **k: FakeResponse())

    def crash(self, *args, **kwargs):
        raise OSError("disk full")

    monkeypatch.setattr(Path, "replace", crash)  # fail at the last moment, after the .part file was written

    with pytest.raises(OSError):
        module.download(tmp_path)
    assert not (tmp_path / module.FILE_NAME).exists()
    assert not (tmp_path / (module.FILE_NAME + ".part")).exists()
