# MedCAT and HunFlair diagnostics

## MedCATservice setup

BioAnnoHub is an HTTP client; it does not install, start, or supply a model for
MedCATservice. A compatible model must be loaded by the separate service.
The default process URL is `http://localhost:5555/api/process`.

Configuration precedence is:

1. `[annotators.medcat] endpoint` (`base_url` is a compatibility alias).
2. Environment variable `MEDCAT_API_URL`.
3. The localhost default above.

```toml
[annotators]
enabled = ["medcat"]

[annotators.medcat]
endpoint = "http://localhost:5555/api/process"
# Optional confidence cutoff; defaults to no cutoff.
min_acc = 0.5
```

Use this table in an otherwise complete BioAnnoHub config, or export
`MEDCAT_API_URL` before running. Export `MEDCAT_MIN_ACC` to configure the cutoff
through the environment; a positive config `min_acc` takes precedence.
BioAnnoHub does not automatically load a `.env` file.
Root host URLs have `/api/process` appended; `/api` becomes `/api/process`.
An explicit non-root path is used as written, including paths behind a proxy.
The request timeout is 45 seconds in the HTTP client.

For a CPU example with the public MedMen model, the upstream repository provides
a Compose file that enables model downloads and maps host port 5555 to container
port 5000:

```bash
git clone https://github.com/CogStack/MedCATservice.git
cd MedCATservice/docker
docker compose -f docker-compose-example-medmen.yml up -d
docker compose -f docker-compose-example-medmen.yml ps
docker compose -f docker-compose-example-medmen.yml logs --tail=100
```

