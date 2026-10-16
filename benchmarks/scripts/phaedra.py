"""Download the PHAEDRA corpus into benchmarks/data/phaedra/ as JSONL splits.

    uv run python benchmarks/scripts/phaedra.py

PHAEDRA is not on Hugging Face, so this script downloads the brat files
from NaCTeM (PHAEDRA_corpus.tar.gz) and converts them to the same bigbio_kb
layout as the other benchmarks. It needs no extra dependencies.

The .a1 files also contain annotations that are not named entities, and
those are left out (SKIP_TYPES): cue words that mark speculation, negation
or manner, "Coreferring_mention" (words such as "he" that refer back to
another mention) and "Combination" (the word that joins drugs, such as
"and" or "plus"). The .a2 files hold the drug-effect events and are not
used. The text is kept exactly as released (it starts with some blank
lines), as one passage, so the offsets need no change.
"""

from __future__ import annotations

import io
import json
import tarfile
import urllib.request
from pathlib import Path
from typing import Any, Iterable

SOURCE_URL = "http://www.nactem.ac.uk/PHAEDRA/PHAEDRA_corpus.tar.gz"
SPLITS = ("train", "validation", "test")
# The corpus calls the validation split "dev".
SOURCE_DIRS = {"train": "train", "validation": "dev", "test": "test"}
SKIP_TYPES = {"Speculation_cue", "Negation_cue", "Manner_cue", "Coreferring_mention", "Combination"}


def _find_project_root() -> Path | None:
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "pyproject.toml").exists():
            return parent
    return None


def _default_data_dir() -> Path:
    root = _find_project_root()
    base = root if root is not None else Path.cwd()
    return base / "benchmarks" / "data" / "phaedra"


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
        term_id, type_and_offsets, surface = line.split("\t")[:3]
        entity_type, _, offsets_raw = type_and_offsets.partition(" ")
        if entity_type in SKIP_TYPES:
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
        "passages": [{"id": f"{doc_id}_text", "type": "abstract", "text": [text], "offsets": [[0, len(text)]]}],
        "entities": _parse_a1(ann_text, text, doc_id),
        "events": [],
        "coreferences": [],
        "relations": [],
    }


def download_all(data_dir: Path, splits: Iterable[str]) -> dict[str, Path]:
    """Download the corpus once and write the requested splits as JSONL."""
    with urllib.request.urlopen(SOURCE_URL, timeout=300) as response:
        archive = tarfile.open(fileobj=io.BytesIO(response.read()), mode="r:gz")
    files = {m.name: m for m in archive.getmembers() if m.isfile()}

    written = {}
    for split in splits:
        prefix = f"PHAEDRA_corpus/{SOURCE_DIRS[split]}/"
        rows = []
        for name in sorted(files):
            base = Path(name).name
            if not name.startswith(prefix) or not name.endswith(".txt") or base.startswith("._"):
                continue
            doc_id = base[:-4]
            text = archive.extractfile(files[name]).read().decode("utf-8")
            ann_text = archive.extractfile(files[name[:-4] + ".a1"]).read().decode("utf-8")
            rows.append(_to_bigbio_kb(doc_id, text, ann_text))
        target = _split_file(data_dir, split)
        _write_jsonl(target, rows)
        written[split] = target
    return written


def main() -> None:
    data_dir = _default_data_dir()
    print(f"PHAEDRA target directory: {data_dir}")

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
