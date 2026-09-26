"""Download the ChEBI corpus (bigbio_kb) into benchmarks/data/chebi/ as JSONL files.

    uv run python benchmarks/scripts/chebi.py

The ChEBI corpus has no train/test split. It has three parts, and each one
is written to its own file:

- chebi_fullpaper.jsonl:       100 full papers
- chebi_abstracts_ann1.jsonl:  199 abstracts, annotated by annotator 1
- chebi_abstracts_ann2.jsonl:  the same 199 abstracts, annotated by annotator 2

About 1% of the entity spans in the original files include extra spaces at
the end (for example the offsets cover "enzyme  " while the mention is
"enzyme"). An annotator that tags "enzyme" correctly would then be scored
wrong under strict matching, so this script moves those offsets in to the
first and last non-space character (_trim_offsets).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable

HF_DATASET = "bigbio/chebi_nactem"
# Output file name -> Hugging Face config. The loader puts everything in "train".
SPLITS = ("chebi_fullpaper", "chebi_abstracts_ann1", "chebi_abstracts_ann2")
HF_CONFIGS = {
    "chebi_fullpaper": "chebi_nactem_fullpaper_bigbio_kb",
    "chebi_abstracts_ann1": "chebi_nactem_abstr_ann1_bigbio_kb",
    "chebi_abstracts_ann2": "chebi_nactem_abstr_ann2_bigbio_kb",
}
HF_SPLIT = "train"


def _find_project_root() -> Path | None:
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "pyproject.toml").exists():
            return parent
    return None


def _default_data_dir() -> Path:
    root = _find_project_root()
    base = root if root is not None else Path.cwd()
    return base / "benchmarks" / "data" / "chebi"


def _split_file(data_dir: Path, split: str) -> Path:
    return data_dir / f"{split}.jsonl"


def _write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, default=str))
            handle.write("\n")


def _trim_offsets(row: dict[str, Any]) -> dict[str, Any]:
    """Move each entity fragment's offsets in past leading and trailing spaces."""
    text = "".join(t for passage in row["passages"] for t in passage["text"])
    for entity in row["entities"]:
        trimmed = []
        for start, end in entity["offsets"]:
            while start < end and text[start].isspace():
                start += 1
            while end > start and text[end - 1].isspace():
                end -= 1
            trimmed.append([start, end])
        entity["offsets"] = trimmed
    return row


def download_split(split: str, data_dir: Path) -> Path:
    """Pull one part from Hugging Face, trim its offsets and persist it as JSONL."""
    try:
        from datasets import load_dataset
    except ImportError as exc:
        raise ImportError(
            "Downloading the ChEBI corpus requires the optional 'datasets' dependency. "
            "Install with: uv sync --extra benchmarks"
        ) from exc

    ds = load_dataset(
        HF_DATASET,
        name=HF_CONFIGS[split],
        split=HF_SPLIT,
        trust_remote_code=True,
    )
    target = _split_file(data_dir, split)
    _write_jsonl(target, (_trim_offsets(dict(row)) for row in ds))
    return target


def main() -> None:
    data_dir = _default_data_dir()
    print(f"ChEBI target directory: {data_dir}")

    for split in SPLITS:
        target = _split_file(data_dir, split)
        if target.exists():
            count = sum(1 for _ in target.open(encoding="utf-8"))
            print(f"  {split:21s} already present ({count} docs) at {target}")
            continue
        print(f"  {split:21s} downloading from {HF_DATASET} ...")
        path = download_split(split, data_dir)
        count = sum(1 for _ in path.open(encoding="utf-8"))
        print(f"  {split:21s} wrote {count} docs to {path}")

    print("Done.")


if __name__ == "__main__":
    main()
