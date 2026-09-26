"""Download the English part of the Mantra GSC into benchmarks/data/mantra/ as JSONL files.

    uv run python benchmarks/scripts/mantra.py

The Mantra Gold Standard Corpus has 5 languages and 3 kinds of text, and no
train/test split. Only the English texts are used here (the annotators in
this project work on English), and each kind of text is written to its own
file:

- mantra_en_medline.jsonl:  titles of Medline abstracts
- mantra_en_emea.jsonl:     sentences from EMEA drug labels
- mantra_en_patents.jsonl:  claims from biomedical patents

The Hugging Face loader (bigbio/mantra_gsc) reads the text files with the
computer's default encoding instead of UTF-8. On a Greek Windows PC that is
cp1253, which garbles characters such as the é in México (and shifts every
offset after it) or crashes. We make the loader read them as UTF-8 while it
runs (_utf8_path_open).

Entity types are UMLS semantic groups (DISO, CHEM, ANAT, ...). A few
annotations in the original data use a UMLS semantic type name instead (for
example "Manufactured Object"). Each of those belongs to one semantic group,
so we replace it with that group (TYPE_TO_GROUP).
"""

from __future__ import annotations

import json
import pathlib
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterable

HF_DATASET = "bigbio/mantra_gsc"
# Output file name -> Hugging Face config. The loader puts everything in "train".
SPLITS = ("mantra_en_medline", "mantra_en_emea", "mantra_en_patents")
HF_CONFIGS = {
    "mantra_en_medline": "mantra_gsc_en_medline_bigbio_kb",
    "mantra_en_emea": "mantra_gsc_en_emea_bigbio_kb",
    "mantra_en_patents": "mantra_gsc_en_patents_bigbio_kb",
}
HF_SPLIT = "train"
# UMLS semantic type names found in the data -> their UMLS semantic group.
TYPE_TO_GROUP = {
    "Manufactured Object": "OBJC",
    "Research Device": "DEVI",
    "Research Activity": "PROC",
    "Mental or Behavioral Dysfunction": "DISO",
    "Amino Acid, Peptide, or Protein|Enzyme|Receptor": "CHEM",
}


def _find_project_root() -> Path | None:
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "pyproject.toml").exists():
            return parent
    return None


def _default_data_dir() -> Path:
    root = _find_project_root()
    base = root if root is not None else Path.cwd()
    return base / "benchmarks" / "data" / "mantra"


def _split_file(data_dir: Path, split: str) -> Path:
    return data_dir / f"{split}.jsonl"


def _write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, default=str))
            handle.write("\n")


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


def download_split(split: str, data_dir: Path) -> Path:
    """Build one part with the HF loader (reading UTF-8) and persist it as JSONL."""
    try:
        from datasets import load_dataset
    except ImportError as exc:
        raise ImportError(
            "Downloading Mantra requires the optional 'datasets' dependency. "
            "Install with: uv sync --extra benchmarks"
        ) from exc

    with _utf8_path_open():
        # Rebuild even if a version read with the wrong encoding is in the HF cache.
        ds = load_dataset(
            HF_DATASET,
            name=HF_CONFIGS[split],
            split=HF_SPLIT,
            trust_remote_code=True,
            download_mode="force_redownload",
        )
    target = _split_file(data_dir, split)
    _write_jsonl(target, (_map_types(dict(row)) for row in ds))
    return target


def _map_types(row: dict[str, Any]) -> dict[str, Any]:
    for entity in row["entities"]:
        entity["type"] = TYPE_TO_GROUP.get(entity["type"], entity["type"])
    return row


def main() -> None:
    data_dir = _default_data_dir()
    print(f"Mantra target directory: {data_dir}")

    for split in SPLITS:
        target = _split_file(data_dir, split)
        if target.exists():
            count = sum(1 for _ in target.open(encoding="utf-8"))
            print(f"  {split:18s} already present ({count} docs) at {target}")
            continue
        print(f"  {split:18s} downloading from {HF_DATASET} ...")
        path = download_split(split, data_dir)
        count = sum(1 for _ in path.open(encoding="utf-8"))
        print(f"  {split:18s} wrote {count} docs to {path}")

    print("Done.")


if __name__ == "__main__":
    main()
