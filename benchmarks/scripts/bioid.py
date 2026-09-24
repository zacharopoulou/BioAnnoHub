"""Download BioID (bigbio_kb) into benchmarks/data/bioid/ as one JSONL file.

    uv run python benchmarks/scripts/bioid.py

The Hugging Face loader for BioID (bigbio/bioid) is broken in four ways.
This script still uses it, but fixes each problem:

1. The download link is dead. The loader downloads the data from the
   BioCreative website, which now blocks every request. The Internet
   Archive saved a copy of the same file in 2022, so we download it from
   there instead (ARCHIVE_URL).
2. Most annotations were thrown away. Each figure caption has several
   annotated entities, but a bug in the loader kept only the last one per
   caption, so 102,717 annotations became 13,573. We replace that part of
   the loader with a fixed version that keeps all of them
   (_load_annotations_fixed).
3. The loader crashes with the pandas version we use, because it was
   written for an older one. We switch pandas back to its older behavior
   while the loader runs.
4. Some entities got the wrong type. BioID links cell parts such as
   mitochondria, nucleus or ER to the GO database, and the loader labels
   everything linked to GO as a gene. We label them "subcellular" instead,
   which is the label BioID itself uses for cell parts.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Iterable

HF_DATASET = "bigbio/bioid"
HF_CONFIG = "bioid_bigbio_kb"
SPLITS = ("bioid",)  # BioID has no splits: the whole released corpus is one file, bioid.jsonl
# The HF loader still has to name a split and puts all captions under "train".
HF_SPLITS = {"bioid": "train"}
ARCHIVE_URL = (
    "https://web.archive.org/web/20220725034815id_/"
    "https://biocreative.bioinformatics.udel.edu/media/store/files/2017/BioIDtraining_2.tar.gz"
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
    return base / "benchmarks" / "data" / "bioid"


def _split_file(data_dir: Path, split: str) -> Path:
    return data_dir / f"{split}.jsonl"


def _write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, default=str))
            handle.write("\n")


def _load_annotations_fixed(self, path: str) -> dict[str, dict]:
    """Same as bigbio's `load_annotations`, but keeps every row of a caption."""
    import pandas as pd

    df = pd.read_csv(path, sep=",", low_memory=False)
    df.fillna(-1, inplace=True)

    annotations: dict[str, dict] = {}
    for record in df.to_dict("records"):
        article_id = str(record["don_article"])
        annotations.setdefault(article_id, {}).setdefault(record["figure"], []).append(record)
    return annotations


def download_split(split: str, data_dir: Path) -> Path:
    """Build the corpus with the patched HF loader and persist it as JSONL on disk."""
    try:
        import pandas as pd
        from datasets import load_dataset_builder
    except ImportError as exc:
        raise ImportError(
            "Downloading BioID requires the optional 'datasets' dependency. "
            "Install with: uv sync --extra benchmarks"
        ) from exc

    pd.set_option("future.infer_string", False)

    builder = load_dataset_builder(HF_DATASET, name=HF_CONFIG, trust_remote_code=True)
    module = sys.modules[type(builder).__module__]
    module._URLS["bioid"] = ARCHIVE_URL
    type(builder).load_annotations = _load_annotations_fixed
    type(builder).DB_NAME_TO_ENTITY_TYPE = {
        **type(builder).DB_NAME_TO_ENTITY_TYPE,
        "GO": "subcellular",
    }

    # Rebuild even if an unpatched version is already in the HF cache.
    builder.download_and_prepare(download_mode="force_redownload")
    ds = builder.as_dataset(split=HF_SPLITS[split])

    target = _split_file(data_dir, split)
    _write_jsonl(target, (dict(row) for row in ds))
    return target


def main() -> None:
    data_dir = _default_data_dir()
    print(f"BioID target directory: {data_dir}")

    for split in SPLITS:
        target = _split_file(data_dir, split)
        if target.exists():
            count = sum(1 for _ in target.open(encoding="utf-8"))
            print(f"  {split:11s} already present ({count} docs) at {target}")
            continue
        print(f"  {split:11s} downloading from {HF_DATASET} (Internet Archive source) ...")
        path = download_split(split, data_dir)
        count = sum(1 for _ in path.open(encoding="utf-8"))
        print(f"  {split:11s} wrote {count} docs to {path}")

    print("Done.")


if __name__ == "__main__":
    main()
