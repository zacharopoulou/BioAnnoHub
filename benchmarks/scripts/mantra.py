"""Download the English part of the Mantra GSC into benchmarks/data/mantra/ as JSONL files.

    uv run python benchmarks/scripts/mantra.py

English texts only (no train/test split), one file per kind of text:
mantra_en_medline (Medline titles), mantra_en_emea (drug label sentences)
and mantra_en_patents (patent claims).

- The loader reads files with the system encoding, which garbles non-ASCII
  text on Windows; _utf8_path_open makes it read UTF-8.
- The three parts share one fresh temporary HF cache: the source is
  downloaded once, and no wrongly encoded copy can be reused.
- A few entity types are UMLS semantic type names; TYPE_TO_GROUP maps them to
  their semantic group (DISO, CHEM, ...).
"""

from __future__ import annotations

import json
import pathlib
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterable

HF_DATASET = "bigbio/mantra_gsc"
# Pinned dataset version: the commit sha of the Hugging Face repo, i.e. the "sha" field of
# https://huggingface.co/api/datasets/bigbio/mantra_gsc (its latest commit when it was pinned).
HF_REVISION = "babc253e90d3c0c63b6f676f4021473623bf4f00"
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


def download_split(split: str, data_dir: Path, cache_dir: str | None = None) -> Path:
    """Build one part with the HF loader (reading UTF-8) and persist it as JSONL.

    cache_dir must be a fresh folder (shared between the parts of one run); without
    it, a temporary one is used for this part alone.
    """
    try:
        from datasets import load_dataset
    except ImportError as exc:
        raise ImportError(
            "Downloading Mantra requires the optional 'datasets' dependency. "
            "Install with: uv sync --extra benchmarks"
        ) from exc

    if cache_dir is None:
        with tempfile.TemporaryDirectory() as fresh_cache:
            return download_split(split, data_dir, fresh_cache)

    with _utf8_path_open():
        ds = load_dataset(
            HF_DATASET,
            name=HF_CONFIGS[split],
            split=HF_SPLIT,
            trust_remote_code=True,
            revision=HF_REVISION,
            cache_dir=cache_dir,
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

    with tempfile.TemporaryDirectory() as cache_dir:  # one fresh cache for all three parts
        for split in SPLITS:
            target = _split_file(data_dir, split)
            if target.exists():
                count = sum(1 for _ in target.open(encoding="utf-8"))
                print(f"  {split:18s} already present ({count} docs) at {target}")
                continue
            print(f"  {split:18s} downloading from {HF_DATASET} ...")
            path = download_split(split, data_dir, cache_dir)
            count = sum(1 for _ in path.open(encoding="utf-8"))
            print(f"  {split:18s} wrote {count} docs to {path}")

    print("Done.")


if __name__ == "__main__":
    main()
