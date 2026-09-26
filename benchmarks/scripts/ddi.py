"""Download the DDI corpus (bigbio_kb) into benchmarks/data/ddi/ as JSONL splits.

    uv run python benchmarks/scripts/ddi.py

The DDI 2013 corpus has two different test sets: one for the drug NER task
(112 documents) and one for the drug-drug interaction task (191 documents).
The Hugging Face loader (bigbio/ddi_corpus) puts both into its "test"
split. For an NER benchmark we want the official NER test set, so this
script keeps only the 112 documents listed in the "Test for DrugNER task"
folder of the original XML release (_drugner_test_ids). The file names in
that folder are the same as the document IDs in the loader.
"""

from __future__ import annotations

import io
import json
import urllib.request
import zipfile
from pathlib import Path
from typing import Any, Iterable

HF_DATASET = "bigbio/ddi_corpus"
HF_CONFIG = "ddi_corpus_bigbio_kb"
SPLITS = ("train", "test")  # the DDI corpus has no validation split
SOURCE_COMMIT = "819b0fa538ed83ab2a8b4f5417bba3c03249b7f3"
XML_RELEASE_URL = (
    f"https://github.com/isegura/DDICorpus/raw/{SOURCE_COMMIT}/DDICorpus-2013.zip"
)
DRUGNER_TEST_FOLDER = "Test for DrugNER task"


def _find_project_root() -> Path | None:
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "pyproject.toml").exists():
            return parent
    return None


def _default_data_dir() -> Path:
    root = _find_project_root()
    base = root if root is not None else Path.cwd()
    return base / "benchmarks" / "data" / "ddi"


def _split_file(data_dir: Path, split: str) -> Path:
    return data_dir / f"{split}.jsonl"


def _write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, default=str))
            handle.write("\n")


def _drugner_test_ids() -> set[str]:
    """Document IDs of the official drug NER test set, from the XML release."""
    with urllib.request.urlopen(XML_RELEASE_URL, timeout=300) as response:
        archive = zipfile.ZipFile(io.BytesIO(response.read()))
    return {
        Path(name).stem
        for name in archive.namelist()
        if f"/{DRUGNER_TEST_FOLDER}/" in name and name.endswith(".xml")
    }


def download_split(split: str, data_dir: Path) -> Path:
    """Pull one split from Hugging Face and persist it as JSONL on disk."""
    try:
        from datasets import load_dataset
    except ImportError as exc:
        raise ImportError(
            "Downloading the DDI corpus requires the optional 'datasets' dependency. "
            "Install with: uv sync --extra benchmarks"
        ) from exc

    ds = load_dataset(
        HF_DATASET,
        name=HF_CONFIG,
        split=split,
        trust_remote_code=True,
    )
    rows: Iterable[dict[str, Any]] = (dict(row) for row in ds)
    if split == "test":
        keep = _drugner_test_ids()
        rows = (row for row in rows if row["document_id"] in keep)
    target = _split_file(data_dir, split)
    _write_jsonl(target, rows)
    return target


def main() -> None:
    data_dir = _default_data_dir()
    print(f"DDI target directory: {data_dir}")

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
