"""Download BioNLP11EPI (bigbio_kb) into benchmarks/data/bionlp11epi/ as JSONL splits.

    uv run python benchmarks/scripts/bionlp11epi.py

The Hugging Face loader for BioNLP11EPI (bigbio/bionlp_st_2011_epi) has two
problems. This script still uses it, but fixes both:

1. There is no test set on Hugging Face. The loader reads its own copy of
   the data (data/train.zip, data/devel.zip, data/test.zip in the Hugging
   Face repository), but test.zip only contains another copy of the
   training data, so the test split comes out empty. We download the
   original data from the openbiocorpora GitHub repository instead (pinned
   to a fixed commit) and give the loader its train, devel and test folders
   (_extract_splits).
2. The files are read with the wrong encoding on Windows. The loader opens
   them with the computer's default encoding, which on a Greek Windows PC
   is cp1253, instead of UTF-8. We make it read them as UTF-8 while it runs
   (_utf8_path_open).
"""

from __future__ import annotations

import io
import json
import pathlib
import tempfile
import urllib.request
import zipfile
from contextlib import contextmanager
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable

HF_DATASET = "bigbio/bionlp_st_2011_epi"
HF_CONFIG = "bionlp_st_2011_epi_bigbio_kb"
SPLITS = ("train", "validation", "test")
SOURCE_COMMIT = "9e9b686175015e1adc629d3ee3857be004dcd923"
SOURCE_URL = f"https://github.com/openbiocorpora/bionlp-st-2011-epi/archive/{SOURCE_COMMIT}.zip"
# The original data calls the validation split "devel".
SOURCE_DIRS = {"train": "train", "validation": "devel", "test": "test"}


def _find_project_root() -> Path | None:
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "pyproject.toml").exists():
            return parent
    return None


def _default_data_dir() -> Path:
    root = _find_project_root()
    base = root if root is not None else Path.cwd()
    return base / "benchmarks" / "data" / "bionlp11epi"


def _split_file(data_dir: Path, split: str) -> Path:
    return data_dir / f"{split}.jsonl"


def _write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, default=str))
            handle.write("\n")


def _extract_splits(target_dir: Path) -> dict[str, str]:
    """Download the original data and return the folder of each split."""
    with urllib.request.urlopen(SOURCE_URL, timeout=300) as response:
        zipfile.ZipFile(io.BytesIO(response.read())).extractall(target_dir)
    original = target_dir / f"bionlp-st-2011-epi-{SOURCE_COMMIT}" / "original-data"
    return {split: str(original / folder) for split, folder in SOURCE_DIRS.items()}


@contextmanager
def _utf8_path_open():
    """Make Path.open read text files as UTF-8 while the loader runs."""
    path_open = pathlib.Path.open

    def _open(self, mode="r", *args, **kwargs):
        if "b" not in mode:
            kwargs.setdefault("encoding", "utf-8")
        return path_open(self, mode, *args, **kwargs)

    pathlib.Path.open = _open
    try:
        yield
    finally:
        pathlib.Path.open = path_open


@lru_cache(maxsize=1)
def _prepared_builder():
    """Build all splits once with the HF loader, reading the original data."""
    try:
        from datasets import load_dataset_builder
    except ImportError as exc:
        raise ImportError(
            "Downloading BioNLP11EPI requires the optional 'datasets' dependency. "
            "Install with: uv sync --extra benchmarks"
        ) from exc

    builder = load_dataset_builder(HF_DATASET, name=HF_CONFIG, trust_remote_code=True)
    split_generators = type(builder)._split_generators

    with tempfile.TemporaryDirectory() as tmp:
        split_dirs = _extract_splits(Path(tmp))

        def _split_generators_local(self, dl_manager):
            """The loader's own split setup, reading our folders instead of its zips."""
            dl_manager.download_and_extract = lambda urls: split_dirs
            return split_generators(self, dl_manager)

        type(builder)._split_generators = _split_generators_local
        with _utf8_path_open():
            builder.download_and_prepare(download_mode="force_redownload")
    return builder


def download_split(split: str, data_dir: Path) -> Path:
    """Take one split from the prepared corpus and persist it as JSONL on disk."""
    ds = _prepared_builder().as_dataset(split=split)
    target = _split_file(data_dir, split)
    _write_jsonl(target, (dict(row) for row in ds))
    return target


def main() -> None:
    data_dir = _default_data_dir()
    print(f"BioNLP11EPI target directory: {data_dir}")

    for split in SPLITS:
        target = _split_file(data_dir, split)
        if target.exists():
            count = sum(1 for _ in target.open(encoding="utf-8"))
            print(f"  {split:11s} already present ({count} docs) at {target}")
            continue
        print(f"  {split:11s} building from {SOURCE_URL} ...")
        path = download_split(split, data_dir)
        count = sum(1 for _ in path.open(encoding="utf-8"))
        print(f"  {split:11s} wrote {count} docs to {path}")

    print("Done.")


if __name__ == "__main__":
    main()
