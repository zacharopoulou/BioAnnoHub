from __future__ import annotations

from http.server import BaseHTTPRequestHandler, HTTPServer
import json
from threading import Thread
from types import SimpleNamespace
from urllib.error import URLError

import pytest

from bio_annotation.entity_proposal import medcat_proposer
from bio_annotation.entity_proposal.flair_proposer import annotate_with_flair, parse_flair_labels
from bio_annotation.pipeline.execution import run_selected_annotators_with_status
from bio_annotation.schemas.document import Document


@pytest.fixture
def medcat_server():
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            self.server.request_path = self.path
            self.server.request_payload = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
            self.send_response(self.server.response_status)
            self.end_headers()
            self.wfile.write(self.server.response_body)

        def log_message(self, *args):
            pass

    server = HTTPServer(('127.0.0.1', 0), Handler)
    server.response_status = 200
    server.response_body = b'{"result": {"annotations": {}, "success": true}}'
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server, f'http://127.0.0.1:{server.server_port}'
    finally:
        server.shutdown()
        thread.join()
        server.server_close()


@pytest.mark.parametrize(('code', 'body', 'status', 'reason'), [
    (200, b'{"result":{"annotations":{},"success":true}}', 'no_annotations', 'completed successfully'),
    (503, b'Service Unavailable', 'failed', 'HTTP 503'),
    (404, b'Not found', 'failed', 'endpoint path'),
    (200, b'<html>wrong service</html>', 'failed', 'invalid JSON'),
    (200, b'{"result":{"success":false,"annotations":[]}}', 'failed', 'success=false'),
    (200, b'{"health":"ok"}', 'failed', 'unrecognized response'),
])
def test_medcat_http_outcomes_reach_pipeline_status(medcat_server, code, body, status, reason):
    server, endpoint = medcat_server
    server.response_status, server.response_body = code, body
    document = Document(document_id='test', abstract='Patients with diabetes.')
    results, statuses = run_selected_annotators_with_status(
        document, annotators=['medcat'], medcat_options={'endpoint': endpoint},
    )
    assert results == {'medcat': []}
    assert statuses[0]['status'] == status
    assert reason in statuses[0]['reason']
    assert server.request_path == '/api/process'
    assert server.request_payload['content']['text'] == document.text


def test_medcat_connection_failure_is_not_empty_prediction(monkeypatch):
    def refuse(*args, **kwargs):
        raise URLError('connection refused')
    monkeypatch.setattr(medcat_proposer.request, 'urlopen', refuse)
    _, statuses = run_selected_annotators_with_status(
        Document(document_id='test', abstract='diabetes'), annotators=['medcat'],
    )
    assert statuses[0]['status'] == 'failed'
    assert 'connection failed' in statuses[0]['reason']


def test_medcat_successful_annotation_reaches_pipeline(medcat_server):
    server, endpoint = medcat_server
    server.response_body = json.dumps({'result': {'annotations': {'entities': {
        '0': {'cui': 'C0011849', 'source_value': 'diabetes', 'start': 14, 'end': 22},
    }}}}).encode()
    document = Document(document_id='test', abstract='Patients with diabetes.')
    results, statuses = run_selected_annotators_with_status(
        document, annotators=['medcat'], medcat_options={'endpoint': endpoint},
    )
    assert statuses[0]['status'] == 'produced_annotations'
    annotation = results['medcat'][0]
    assert document.text[annotation.start:annotation.end] == annotation.span_text == 'diabetes'


def test_medcat_endpoint_precedence_and_explicit_path(medcat_server, monkeypatch):
    server, endpoint = medcat_server
    monkeypatch.setenv('MEDCAT_API_URL', endpoint + '/from-env')
    document = Document(document_id='test', abstract='diabetes')
    medcat_proposer.call_medcat(document)
    assert server.request_path == '/from-env'
    medcat_proposer.call_medcat(document, endpoint=endpoint + '/custom/process')
    assert server.request_path == '/custom/process'
    assert medcat_proposer._normalize_medcat_process_url(endpoint + '/api') == endpoint + '/api/process'


@pytest.mark.parametrize('endpoint', ['localhost:5555', 'ftp://host', 'http://host:bad'])
def test_medcat_rejects_invalid_endpoint(endpoint):
    with pytest.raises(medcat_proposer.MedCATServiceError):
        medcat_proposer.call_medcat(Document(document_id='test'), endpoint=endpoint)


def test_medcat_none_callback_does_not_retry_default_service(monkeypatch):
    def unexpected(*args, **kwargs):
        pytest.fail('callback failure must not call a different service')
    monkeypatch.setattr(medcat_proposer, 'call_medcat', unexpected)
    with pytest.raises(medcat_proposer.MedCATServiceError):
        medcat_proposer.annotate_with_medcat(Document(document_id='test'), request_fn=lambda _: None)


def label(text, start, end):
    return SimpleNamespace(value='Gene', score=0.9, data_point=SimpleNamespace(
        text=text, start_position=start, end_position=end,
    ))


def test_flair_repeated_mentions_and_original_whitespace():
    document = Document(document_id='test', title='PTEN', abstract='PTEN\t\tprotein. PTEN\nprotein.')
    labels = []
    for mention in ['PTEN\t\tprotein', 'PTEN\nprotein']:
        start = document.text.index(mention)
        labels.append(label('PTEN protein', start, start + len(mention)))
    annotations = parse_flair_labels(document, labels)
    assert len(annotations) == 2
    assert annotations[0].start != annotations[1].start
    for annotation in annotations:
        assert document.text[annotation.start:annotation.end] == annotation.span_text


@pytest.mark.parametrize(('start', 'end'), [(1, 5), (-1, 3), (0, 99)])
def test_flair_rejects_wrong_offsets(start, end):
    with pytest.raises(ValueError, match='Flair span'):
        parse_flair_labels(Document(document_id='test', abstract='PTEN'), [label('PTEN', start, end)])


def test_flair_linking_diagnostic_and_offsets(caplog):
    document = Document(document_id='test', abstract='PTEN in patients.')
    ner_label = label('PTEN', 0, 4)
    class Sentence:
        def __init__(self, text):
            assert text == document.text
        def get_labels(self, kind):
            return [ner_label] if kind == 'ner' else []
    class Tagger:
        def predict(self, sentence):
            pass
    class Linker:
        preprocessor = SimpleNamespace(ab3p=object())
        def predict(self, sentence):
            pass
    with caplog.at_level('INFO'):
        annotations = annotate_with_flair(document, tagger=Tagger(), linkers=[Linker()], sentence_factory=Sentence)
    assert 'Ab3P' in caplog.text
    assert 'linked IDs may be affected' in caplog.text
    assert annotations[0].span_text == document.text[0:4]


def test_ab3p_native_warning_does_not_change_input(capfd):
    pyab3p = pytest.importorskip('pyab3p')
    original = 'Methods that  are effective. Benefits of  using PTEN. A group of  patients with glioblastoma (GBM).'
    ab3p = pyab3p.Ab3p()
    abbreviations = ab3p.get_abbrs(original)
    assert 'Failed to find sentence:' in capfd.readouterr().err
    assert 'that  are' in original
    assert any(item.short_form == 'GBM' and item.long_form == 'glioblastoma' for item in abbreviations)
