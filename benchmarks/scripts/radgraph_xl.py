"""Convert a local RadGraph-XL download into benchmarks/data/radgraph_xl/ as one JSONL file.

    uv run python benchmarks/scripts/radgraph_xl.py [path/to/radgraph-xl-...-1.0.0.zip]

RadGraph-XL (Delbrouck et al., Findings of ACL 2024) is on PhysioNet with
**credentialed access** only (PhysioNet Credentialed Health Data License).
This script cannot download it: each user downloads the zip from
https://physionet.org/content/radgraph-xl/1.0.0/ themselves and passes its
path (default: the zip's original name in ~/Downloads). The converted file
must not be shared, so the whole data folder except the README is in
.gitignore.

The zip holds mimic-radgraph-XL.jsonl: 300 MIMIC radiology reports (chest CT,
abdomen/pelvis CT, brain MR) in the DyGIE format, with token-level entity
spans (end inclusive) and relations. They are converted to the same bigbio_kb
layout as the other benchmarks. The text of each report is its tokens joined
by single spaces (the original spacing is not in the source file).
"""

from __future__ import annotations

import hashlib
import json
import sys
import zipfile
from pathlib import Path
from typing import Any, Iterable

ZIP_NAME = (
    "radgraph-xl-a-large-scale-expert-annotated-dataset-for-entity-and-relation-extraction-"
    "from-radiology-reports-1.0.0.zip"
)
MEMBER = ZIP_NAME[: -len(".zip")] + "/mimic-radgraph-XL.jsonl"
MEMBER_SHA256 = "21d7d3d4d7354e3a02dede58577471d3354c060c1a8a64ecc1d4e7b6269402a7"  # from SHA256SUMS.txt
SPLITS = ("radgraph_xl",)  # no splits: all 300 reports are in one file, radgraph_xl.jsonl


def _find_project_root() -> Path | None:
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "pyproject.toml").exists():
            return parent
    return None


def _default_data_dir() -> Path:
    root = _find_project_root()
    base = root if root is not None else Path.cwd()
    return base / "benchmarks" / "data" / "radgraph_xl"


def _split_file(data_dir: Path, split: str) -> Path:
    return data_dir / f"{split}.jsonl"


def _write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, default=str))
            handle.write("\n")


def _to_bigbio_kb(record: dict[str, Any]) -> dict[str, Any]:
    """Join all tokens with single spaces and turn token spans (end inclusive) into character offsets."""
    doc_id = f"{record['dataset']}_{record['doc_key']}"
    tokens = [token for sentence in record["sentences"] for token in sentence]
    if any(not token or token != token.strip() or " " in token for token in tokens):
        raise ValueError(f"{doc_id}: a token is empty or contains a space")
    starts = []
    position = 0
    for token in tokens:
        starts.append(position)
        position += len(token) + 1
    text = " ".join(tokens)

    passages = []
    first_token = 0
    for index, sentence in enumerate(record["sentences"]):
        last_token = first_token + len(sentence) - 1
        start, end = starts[first_token], starts[last_token] + len(tokens[last_token])
        passages.append({"id": f"{doc_id}_s{index}", "type": "sentence", "text": [text[start:end]], "offsets": [[start, end]]})
        first_token = last_token + 1

    entities = []
    entity_by_span: dict[tuple[int, int], str] = {}
    for first, last, label in (span for sentence in record["ner"] for span in sentence):
        if not 0 <= first <= last < len(tokens):
            raise ValueError(f"{doc_id}: span {first}-{last} is outside the {len(tokens)} tokens")
        start, end = starts[first], starts[last] + len(tokens[last])
        entity_id = f"{doc_id}_T{len(entities)}"
        entity_by_span.setdefault((first, last), entity_id)
        entities.append({"id": entity_id, "type": label, "text": [text[start:end]], "offsets": [[start, end]], "normalized": []})

    relations = []
    for first1, last1, first2, last2, label in (rel for sentence in record["relations"] for rel in sentence):
        relations.append(
            {
                "id": f"{doc_id}_R{len(relations)}",
                "type": label,
                "arg1_id": entity_by_span[(first1, last1)],
                "arg2_id": entity_by_span[(first2, last2)],
                "normalized": [],
            }
        )

    return {
        "id": doc_id,
        "document_id": doc_id,
        "passages": passages,
        "entities": entities,
        "events": [],
        "coreferences": [],
        "relations": relations,
    }


def convert(zip_path: Path, data_dir: Path) -> Path:
    """Read the local RadGraph-XL zip, check it, convert every report and persist it as JSONL."""
    with zipfile.ZipFile(zip_path) as archive:
        raw = archive.read(MEMBER)
    if hashlib.sha256(raw).hexdigest() != MEMBER_SHA256:
        raise ValueError(f"{MEMBER} does not match the checksum of the 1.0.0 release")
    rows = [_to_bigbio_kb(json.loads(line)) for line in raw.decode("utf-8").splitlines() if line.strip()]
    target = _split_file(data_dir, SPLITS[0])
    _write_jsonl(target, rows)
    return target


def main() -> None:
    zip_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.home() / "Downloads" / ZIP_NAME
    data_dir = _default_data_dir()
    print(f"RadGraph-XL target directory: {data_dir}")

    for split in SPLITS:
        target = _split_file(data_dir, split)
        if target.exists():
            count = sum(1 for _ in target.open(encoding="utf-8"))
            print(f"  {split:11s} already present ({count} docs) at {target}")
            continue
        if not zip_path.exists():
            raise SystemExit(
                f"RadGraph-XL zip not found: {zip_path}\n"
                "Download it (credentialed access) from https://physionet.org/content/radgraph-xl/1.0.0/ "
                "and pass its path as the first argument."
            )
        print(f"  {split:11s} converting {zip_path} ...")
        path = convert(zip_path, data_dir)
        count = sum(1 for _ in path.open(encoding="utf-8"))
        print(f"  {split:11s} wrote {count} docs to {path}")

    print("Done.")


if __name__ == "__main__":
    main()
