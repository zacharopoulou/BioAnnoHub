"""Download CRAFT (bigbio_kb) into benchmarks/data/craft/ as JSONL splits.

    uv run python benchmarks/scripts/craft.py

The Hugging Face loader for CRAFT (bigbio/craft) has two problems on
Windows. This script still uses it, but fixes both:

1. The download cannot be unpacked. The CRAFT archive contains a few files
   with very long paths, and inside the Hugging Face cache folder they go
   over the Windows limit of 260 characters, so unpacking stops early and
   most annotation folders are missing. We download the archive ourselves
   and unpack only the files the loader uses (the article texts, the split
   lists and one annotation folder per ontology), whose paths are short,
   into a temporary folder. Then we point the loader at that folder
   (_extract_needed_files).
2. The article texts are read with the wrong encoding. The files are
   UTF-8, but the loader opens them with the computer's default encoding,
   which on a Greek Windows PC is cp1253. That garbles special characters
   or crashes. We make the loader read them as UTF-8 (_open_utf8).
"""

from __future__ import annotations

import io
import json
import sys
import tempfile
import urllib.request
import zipfile
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable

HF_DATASET = "bigbio/craft"
HF_CONFIG = "craft_bigbio_kb"
SPLITS = ("train", "validation", "test")
CRAFT_URL = "https://github.com/UCDenver-ccp/CRAFT/archive/refs/tags/v5.0.2.zip"
# One knowtator folder per ontology, the same ones the loader reads.
ONTOLOGIES = ("CHEBI", "CL", "GO_BP", "GO_CC", "GO_MF", "MOP", "NCBITaxon", "PR", "SO", "UBERON")
NEEDED_PREFIXES = (
    "CRAFT-5.0.2/articles/txt/",
    "CRAFT-5.0.2/articles/ids/",
    "CRAFT-5.0.2/concept-annotation/MONDO/MONDO_without_genotype_annotations/knowtator-2/",
    *(f"CRAFT-5.0.2/concept-annotation/{name}/{name}/knowtator/" for name in ONTOLOGIES),
)


def _find_project_root() -> Path | None:
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "pyproject.toml").exists():
            return parent
    return None


def _default_data_dir() -> Path:
    root = _find_project_root()
    base = root if root is not None else Path.cwd()
    return base / "benchmarks" / "data" / "craft"


def _split_file(data_dir: Path, split: str) -> Path:
    return data_dir / f"{split}.jsonl"


def _write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, default=str))
            handle.write("\n")


def _extract_needed_files(target_dir: Path) -> None:
    """Download the CRAFT archive and unpack only the files the loader reads."""
    with urllib.request.urlopen(CRAFT_URL, timeout=300) as response:
        archive = zipfile.ZipFile(io.BytesIO(response.read()))
    members = [
        name
        for name in archive.namelist()
        if name.startswith(NEEDED_PREFIXES) and not name.endswith("/")
    ]
    archive.extractall(target_dir, members=members)


@lru_cache(maxsize=1)
def _prepared_builder():
    """Build all CRAFT splits once with the patched HF loader."""
    try:
        from datasets import load_dataset_builder
    except ImportError as exc:
        raise ImportError(
            "Downloading CRAFT requires the optional 'datasets' dependency. "
            "Install with: uv sync --extra benchmarks"
        ) from exc

    builder = load_dataset_builder(HF_DATASET, name=HF_CONFIG, trust_remote_code=True)
    module = sys.modules[type(builder).__module__]

    def _open_utf8(file, mode="r", *args, **kwargs):
        """`open` for the loader's module that reads text files as UTF-8."""
        if "b" not in mode:
            kwargs.setdefault("encoding", "utf-8")
        return open(file, mode, *args, **kwargs)

    module.open = _open_utf8

    split_generators = type(builder)._split_generators

    with tempfile.TemporaryDirectory() as tmp:
        _extract_needed_files(Path(tmp))

        def _split_generators_local(self, dl_manager):
            """The loader's own split setup, reading our unpacked folder instead of downloading."""
            dl_manager.download_and_extract = lambda urls: tmp
            return split_generators(self, dl_manager)

        type(builder)._split_generators = _split_generators_local
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
    print(f"CRAFT target directory: {data_dir}")

    for split in SPLITS:
        target = _split_file(data_dir, split)
        if target.exists():
            count = sum(1 for _ in target.open(encoding="utf-8"))
            print(f"  {split:11s} already present ({count} docs) at {target}")
            continue
        print(f"  {split:11s} downloading from {CRAFT_URL} ...")
        path = download_split(split, data_dir)
        count = sum(1 for _ in path.open(encoding="utf-8"))
        print(f"  {split:11s} wrote {count} docs to {path}")

    print("Done.")


if __name__ == "__main__":
    main()
