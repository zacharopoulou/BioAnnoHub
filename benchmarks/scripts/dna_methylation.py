"""Download the DNA Methylation corpus into benchmarks/data/dna_methylation/ as JSONL splits.

    uv run python benchmarks/scripts/dna_methylation.py

The corpus is not on Hugging Face, so this script downloads the original
brat standoff files from the openbiocorpora GitHub repository (pinned to a
fixed commit) and converts them to the same bigbio_kb layout as the other
benchmarks. It needs no extra dependencies.

Only the Protein annotations in the .a1 files are used. The .a2 files hold
the events and an "Entity" type that was only annotated when it takes part
in an event, so they are left out.
"""

from __future__ import annotations

import io
import json
import urllib.request
import zipfile
from pathlib import Path
from typing import Any, Iterable

SOURCE_COMMIT = "cbc076e54805f9d6fe4a311af1cd717ba620d25f"
SOURCE_URL = f"https://github.com/openbiocorpora/dna-methylation/archive/{SOURCE_COMMIT}.zip"
# The real test set was never released; "develtest" is the public held-out set.
SPLITS = ("train", "develtest")


def _find_project_root() -> Path | None:
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "pyproject.toml").exists():
            return parent
    return None


def _default_data_dir() -> Path:
    root = _find_project_root()
    base = root if root is not None else Path.cwd()
    return base / "benchmarks" / "data" / "dna_methylation"


def _split_file(data_dir: Path, split: str) -> Path:
    return data_dir / f"{split}.jsonl"


def _write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, default=str))
            handle.write("\n")


def _parse_a1(ann_text: str, doc_text: str, doc_id: str) -> list[dict[str, Any]]:
    """Convert brat T-lines into bigbio_kb entities, checking each offset against the text."""
    entities = []
    for line in ann_text.splitlines():
        if not line.startswith("T"):
            continue
        term_id, type_and_offsets, surface = line.split("\t")
        entity_type, _, offsets_raw = type_and_offsets.partition(" ")
        offsets = [[int(x) for x in fragment.split()] for fragment in offsets_raw.split(";")]
        fragments = [doc_text[start:end] for start, end in offsets]
        if " ".join(fragments) != surface:
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
    # Each .txt file is the title, a newline, then the abstract.
    title_end = text.index("\n")
    abstract_end = len(text.rstrip())
    return {
        "id": doc_id,
        "document_id": doc_id,
        "passages": [
            {"id": f"{doc_id}_title", "type": "title", "text": [text[:title_end]], "offsets": [[0, title_end]]},
            {
                "id": f"{doc_id}_abstract",
                "type": "abstract",
                "text": [text[title_end + 1 : abstract_end]],
                "offsets": [[title_end + 1, abstract_end]],
            },
        ],
        "entities": _parse_a1(ann_text, text, doc_id),
        "events": [],
        "coreferences": [],
        "relations": [],
    }


def download_all(data_dir: Path, splits: Iterable[str]) -> dict[str, Path]:
    """Download the corpus once and write the requested splits as JSONL."""
    with urllib.request.urlopen(SOURCE_URL, timeout=300) as response:
        archive = zipfile.ZipFile(io.BytesIO(response.read()))
    root = f"dna-methylation-{SOURCE_COMMIT}/original-data"

    written = {}
    for split in splits:
        prefix = f"{root}/{split}/"
        txt_names = sorted(n for n in archive.namelist() if n.startswith(prefix) and n.endswith(".txt"))
        rows = []
        for name in txt_names:
            doc_id = Path(name).stem
            text = archive.read(name).decode("utf-8")
            ann_text = archive.read(name[:-4] + ".a1").decode("utf-8")
            rows.append(_to_bigbio_kb(doc_id, text, ann_text))
        target = _split_file(data_dir, split)
        _write_jsonl(target, rows)
        written[split] = target
    return written


def main() -> None:
    data_dir = _default_data_dir()
    print(f"DNA Methylation target directory: {data_dir}")

    missing = []
    for split in SPLITS:
        target = _split_file(data_dir, split)
        if target.exists():
            count = sum(1 for _ in target.open(encoding="utf-8"))
            print(f"  {split:11s} already present ({count} docs) at {target}")
        else:
            missing.append(split)

    if missing:
        print(f"  downloading from {SOURCE_URL} ...")
        for split, path in download_all(data_dir, missing).items():
            count = sum(1 for _ in path.open(encoding="utf-8"))
            print(f"  {split:11s} wrote {count} docs to {path}")

    print("Done.")


if __name__ == "__main__":
    main()
