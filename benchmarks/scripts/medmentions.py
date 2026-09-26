"""Download MedMentions (bigbio_kb) into benchmarks/data/medmentions/ as JSONL splits.

    uv run python benchmarks/scripts/medmentions.py

MedMentions comes in two versions with the same abstracts and the same
official train/dev/test split, and both are written here:

- st21pv: mentions of 21 UMLS semantic types from a set of preferred
  vocabularies. This is the version the authors recommend as a benchmark.
  Files: st21pv_train.jsonl, st21pv_validation.jsonl, st21pv_test.jsonl
- full: mentions of any UMLS concept (127 semantic types).
  Files: full_train.jsonl, full_validation.jsonl, full_test.jsonl
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable

HF_DATASET = "bigbio/medmentions"
VERSIONS = ("st21pv", "full")
HF_SPLITS = ("train", "validation", "test")
# Output file name -> (Hugging Face config, Hugging Face split).
SPLITS = tuple(f"{version}_{split}" for version in VERSIONS for split in HF_SPLITS)


def _find_project_root() -> Path | None:
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "pyproject.toml").exists():
            return parent
    return None


def _default_data_dir() -> Path:
    root = _find_project_root()
    base = root if root is not None else Path.cwd()
    return base / "benchmarks" / "data" / "medmentions"


def _split_file(data_dir: Path, split: str) -> Path:
    return data_dir / f"{split}.jsonl"


def _write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, default=str))
            handle.write("\n")


def download_split(split: str, data_dir: Path) -> Path:
    """Pull one version and split from Hugging Face and persist it as JSONL on disk."""
    try:
        from datasets import load_dataset
    except ImportError as exc:
        raise ImportError(
            "Downloading MedMentions requires the optional 'datasets' dependency. "
            "Install with: uv sync --extra benchmarks"
        ) from exc

    version, hf_split = split.split("_", 1)
    ds = load_dataset(
        HF_DATASET,
        name=f"medmentions_{version}_bigbio_kb",
        split=hf_split,
        trust_remote_code=True,
    )
    target = _split_file(data_dir, split)
    _write_jsonl(target, (dict(row) for row in ds))
    return target


def main() -> None:
    data_dir = _default_data_dir()
    print(f"MedMentions target directory: {data_dir}")

    for split in SPLITS:
        target = _split_file(data_dir, split)
        if target.exists():
            count = sum(1 for _ in target.open(encoding="utf-8"))
            print(f"  {split:17s} already present ({count} docs) at {target}")
            continue
        print(f"  {split:17s} downloading from {HF_DATASET} ...")
        path = download_split(split, data_dir)
        count = sum(1 for _ in path.open(encoding="utf-8"))
        print(f"  {split:17s} wrote {count} docs to {path}")

    print("Done.")


if __name__ == "__main__":
    main()
