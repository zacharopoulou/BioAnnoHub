"""Downloads AnatEM (bigbio_kb) into benchmarks/data/anatem/ as JSONL splits.

    uv run python benchmarks/scripts/anatem.py 

Fetches the official distribution from www.nactem.ac.uk and converts its brat
standoff annotations to bigbio_kb, so this corpus needs no `datasets` dependency.
"""

from __future__ import annotations

import argparse
import json
import shutil
import tarfile
import tempfile
import urllib.request
from pathlib import Path
from typing import Any, Iterable, Iterator

CORPUS_URL = "https://www.nactem.ac.uk/anatomytagger/AnatEM-1.0.2.tar.gz"
CORPUS_DIRNAME = "AnatEM-1.0.2"

# AnatEM names its held-out split "devel"; every other corpus script here writes
# "validation", and .gitignore expects that name.
SPLIT_SOURCE_DIRS = {"train": "train", "validation": "devel", "test": "test"}
SPLITS = tuple(SPLIT_SOURCE_DIRS)


def _find_project_root() -> Path | None:
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "pyproject.toml").exists():
            return parent
    return None


def _default_data_dir() -> Path:
    root = _find_project_root()
    base = root if root is not None else Path.cwd()
    return base / "benchmarks" / "data" / "anatem"


def _split_file(data_dir: Path, split: str) -> Path:
    return data_dir / f"{split}.jsonl"


def _write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    written = 0
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, default=str))
            handle.write("\n")
            written += 1
    return written


def fetch_corpus(cache_dir: Path) -> Path:
    """Download and extract the AnatEM distribution, reusing a cached copy."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    extracted = cache_dir / CORPUS_DIRNAME
    if (extracted / "standoff").is_dir():
        return extracted

    archive = cache_dir / "AnatEM-1.0.2.tar.gz"
    if not archive.exists():
        print(f"  downloading {CORPUS_URL} ...")
        with urllib.request.urlopen(CORPUS_URL, timeout=300) as response:
            archive.write_bytes(response.read())
        print(f"  downloaded {archive.stat().st_size} bytes")

    print(f"  extracting into {cache_dir} ...")
    with tarfile.open(archive, "r:gz") as tar:
        tar.extractall(cache_dir, filter="data")
    if not (extracted / "standoff").is_dir():
        raise RuntimeError(f"unexpected archive layout: no standoff/ under {extracted}")
    return extracted


def _parse_offsets(raw: str) -> list[list[int]]:
    """brat offsets: "112 116", or "112 116;120 125" for a discontinuous span."""
    spans = []
    for fragment in raw.split(";"):
        start, end = fragment.split()
        spans.append([int(start), int(end)])
    return spans


def parse_ann(ann_text: str, doc_text: str, doc_id: str) -> list[dict[str, Any]]:
    """Convert brat T-lines into bigbio_kb entities.

    AnatEM contains only textbound (T) annotations: no relations, events or
    normalizations, so those containers stay empty for every document.
    """
    entities: list[dict[str, Any]] = []
    for line in ann_text.splitlines():
        line = line.rstrip("\n")
        if not line or not line.startswith("T"):
            continue
        parts = line.split("\t")
        if len(parts) < 3:
            raise ValueError(f"{doc_id}: malformed brat line: {line!r}")
        term_id, type_and_offsets, surface = parts[0], parts[1], parts[2]
        entity_type, _, offsets_raw = type_and_offsets.partition(" ")
        offsets = _parse_offsets(offsets_raw)

        fragments = [doc_text[start:end] for start, end in offsets]
        # brat joins the fragments of a discontinuous span with a single space.
        if " ".join(fragments) != surface:
            raise ValueError(
                f"{doc_id}/{term_id}: offsets {offsets} yield "
                f"{' '.join(fragments)!r} but the annotation says {surface!r}"
            )

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


def iter_split_documents(corpus_dir: Path, split: str) -> Iterator[dict[str, Any]]:
    source = corpus_dir / "standoff" / SPLIT_SOURCE_DIRS[split]
    if not source.is_dir():
        raise RuntimeError(f"missing split directory: {source}")

    for txt_path in sorted(source.glob("*.txt")):
        # The distribution was packaged on macOS and carries an AppleDouble
        # resource fork ("._<name>") beside every real file. Those are binary,
        # and pathlib.Path.glob matches dotfiles (unlike the glob module), so
        # they must be filtered out explicitly or they double the document
        # count and blow up on decode.
        if txt_path.name.startswith("._"):
            continue
        doc_id = txt_path.stem
        doc_text = txt_path.read_text(encoding="utf-8")
        ann_path = txt_path.with_suffix(".ann")
        ann_text = ann_path.read_text(encoding="utf-8") if ann_path.exists() else ""

        yield {
            "id": doc_id,
            "document_id": doc_id,
            # AnatEM documents are PMC captions/sections and PubMed abstracts.
            # "abstract" is not strictly accurate for all of them, but it is the
            # passage type the previous bigbio-derived files used and what any
            # downstream passage-type filtering expects.
            "passages": [
                {
                    "id": f"{doc_id}__text",
                    "type": "abstract",
                    "text": [doc_text],
                    "offsets": [[0, len(doc_text)]],
                }
            ],
            "entities": parse_ann(ann_text, doc_text, doc_id),
            "events": [],
            "coreferences": [],
            "relations": [],
        }


def build_split(split: str, corpus_dir: Path, data_dir: Path) -> tuple[Path, int, int]:
    target = _split_file(data_dir, split)
    mentions = 0

    def rows() -> Iterator[dict[str, Any]]:
        nonlocal mentions
        for row in iter_split_documents(corpus_dir, split):
            mentions += len(row["entities"])
            yield row

    docs = _write_jsonl(target, rows())
    return target, docs, mentions


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--force",
        action="store_true",
        help="Rebuild splits even if the JSONL files already exist.",
    )
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=Path(tempfile.gettempdir()) / "anatem-corpus",
        help="Where to download and extract the AnatEM distribution.",
    )
    args = parser.parse_args()

    data_dir = _default_data_dir()
    print(f"AnatEM target directory: {data_dir}")

    pending = [
        split
        for split in SPLITS
        if args.force or not _split_file(data_dir, split).exists()
    ]
    for split in SPLITS:
        if split not in pending:
            count = sum(1 for _ in _split_file(data_dir, split).open(encoding="utf-8"))
            print(f"  {split:11s} already present ({count} docs)")

    if not pending:
        print("Done.")
        return

    corpus_dir = fetch_corpus(args.cache_dir)

    total_docs = total_mentions = 0
    for split in pending:
        target, docs, mentions = build_split(split, corpus_dir, data_dir)
        total_docs += docs
        total_mentions += mentions
        print(f"  {split:11s} wrote {docs} docs, {mentions} mentions to {target}")

    print(f"Total: {total_docs} documents, {total_mentions} entity mentions.")
    print("Done.")


if __name__ == "__main__":
    main()
