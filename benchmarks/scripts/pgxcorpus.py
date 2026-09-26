"""Download PGxCorpus into benchmarks/data/pgxcorpus/ as one JSONL file.

    uv run python benchmarks/scripts/pgxcorpus.py

PGxCorpus is not on Hugging Face, so this script downloads the brat files
(PGxCorpus.tar) from the practikpharma GitHub repository (pinned to a fixed
commit) and converts them to the same bigbio_kb layout as the other
benchmarks. It needs no extra dependencies.

Each document is one sentence. About half of the annotations in the
original files have an extra space at the end of their text field (for
example "estrone " while the offsets cover "estrone"). The offsets are
correct, so the mention text is taken from the offsets (_parse_ann).
"""

from __future__ import annotations

import io
import json
import tarfile
import urllib.request
from pathlib import Path
from typing import Any, Iterable

SOURCE_COMMIT = "067513c1ed0ad55c28e62aef5a5bc14b6945595e"
SOURCE_URL = f"https://github.com/practikpharma/PGxCorpus/raw/{SOURCE_COMMIT}/PGxCorpus.tar"
SPLITS = ("pgxcorpus",)  # PGxCorpus has no splits: the whole corpus is one file, pgxcorpus.jsonl


def _find_project_root() -> Path | None:
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "pyproject.toml").exists():
            return parent
    return None


def _default_data_dir() -> Path:
    root = _find_project_root()
    base = root if root is not None else Path.cwd()
    return base / "benchmarks" / "data" / "pgxcorpus"


def _split_file(data_dir: Path, split: str) -> Path:
    return data_dir / f"{split}.jsonl"


def _write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, default=str))
            handle.write("\n")


def _parse_ann(ann_text: str, doc_text: str, doc_id: str) -> list[dict[str, Any]]:
    """Convert brat T-lines into bigbio_kb entities, with the text taken from the offsets."""
    entities = []
    for line in ann_text.splitlines():
        if not line.startswith("T"):
            continue
        term_id, type_and_offsets, surface = line.split("\t")
        entity_type, _, offsets_raw = type_and_offsets.partition(" ")
        offsets = [[int(x) for x in fragment.split()] for fragment in offsets_raw.split(";")]
        fragments = [doc_text[start:end] for start, end in offsets]
        if " ".join(fragments) != surface.strip():
            raise ValueError(f"{doc_id}/{term_id}: offsets give {fragments!r}, annotation says {surface!r}")
        entities.append(
            {
                "id": f"{doc_id}_{term_id}",
                "type": entity_type,
                "text": fragments,
                "offsets": offsets,
                "normalized": [],
            }
        )
    return entities


def _to_bigbio_kb(doc_id: str, text: str, ann_text: str) -> dict[str, Any]:
    end = len(text.rstrip())
    return {
        "id": doc_id,
        "document_id": doc_id,
        "passages": [{"id": f"{doc_id}_s", "type": "sentence", "text": [text[:end]], "offsets": [[0, end]]}],
        "entities": _parse_ann(ann_text, text, doc_id),
        "events": [],
        "coreferences": [],
        "relations": [],
    }


def download_split(split: str, data_dir: Path) -> Path:
    """Download PGxCorpus.tar, convert every sentence and persist the corpus as JSONL."""
    with urllib.request.urlopen(SOURCE_URL, timeout=300) as response:
        archive = tarfile.open(fileobj=io.BytesIO(response.read()), mode="r:")
    members = {Path(m.name).name: m for m in archive.getmembers() if m.isfile()}
    rows = []
    for name in sorted(n for n in members if n.endswith(".txt")):
        doc_id = name[:-4]
        text = archive.extractfile(members[name]).read().decode("utf-8")
        ann_text = archive.extractfile(members[doc_id + ".ann"]).read().decode("utf-8")
        rows.append(_to_bigbio_kb(doc_id, text, ann_text))
    target = _split_file(data_dir, split)
    _write_jsonl(target, rows)
    return target


def main() -> None:
    data_dir = _default_data_dir()
    print(f"PGxCorpus target directory: {data_dir}")

    for split in SPLITS:
        target = _split_file(data_dir, split)
        if target.exists():
            count = sum(1 for _ in target.open(encoding="utf-8"))
            print(f"  {split:11s} already present ({count} docs) at {target}")
            continue
        print(f"  {split:11s} downloading from {SOURCE_URL} ...")
        path = download_split(split, data_dir)
        count = sum(1 for _ in path.open(encoding="utf-8"))
        print(f"  {split:11s} wrote {count} docs to {path}")

    print("Done.")


if __name__ == "__main__":
    main()
