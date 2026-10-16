"""Download MACCROBAT2020 into benchmarks/data/maccrobat/ as one JSONL file.

    uv run python benchmarks/scripts/maccrobat.py

MACCROBAT is not part of BigBIO. This script downloads the original release
(MACCROBAT2020.zip from figshare, CC BY 4.0) and converts its brat files to
the same bigbio_kb layout as the other benchmarks. It needs no extra
dependencies.

The original release is used instead of the Hugging Face copy
(singh-aditya/MACCROBAT_biomedical_ner), because that copy lost 394 of the
25,189 annotations in its processing, renamed the types to upper case and
dropped the PubMed IDs. Here each document keeps its PubMed ID, and every
annotation is kept with its original type.
"""

from __future__ import annotations

import io
import json
import urllib.request
import zipfile
from pathlib import Path
from typing import Any, Iterable

SOURCE_URL = "https://ndownloader.figshare.com/files/21489405"  # MACCROBAT2020.zip
SPLITS = ("maccrobat",)  # MACCROBAT has no splits: the whole corpus is one file, maccrobat.jsonl


def _find_project_root() -> Path | None:
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "pyproject.toml").exists():
            return parent
    return None


def _default_data_dir() -> Path:
    root = _find_project_root()
    base = root if root is not None else Path.cwd()
    return base / "benchmarks" / "data" / "maccrobat"


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
        term_id, type_and_offsets, surface = line.split("\t", 2)
        entity_type, _, offsets_raw = type_and_offsets.partition(" ")
        offsets = []
        for fragment in offsets_raw.split(";"):
            start, end = (int(x) for x in fragment.split())
            if doc_text[start:end].strip() != doc_text[start:end]:
                # A few spans include a space at an edge (often a Unicode space
                # such as U+2005); move the offsets in so they cover the words only.
                start += len(doc_text[start:end]) - len(doc_text[start:end].lstrip())
                end -= len(doc_text[start:end]) - len(doc_text[start:end].rstrip())
            offsets.append([start, end])
        fragments = [doc_text[start:end] for start, end in offsets]
        # Compare with all runs of whitespace (including Unicode spaces) as one space.
        if " ".join(" ".join(fragments).split()) != " ".join(surface.split()):
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
    return {
        "id": doc_id,
        "document_id": doc_id,
        "passages": [{"id": f"{doc_id}_text", "type": "case_report", "text": [text], "offsets": [[0, len(text)]]}],
        "entities": _parse_ann(ann_text, text, doc_id),
        "events": [],
        "coreferences": [],
        "relations": [],
    }


def download_split(split: str, data_dir: Path) -> Path:
    """Download MACCROBAT2020.zip, convert every case report and persist it as JSONL."""
    with urllib.request.urlopen(SOURCE_URL, timeout=300) as response:
        archive = zipfile.ZipFile(io.BytesIO(response.read()))
    names = sorted(n for n in archive.namelist() if n.endswith(".txt") and "__MACOSX" not in n)
    rows = []
    for name in names:
        doc_id = Path(name).stem
        text = archive.read(name).decode("utf-8")
        ann_text = archive.read(name[:-4] + ".ann").decode("utf-8")
        rows.append(_to_bigbio_kb(doc_id, text, ann_text))
    target = _split_file(data_dir, split)
    _write_jsonl(target, rows)
    return target


def main() -> None:
    data_dir = _default_data_dir()
    print(f"MACCROBAT target directory: {data_dir}")

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
