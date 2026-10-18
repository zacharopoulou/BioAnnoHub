"""Download the Europe PMC full-text corpus into benchmarks/data/europepmc/ as JSONL splits.

    uv run python benchmarks/scripts/europepmc.py

This script downloads the original release from figshare
(europepmc-corpus-master.zip, CC BY 4.0) and converts it to the same
bigbio_kb layout as the other benchmarks. 

1. The annotations come from the release's JSON file
   (annotations/JSON/ner_rel_fulltext_full.json), which has every sentence
   with character offsets. 
2. The split comes from the release's IOB folders (train/dev/test):
   210 train, 45 validation and 45 test articles.
3. Each sentence is one passage, and they are joined with one space
   to make the document text, so the entity offsets are document-level.
"""

from __future__ import annotations

import io
import json
import urllib.request
import zipfile
from pathlib import Path
from typing import Any, Iterable

SOURCE_URL = "https://ndownloader.figshare.com/files/40595507"  # europepmc-corpus-master.zip
ROOT = "europepmc-corpus-master/"
ANNOTATIONS_FILE = ROOT + "annotations/JSON/ner_rel_fulltext_full.json"
SPLITS = ("train", "validation", "test")
# The release calls the validation split "dev".
SPLIT_NAMES = {"train": "train", "validation": "dev", "test": "test"}


def _find_project_root() -> Path | None:
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "pyproject.toml").exists():
            return parent
    return None


def _default_data_dir() -> Path:
    root = _find_project_root()
    base = root if root is not None else Path.cwd()
    return base / "benchmarks" / "data" / "europepmc"


def _split_file(data_dir: Path, split: str) -> Path:
    return data_dir / f"{split}.jsonl"


def _write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    """Write to <name>.part and rename it only once every row is written.

    An interrupted download then never leaves a file that looks complete.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_name(path.name + ".part")
    try:
        with partial.open("w", encoding="utf-8") as handle:
            for row in rows:
                handle.write(json.dumps(row, ensure_ascii=False, default=str))
                handle.write("\n")
        partial.replace(path)
    except BaseException:
        partial.unlink(missing_ok=True)
        raise


def _read_release() -> tuple[dict[str, Any], dict[str, list[str]]]:
    """Return (annotations by PMCID, PMCIDs by release split name) from the release zip."""
    with urllib.request.urlopen(SOURCE_URL, timeout=300) as response:
        archive = zipfile.ZipFile(io.BytesIO(response.read()))
    annotations = json.loads(archive.read(ANNOTATIONS_FILE))
    split_ids: dict[str, list[str]] = {}
    for name in sorted(archive.namelist()):
        parts = name.split("/")
        # europepmc-corpus-master/annotations/IOB/<split>/<PMCID>.tsv
        if len(parts) == 5 and parts[1:3] == ["annotations", "IOB"] and parts[4].endswith(".tsv"):
            split_ids.setdefault(parts[3], []).append(parts[4][: -len(".tsv")])
    return annotations, split_ids


def _to_bigbio_kb(uid: int, pmcid: str, sentences: list[dict[str, Any]]) -> dict[str, Any]:
    """Build one bigbio_kb document: one passage per sentence, entities with document offsets."""
    passages = []
    entities = []
    cursor = 0
    for sentence in sentences:
        text = sentence["sent"]
        mentions = sentence["ner"] or []
        if not text.strip():
            if mentions:
                raise ValueError(f"{pmcid} sentence {sentence['sid']}: blank sentence with mentions")
            continue
        passages.append(
            {
                "id": f"{pmcid}_s{sentence['sid']}",
                # Section tags such as METHODS, or two joined by a comma (RESULTS,DISCUSS).
                "type": sentence["section"].lower(),
                "text": [text],
                "offsets": [[cursor, cursor + len(text)]],
            }
        )
        for start, end, mention, entity_type in mentions:
            if text[start:end] != mention:
                raise ValueError(f"{pmcid} sentence {sentence['sid']}: {text[start:end]!r} vs {mention!r}")
            entities.append(
                {
                    "id": f"{pmcid}_T{len(entities) + 1}",
                    "type": entity_type,
                    "text": [mention],
                    "offsets": [[cursor + start, cursor + end]],
                    "normalized": [],
                }
            )
        cursor += len(text) + 1  # one space between sentences

    return {
        "id": str(uid),
        "document_id": pmcid,
        "passages": passages,
        "entities": entities,
        "events": [],
        "coreferences": [],
        "relations": [],
    }


def download_all(data_dir: Path, splits: Iterable[str]) -> dict[str, Path]:
    """Build the requested splits from the release and persist them as JSONL on disk."""
    annotations, split_ids = _read_release()

    written: dict[str, Path] = {}
    uid = 0
    for split in splits:
        rows = []
        for pmcid in split_ids[SPLIT_NAMES[split]]:
            rows.append(_to_bigbio_kb(uid, pmcid, annotations[pmcid]["annotations"]))
            uid += 1
        target = _split_file(data_dir, split)
        _write_jsonl(target, rows)
        written[split] = target
    return written


def main() -> None:
    data_dir = _default_data_dir()
    print(f"Europe PMC target directory: {data_dir}")

    missing = []
    for split in SPLITS:
        target = _split_file(data_dir, split)
        if target.exists():
            count = sum(1 for _ in target.open(encoding="utf-8"))
            print(f"  {split:11s} already present ({count} docs) at {target}")
        else:
            missing.append(split)

    if missing:
        print(f"  downloading the Europe PMC corpus from {SOURCE_URL} ...")
        for split, path in download_all(data_dir, missing).items():
            count = sum(1 for _ in path.open(encoding="utf-8"))
            print(f"  {split:11s} wrote {count} docs to {path}")

    print("Done.")


if __name__ == "__main__":
    main()
