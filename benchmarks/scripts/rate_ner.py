"""Download RaTE-NER (Radiopaedia part) into benchmarks/data/rate_ner/ as JSONL splits.

    uv run python benchmarks/scripts/rate_ner.py

RaTE-NER (Zhao et al., EMNLP 2024) is a radiology NER dataset on Hugging Face
(Angelakeke/RaTE-NER, CC BY-NC 4.0). It is not part of BigBIO, so this script
downloads its span files directly and converts them to the same bigbio_kb
layout as the other benchmarks. It needs no extra dependencies.

Only the Radiopaedia part is downloaded. The dataset also has a MIMIC-IV part,
but that is MIMIC-IV radiology report text, which is normally available only
with credentialed PhysioNet access, so it is left out here.

Each line of the source files is one tokenized sentence. Each sentence becomes
one document, whose text is its tokens joined by single spaces (the original
spacing is not in the source files).
"""

from __future__ import annotations

import json
import urllib.request
from pathlib import Path
from typing import Any, Iterable

HF_REPO = "Angelakeke/RaTE-NER"
# Pinned dataset version: the commit sha of the Hugging Face repo, i.e. the "sha" field of
# https://huggingface.co/api/datasets/Angelakeke/RaTE-NER (its latest commit when it was pinned).
HF_REVISION = "7327bf066d997713245ae61815a3b973406ea7b9"
SUBSET = "Radiopaedia"
SPLITS = {"train": "train", "validation": "dev", "test": "test"}  # our name -> file name


def _find_project_root() -> Path | None:
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "pyproject.toml").exists():
            return parent
    return None


def _default_data_dir() -> Path:
    root = _find_project_root()
    base = root if root is not None else Path.cwd()
    return base / "benchmarks" / "data" / "rate_ner"


def _split_file(data_dir: Path, split: str) -> Path:
    return data_dir / f"{split}.jsonl"


def _source_url(split: str) -> str:
    return f"https://huggingface.co/datasets/{HF_REPO}/resolve/{HF_REVISION}/{SUBSET}/{SPLITS[split]}_span.json"


def _write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, default=str))
            handle.write("\n")


def _to_bigbio_kb(doc_id: str, note_id: str, tokens: list[str], spans: list[list[Any]]) -> dict[str, Any]:
    """Join the tokens with single spaces and turn token spans (end inclusive) into character offsets."""
    if any(not token or token != token.strip() or " " in token for token in tokens):
        raise ValueError(f"{doc_id}: a token is empty or contains a space: {tokens!r}")
    starts = []
    position = 0
    for token in tokens:
        starts.append(position)
        position += len(token) + 1
    text = " ".join(tokens)

    entities = []
    for index, (first, last, entity_type) in enumerate(spans):
        if last == first - 1:
            # 4 spans in the Radiopaedia train file are empty (end one before start); skip them.
            continue
        if not 0 <= first <= last < len(tokens):
            raise ValueError(f"{doc_id}: span {first}-{last} is outside the {len(tokens)} tokens")
        start, end = starts[first], starts[last] + len(tokens[last])
        entities.append(
            {
                "id": f"{doc_id}_T{index}",
                "type": entity_type,
                "text": [text[start:end]],
                "offsets": [[start, end]],
                "normalized": [],
            }
        )
    return {
        "id": doc_id,
        "document_id": note_id,
        "passages": [{"id": f"{doc_id}_sentence", "type": "sentence", "text": [text], "offsets": [[0, len(text)]]}],
        "entities": entities,
        "events": [],
        "coreferences": [],
        "relations": [],
    }


def download_split(split: str, data_dir: Path) -> Path:
    """Download one split's span file, convert every sentence and persist it as JSONL."""
    with urllib.request.urlopen(_source_url(split), timeout=300) as response:
        lines = response.read().decode("utf-8").splitlines()
    rows = []
    skipped = 0
    for line_number, line in enumerate(lines):
        if not line.strip():
            continue
        record = json.loads(line)
        if len(record["sentences"]) != 1 or len(record["ner"]) != 1:
            raise ValueError(f"{split} line {line_number}: expected exactly one sentence")
        doc_id = f"{split}_{line_number}"
        row = _to_bigbio_kb(doc_id, str(record["note_id"]), record["sentences"][0], record["ner"][0])
        skipped += len(record["ner"][0]) - len(row["entities"])
        rows.append(row)
    if skipped:
        print(f"  {split:11s} skipped {skipped} empty spans")
    target = _split_file(data_dir, split)
    _write_jsonl(target, rows)
    return target


def main() -> None:
    data_dir = _default_data_dir()
    print(f"RaTE-NER target directory: {data_dir}")

    for split in SPLITS:
        target = _split_file(data_dir, split)
        if target.exists():
            count = sum(1 for _ in target.open(encoding="utf-8"))
            print(f"  {split:11s} already present ({count} docs) at {target}")
            continue
        print(f"  {split:11s} downloading from {_source_url(split)} ...")
        path = download_split(split, data_dir)
        count = sum(1 for _ in path.open(encoding="utf-8"))
        print(f"  {split:11s} wrote {count} docs to {path}")

    print("Done.")


if __name__ == "__main__":
    main()
