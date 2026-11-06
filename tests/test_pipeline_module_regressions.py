from pathlib import Path

import pytest

from bio_annotation import pipeline_runner
from bio_annotation.pipeline import execution, manifest, runner
from bio_annotation.schemas.document import Document


def test_latest_directory_is_preserved_with_warning(tmp_path, caplog):
    latest = tmp_path / "latest"
    latest.mkdir()
    manifest.update_latest_run_link(tmp_path / "run")

    assert latest.is_dir()
    assert not latest.is_symlink()
    assert "exists and is not a symlink" in caplog.text


def test_latest_symlink_failure_is_logged(tmp_path, monkeypatch, caplog):
    def fail_symlink(*args, **kwargs):
        raise OSError("symlinks unavailable")

    monkeypatch.setattr(Path, "symlink_to", fail_symlink)
    manifest.update_latest_run_link(tmp_path / "run")

    assert "Could not update" in caplog.text
    assert "symlinks unavailable" in caplog.text


def test_direct_execution_records_annotator_failure(monkeypatch, caplog):
    def fail_annotator(*args, **kwargs):
        raise RuntimeError("annotator unavailable")

    monkeypatch.setattr(execution, "annotate_with_bern2", fail_annotator)
    results, statuses = execution.run_selected_annotators_with_status(
        Document("doc1"), ["bern2"]
    )

    assert results == {"bern2": []}
    assert statuses[0]["status"] == "failed"
    assert statuses[0]["reason"] == "annotator unavailable"
    assert "bern2 unavailable: annotator unavailable" in caplog.text


@pytest.mark.parametrize("raises", [False, True])
@pytest.mark.parametrize(
    "entry_point",
    [
        "build_pipeline_output",
        "run_selected_annotators",
        "run_selected_annotators_with_status",
        "run_pipeline_from_config",
    ],
)
def test_compat_hooks_are_restored_after_call(entry_point, raises, monkeypatch):
    original = execution.annotate_with_bern2

    def fake_annotator(*args, **kwargs):
        return []

    def invoke():
        assert execution.annotate_with_bern2 is fake_annotator
        if raises:
            raise RuntimeError("pipeline failed")
        return "result"

    target = runner if entry_point == "run_pipeline_from_config" else execution
    monkeypatch.setattr(pipeline_runner, "annotate_with_bern2", fake_annotator)
    monkeypatch.setattr(target, entry_point, invoke)

    if raises:
        with pytest.raises(RuntimeError, match="pipeline failed"):
            getattr(pipeline_runner, entry_point)()
    else:
        assert getattr(pipeline_runner, entry_point)() == "result"

    assert execution.annotate_with_bern2 is original


def test_direct_execution_uses_own_hook_after_compat_patch(monkeypatch):
    calls = []

    def direct_annotator(*args, **kwargs):
        calls.append("direct")
        return []

    def compat_annotator(*args, **kwargs):
        calls.append("compat")
        return []

    monkeypatch.setattr(execution, "annotate_with_bern2", direct_annotator)
    with monkeypatch.context() as patch:
        patch.setattr(pipeline_runner, "annotate_with_bern2", compat_annotator)
        pipeline_runner.run_selected_annotators(Document("doc1"), ["bern2"])

    execution.run_selected_annotators(Document("doc2"), ["bern2"])
    assert calls == ["compat", "direct"]


def test_runs_started_in_same_second_preserve_existing_output(tmp_path):
    from datetime import datetime
    from concurrent.futures import ThreadPoolExecutor

    now = datetime(2026, 11, 6, 12, 0, 0)
    first = manifest.create_run_dir(tmp_path, now=now)
    saved = first / 'results.json'
    saved.write_text('existing run', encoding='utf-8')
    with ThreadPoolExecutor(max_workers=4) as pool:
        others = list(pool.map(lambda _: manifest.create_run_dir(tmp_path, now=now), range(4)))
    assert len({first, *others}) == 5
    assert saved.read_text(encoding='utf-8') == 'existing run'
