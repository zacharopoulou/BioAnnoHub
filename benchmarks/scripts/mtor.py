"""Download the mTOR pathway event corpus into benchmarks/data/mtor/ as one JSONL file.

    uv run python benchmarks/scripts/mtor.py

The corpus is not on Hugging Face, so this script downloads the original
brat standoff files from the openbiocorpora GitHub repository (pinned to a
fixed commit) and converts them to the same bigbio_kb layout as the other
benchmarks. It needs no extra dependencies.

Each document has a single .ann file that holds both the entities and the
event trigger words (such as "Phosphorylation" or "Binding"). A text
annotation is an event trigger when an event line (E...) uses it as its
trigger; those are left out (_parse_ann). The "Entity" type is left out
too, because it was only annotated when it takes part in an event, so it is
not complete.
"""

from __future__ import annotations

import io
import json
import urllib.request
import zipfile
from pathlib import Path
from typing import Any, Iterable

SOURCE_COMMIT = "59694bda18b984578fdb4da44bc3c92aa00fe44d"
SOURCE_URL = f"https://github.com/openbiocorpora/mtor-pathway/archive/{SOURCE_COMMIT}.zip"
SPLITS = ("mtor",)  # the corpus has no splits: the whole corpus is one file, mtor.jsonl
SKIP_TYPES = {"Entity"}


def _find_project_root() -> Path | None:
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "pyproject.toml").exists():
            return parent
    return None


def _default_data_dir() -> Path:
    root = _find_project_root()
    base = root if root is not None else Path.cwd()
    return base / "benchmarks" / "data" / "mtor"


def _split_file(data_dir: Path, split: str) -> Path:
    return data_dir / f"{split}.jsonl"


def _write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, default=str))
            handle.write("\n")


def _parse_ann(ann_text: str, doc_text: str, doc_id: str) -> list[dict[str, Any]]:
    """Return the entity annotations, without event triggers and without "Entity"."""
    lines = ann_text.splitlines()
    triggers = {
        line.split("\t")[1].split()[0].split(":")[1]
        for line in lines
        if line.startswith("E")
    }
    entities = []
    for line in lines:
        if not line.startswith("T"):
            continue
        term_id, type_and_offsets, surface = line.split("\t")
        entity_type, _, offsets_raw = type_and_offsets.partition(" ")
        if term_id in triggers or entity_type in SKIP_TYPES:
            continue
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
        "entities": _parse_ann(ann_text, text, doc_id),
        "events": [],
        "coreferences": [],
        "relations": [],
    }


def download_split(split: str, data_dir: Path) -> Path:
    """Download the corpus, convert every document and persist it as JSONL."""
    with urllib.request.urlopen(SOURCE_URL, timeout=300) as response:
        archive = zipfile.ZipFile(io.BytesIO(response.read()))
    prefix = f"mtor-pathway-{SOURCE_COMMIT}/original-data/mTOR-pathway-events/"
    txt_names = sorted(n for n in archive.namelist() if n.startswith(prefix) and n.endswith(".txt"))
    rows = []
    for name in txt_names:
        doc_id = Path(name).stem
        text = archive.read(name).decode("utf-8")
        ann_text = archive.read(name[:-4] + ".ann").decode("utf-8")
        rows.append(_to_bigbio_kb(doc_id, text, ann_text))
    target = _split_file(data_dir, split)
    _write_jsonl(target, rows)
    return target


def main() -> None:
    data_dir = _default_data_dir()
    print(f"mTOR target directory: {data_dir}")

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
