from pathlib import Path

import pytest

from bio_annotation import cli


@pytest.mark.parametrize('command', ['inspect-config', 'load-documents', 'run-config'])
def test_missing_config_reports_error_without_traceback(command, tmp_path, capsys):
    missing = tmp_path / 'missing.toml'
    assert cli.main([command, '--config', str(missing)]) == 1
    output = capsys.readouterr()
    assert str(missing) in output.err
    assert not output.out
    assert 'Traceback' not in output.err


def test_missing_input_reports_error_without_traceback(tmp_path, capsys):
    config = tmp_path / 'pipeline.toml'
    missing = tmp_path / 'missing.tsv'
    config.write_text(
        f'[input]\nmode = "text_table"\ntext_file = "{missing.as_posix()}"\n'
        'format = "tsv"\n[annotators]\nenabled = []\n', encoding='utf-8'
    )
    assert cli.main(['load-documents', '--config', str(config)]) == 1
    assert str(missing) in capsys.readouterr().err


@pytest.mark.parametrize('error', [EOFError, KeyboardInterrupt])
def test_annotation_interruption_exits_cleanly(monkeypatch, capsys, error):
    def interrupted(**kwargs):
        raise error()
    monkeypatch.setattr(cli, 'run_terminal_annotation_ui', interrupted)
    assert cli.main(['annotate']) == 130
    assert 'Annotation cancelled.' in capsys.readouterr().err


def test_search_output_write_failure_is_reported(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(cli, 'search_pubmed_pmids', lambda *args, **kwargs: ['123'])
    # An existing directory cannot be used as an output file.
    assert cli.main(['search-pmids', '--query', 'PTEN', '--output', str(tmp_path)]) == 1
    output = capsys.readouterr()
    assert not output.out
    assert str(tmp_path) in output.err


def test_local_text_ingestion_writes_complete_run(tmp_path, capsys):
    import json
    from bio_annotation.pipeline_config import load_pipeline_config
    from bio_annotation.preprocessing.document_loader import load_documents_from_config

    source = tmp_path / 'documents.tsv'
    source.write_text('document_id\ttitle\tabstract\ndoc1\tPTEN\tPTEN is a gene.\n', encoding='utf-8')
    config = tmp_path / 'pipeline.toml'
    config.write_text(
        f'[input]\nmode = "text_table"\ntext_file = "{source.as_posix()}"\n'
        'format = "tsv"\n[annotators]\nenabled = []\n'
        f'[output]\npath = "{(tmp_path / "runs" / "results.json").as_posix()}"\n', encoding='utf-8'
    )
    assert cli.main(['run-config', '--config', str(config)]) == 0
    assert 'Pipeline completed.' in capsys.readouterr().out
    manifest_path = next((tmp_path / 'runs').glob('*/run_manifest.json'))
    manifest = json.loads(manifest_path.read_text())
    for path in manifest['files'].values():
        assert Path(path).is_file()
    # A completed run still loads after its original input is removed.
    source.unlink()
    copied_config = load_pipeline_config(Path(manifest['files']['config']))
    documents = load_documents_from_config(copied_config)
    assert documents[0].text == 'PTEN\n\nPTEN is a gene.'
