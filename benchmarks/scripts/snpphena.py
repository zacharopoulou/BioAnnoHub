"""Download the SNPPhenA corpus into benchmarks/data/snpphena/ as JSONL splits.

    uv run python benchmarks/scripts/snpphena.py

SNPPhenA is not on Hugging Face, so this script downloads the brat version
from figshare (SNPPhenA_BRAT.zip, CC BY 4.0) and converts it to the same
bigbio_kb layout as the other benchmarks. It needs no extra dependencies.

Each document is one sentence. Only the SNP and Phenotype annotations are
used; the annotations that mark modality, negation cues and negation scope
are not named entities, so they are left out (KEEP_TYPES). The text is
kept exactly as released, including its non-breaking spaces.
"""

from __future__ import annotations

import io
import json
import urllib.request
import zipfile
from pathlib import Path
from typing import Any, Iterable

SOURCE_URL = "https://ndownloader.figshare.com/files/7644445"  # SNPPhenA_BRAT.zip
SPLITS = ("train", "test")  # SNPPhenA has no validation split
SOURCE_DIRS = {"train": "Train", "test": "Test"}
KEEP_TYPES = {"SNP", "Phenotype"}


def _find_project_root() -> Path | None:
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "pyproject.toml").exists():
            return parent
    return None


def _default_data_dir() -> Path:
    root = _find_project_root()
    base = root if root is not None else Path.cwd()
    return base / "benchmarks" / "data" / "snpphena"


def _split_file(data_dir: Path, split: str) -> Path:
    return data_dir / f"{split}.jsonl"


def _write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, default=str))
            handle.write("\n")


def _parse_ann(ann_text: str, doc_text: str, doc_id: str) -> list[dict[str, Any]]:
    """Convert the SNP and Phenotype T-lines into bigbio_kb entities, checking each offset."""
    entities = []
    for line in ann_text.splitlines():
        if not line.startswith("T"):
            continue
        term_id, type_and_offsets, surface = line.split("\t")
        entity_type, _, offsets_raw = type_and_offsets.partition(" ")
        if entity_type not in KEEP_TYPES:
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
    return {
        "id": doc_id,
        "document_id": doc_id,
        "passages": [{"id": f"{doc_id}_s", "type": "sentence", "text": [text], "offsets": [[0, len(text)]]}],
        "entities": _parse_ann(ann_text, text, doc_id),
        "events": [],
        "coreferences": [],
        "relations": [],
    }


def download_all(data_dir: Path, splits: Iterable[str]) -> dict[str, Path]:
    """Download the corpus once and write the requested splits as JSONL."""
    with urllib.request.urlopen(SOURCE_URL, timeout=300) as response:
        archive = zipfile.ZipFile(io.BytesIO(response.read()))

    written = {}
    for split in splits:
        prefix = f"SNPPhenA_BRAT/{SOURCE_DIRS[split]}/"
        names = sorted(n for n in archive.namelist() if n.startswith(prefix) and n.endswith(".txt"))
        rows = []
        for name in names:
            doc_id = Path(name).stem
            text = archive.read(name).decode("utf-8")
            ann_text = archive.read(name[:-4] + ".ann").decode("utf-8")
            rows.append(_to_bigbio_kb(doc_id, text, ann_text))
        target = _split_file(data_dir, split)
        _write_jsonl(target, rows)
        written[split] = target
    return written


def main() -> None:
    data_dir = _default_data_dir()
    print(f"SNPPhenA target directory: {data_dir}")

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