Wait for the model to download and load. Follow the
[upstream installation instructions](https://github.com/CogStack/MedCATservice)
for a different model, image version, GPU, or production deployment; record the
service image version and model used for reproducibility. For an existing model,
configure the service's `env/app.env`, `env/medcat.env`, and model mount as described
upstream before starting its `docker/docker-compose.yml`.

Check the service from the same host/container/network where BioAnnoHub runs:

```bash
curl --fail-with-body http://localhost:5555/api/info
curl --fail-with-body http://localhost:5555/api/health/ready
curl --fail-with-body -X POST http://localhost:5555/api/process \
  -H 'Content-Type: application/json' \
  -d '{"content":{"text":"The patient has diabetes."}}'
```

Readiness is available in newer service releases; a 404 on that health route can
mean an older version. `/api/info` alone does not prove inference works. The POST
request is the decisive availability check. BioAnnoHub uses the process request
itself to check availability rather than requiring a version-specific health URL.

`localhost` refers to the process's own host/container. If BioAnnoHub runs in a
container, use the MedCATservice network name and internal port (usually 5000) on
a shared Docker network, or a reachable host address and published port. If it
runs on a remote server, your laptop's localhost service is not reachable through
the server's localhost. Check `HTTP_PROXY`, `HTTPS_PROXY`, and `NO_PROXY` when a
proxy may intercept local requests; configure bypasses for the service hostname.

| Outcome | BioAnnoHub status | Action |
|---|---|---|
| Refused connection, DNS failure, timeout | `failed` | Start the service; check address, port and networking. |
| HTTP 503 | `failed` | An HTTP server/proxy answered; inspect service/model startup logs and proxy settings. This does not prove the service is stopped. |
| HTTP 404/405 | `failed` | Check the explicit process URL and HTTP method. |
| Invalid JSON, unknown JSON schema, `success=false` | `failed` | Check that the URL serves MedCAT inference and inspect service logs. |
| Recognized response with zero entities, or none above the confidence cutoff | `no_annotations` | Successful request with no retained annotations. |

The existing per-document statuses and aggregated run summary preserve the failure
reason. A failed document can still have an empty annotations list in the result
JSON; inspect its status to distinguish failure from a successful empty result.
Other annotators continue through the pipeline's existing failure handling.

## HunFlair: `Failed to find sentence`

The exact diagnostic is emitted by the native Ab3P library, exposed through
`pyab3p`, during abbreviation resolution in the HunFlair entity linkers:

- [Flair 0.15.1 `Ab3PEntityPreprocessor`](https://github.com/flairNLP/flair/blob/v0.15.1/flair/models/entity_mention_linking.py)
  calls `ab3p.get_abbrs(sentence.to_original_text())`.
- [pyab3p `AbbrvE::find_sentence_offsets`](https://github.com/helpmefindaname/pyab3p/blob/main/ab3p_source/AbbrvE.cpp)
  searches for the internally segmented sentence in its supplied text and writes
  `Failed to find sentence` directly to native stderr on a mismatch.
- Its MPtok segmentation can change whitespace, so the exact substring lookup can
  fail. With pyab3p 0.1.1, double spaces in `Methods that  are effective.` reproduce
  the warning: the internal sentence contains a single space. Subsequent sentences
  can also warn because the search position has reached the end of the text.

The original reported run/input was not available for replay. The source of this
message and a whitespace mismatch are confirmed; the exact transformation that
produced `thatare`, `ofusing`, or `ofpatients` in that run is not yet reproduced.
Do not infer that the saved input lost its spaces from these messages alone.

BioAnnoHub passes its canonical `document.text` unchanged to Flair's `Sentence`.
Flair reconstructs text from tokens for abbreviation preprocessing. The native
warning concerns that internal abbreviation sentence lookup, rather than
BioAnnoHub's lookup of entity spans. The Ab3P lookup can leave failed sentence
offsets at zero; its returned abbreviation offsets must not be trusted in this
case. Flair uses the returned short/long-form strings for linking, not those
offsets for the exported NER spans. A native reproduction can still return an
abbreviation despite the warning, but this is not proof that every linked ID is
unaffected. Review NEN results separately when these warnings appear.

BioAnnoHub now validates each exported Flair span against the canonical text:

- Coordinates must be in range and match the span's non-whitespace characters.
- The exported `span_text` uses the exact source substring, preserving internal
  tabs/newlines or multiple spaces reconstructed differently by Flair.
- Explicit incorrect coordinates cause a visible failed annotator status rather
  than silently moving the mention to another occurrence. Missing coordinates
  may be recovered only for an unambiguous exact occurrence.

The coordinate reference is `document.text`: stripped title, a blank line, and
stripped abstract/full text as defined by `Document.get_text()`. It is not
necessarily the byte-for-byte source file, including any surrounding whitespace.
For every accepted Flair annotation:

```python
assert annotation.span_text == document.text[annotation.start:annotation.end]
```

When an Ab3P linker is active, an INFO diagnostic identifies the source of the
native messages and their possible effect on linked IDs. Native stderr remains
visible. It is not globally redirected or suppressed.

For diagnosis, repeat with `linking = false` under `[annotators.flair]` to isolate
NER, then compare the span coordinates with a linking-enabled run. To keep linking
while explicitly disabling abbreviation resolution, configure Flair's published
`gene-linker-no-ab3p`, `disease-linker-no-ab3p`, `chemical-linker-no-ab3p`, and
`species-linker-no-ab3p` models in the `linkers` list. This changes NEN behavior
and is an opt-in diagnostic choice, not a default fix.

## Validation

```bash
uv run pytest tests/test_annotator_diagnostics.py tests/test_medcat_proposer.py \
  tests/test_hunflair_nen.py tests/test_annotators.py \
  tests/test_pipeline_runner.py tests/test_pipeline_module_regressions.py
```

Tests use a real local HTTP server for MedCAT HTTP outcomes, injected connection
failures, and controlled Flair spans/linkers. The optional native Ab3P regression
test runs when `pyab3p` is installed. They do not download HunFlair model weights
or start a real MedCAT model service. Replay the original run in its environment
to confirm its linked IDs and the exact glued-word transformation.
