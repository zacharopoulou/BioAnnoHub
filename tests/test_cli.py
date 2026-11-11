from pathlib import Path

from bio_annotation import cli


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
