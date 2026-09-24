"""Download LINNAEUS (bigbio_kb) into benchmarks/data/linnaeus/ as one JSONL file.

    uv run python benchmarks/scripts/linnaeus.py

The Hugging Face loader for LINNAEUS (bigbio/linnaeus) has two problems.
This script still uses it, but fixes both:

1. Documents without species are dropped. The loader skips every document
   that has no species mentions, so it returns 95 of the 100 documents.
   Those 5 documents still matter for testing: any species an annotator
   finds in them is a false positive. We give the loader an empty list of
   annotations for them, so all 100 are kept (_load_tags_all_docs).
2. The text files are read with the wrong encoding on Windows. The files
   are UTF-8, but the loader opens them with the computer's default
   encoding, which on a Greek Windows PC is cp1253. That garbles special
   characters or crashes. We make the loader read them as UTF-8
   (_open_utf8).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Iterable

HF_DATASET = "bigbio/linnaeus"
HF_CONFIG = "linnaeus_bigbio_kb"
SPLITS = ("linnaeus",)  # LINNAEUS has no splits: the whole corpus is one file, linnaeus.jsonl
# The HF loader still has to name a split and puts all docs under "train".
HF_SPLITS = {"linnaeus": "train"}


def _find_project_root() -> Path | None:
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "pyproject.toml").exists():
            return parent
    return None


def _default_data_dir() -> Path:
    root = _find_project_root()
    base = root if root is not None else Path.cwd()
    return base / "benchmarks" / "data" / "linnaeus"


def _split_file(data_dir: Path, split: str) -> Path:
    return data_dir / f"{split}.jsonl"


def _write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, default=str))
            handle.write("\n")


def download_split(split: str, data_dir: Path) -> Path:
    """Build the corpus with the patched HF loader and persist it as JSONL on disk."""
    try:
        from datasets import load_dataset_builder
    except ImportError as exc:
        raise ImportError(
            "Downloading LINNAEUS requires the optional 'datasets' dependency. "
            "Install with: uv sync --extra benchmarks"
        ) from exc

    builder = load_dataset_builder(HF_DATASET, name=HF_CONFIG, trust_remote_code=True)
    load_tags = type(builder)._load_tags

    def _load_tags_all_docs(path: Path) -> dict:
        """Same as the loader's `_load_tags`, plus an empty list for untagged documents."""
        tags = load_tags(path)
        for txt_file in (Path(path).parent / "txt").glob("*txt"):
            tags.setdefault(txt_file.stem, [])
        return tags

    type(builder)._load_tags = staticmethod(_load_tags_all_docs)

    def _open_utf8(file, mode="r", *args, **kwargs):
        """`open` for the loader's module that reads text files as UTF-8."""
        if "b" not in mode:
            kwargs.setdefault("encoding", "utf-8")
        return open(file, mode, *args, **kwargs)

    sys.modules[type(builder).__module__].open = _open_utf8

    # Rebuild even if an unpatched version is already in the HF cache.
    builder.download_and_prepare(download_mode="force_redownload")
    ds = builder.as_dataset(split=HF_SPLITS[split])

    target = _split_file(data_dir, split)
    _write_jsonl(target, (dict(row) for row in ds))
    return target


def main() -> None:
    data_dir = _default_data_dir()
    print(f"LINNAEUS target directory: {data_dir}")

    for split in SPLITS:
        target = _split_file(data_dir, split)
        if target.exists():
            count = sum(1 for _ in target.open(encoding="utf-8"))
            print(f"  {split:11s} already present ({count} docs) at {target}")
            continue
        print(f"  {split:11s} downloading from {HF_DATASET} ...")
        path = download_split(split, data_dir)
        count = sum(1 for _ in path.open(encoding="utf-8"))
        print(f"  {split:11s} wrote {count} docs to {path}")

    print("Done.")


if __name__ == "__main__":
    main()
