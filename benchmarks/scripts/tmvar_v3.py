"""Download tmVar3 (bigbio_kb) into benchmarks/data/tmvar_v3/ as JSONL splits.

    uv run python benchmarks/scripts/tmvar_v3.py

The BigBIO loader downloads the corpus over FTP, which many networks block.
This script points it to the same official file over HTTPS instead (NCBI
serves its FTP folders over HTTPS too; the two files are byte-identical).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Iterable

HF_DATASET = "bigbio/tmvar_v3"
# Pinned dataset version: the commit sha of the Hugging Face repo, i.e. the "sha" field of
# https://huggingface.co/api/datasets/bigbio/tmvar_v3 (its latest commit when it was pinned).
HF_REVISION = "288f10ee20212d03e0e070bbf7c4008c21410797"
HF_CONFIG = "tmvar_v3_bigbio_kb"
SPLITS = ("tmvar_v3",)  # tmVar3 has no splits: the whole corpus is one file, tmvar_v3.jsonl
# The HF loader still has to name a split and puts all 500 docs under "test".
HF_SPLITS = {"tmvar_v3": "test"}
# Official file over HTTPS; the loader's own URL is ftp://ftp.ncbi.nlm.nih.gov/pub/lu/tmVar3/tmVar3Corpus.txt
HTTPS_URL = "https://ftp.ncbi.nlm.nih.gov/pub/lu/tmVar3/tmVar3Corpus.txt"


def _find_project_root() -> Path | None:
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "pyproject.toml").exists():
            return parent
    return None


def _default_data_dir() -> Path:
    root = _find_project_root()
    base = root if root is not None else Path.cwd()
    return base / "benchmarks" / "data" / "tmvar_v3"


def _split_file(data_dir: Path, split: str) -> Path:
    return data_dir / f"{split}.jsonl"


def _write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, default=str))
            handle.write("\n")


def download_split(split: str, data_dir: Path) -> Path:
    """Build the corpus with the HF loader, downloading over HTTPS, and persist it as JSONL on disk."""
    try:
        from datasets import load_dataset_builder
    except ImportError as exc:
        raise ImportError(
            "Downloading tmVar3 requires the optional 'datasets' dependency. "
            "Install with: uv sync --extra benchmarks"
        ) from exc

    builder = load_dataset_builder(HF_DATASET, name=HF_CONFIG, trust_remote_code=True, revision=HF_REVISION)
    module = sys.modules[type(builder).__module__]
    module._URLS["tmvar_v3"] = HTTPS_URL  # instead of the FTP address
    builder.download_and_prepare()
    ds = builder.as_dataset(split=HF_SPLITS[split])
    target = _split_file(data_dir, split)
    _write_jsonl(target, (dict(row) for row in ds))
    return target


def main() -> None:
    data_dir = _default_data_dir()
    print(f"tmVar3 target directory: {data_dir}")

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
