"""Download the ChEBI corpus (bigbio_kb) into benchmarks/data/chebi/ as JSONL files.

    uv run python benchmarks/scripts/chebi.py

No train/test split-> three files: chebi_fullpaper (100 papers),
chebi_abstracts_ann1 and chebi_abstracts_ann2 (the same 199 abstracts, two annotators).

- In the source, some mentions' positions include spaces after the word
  ("enzyme  " instead of "enzyme"). _trim_offsets removes those spaces from
  the positions and copies the text from the corrected positions.
- The source text files are UTF-8, but on Windows they are read with another
  encoding and the download crashes. _utf8_xopen makes them be read as UTF-8.
"""

from __future__ import annotations

import json
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterable

HF_DATASET = "bigbio/chebi_nactem"
# Pinned dataset version: the commit sha of the Hugging Face repo, i.e. the "sha" field of
# https://huggingface.co/api/datasets/bigbio/chebi_nactem (its latest commit when it was pinned).
HF_REVISION = "1edad51fe17c6e0321a7aaebfefecda9347783c6"
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
    """Write to <name>.part and rename it only once every row is written.

    An interrupted download then never leaves a file that looks complete.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_name(path.name + ".part")
    try:
        with partial.open("w", encoding="utf-8") as handle:
            for row in rows:
                handle.write(json.dumps(row, ensure_ascii=False, default=str))
                handle.write("\n")
        partial.replace(path)
    except BaseException:
        partial.unlink(missing_ok=True)
        raise


def _trim_offsets(row: dict[str, Any]) -> dict[str, Any]:
    """Move each entity fragment's offsets in past leading and trailing spaces, and match the text to them."""
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
        entity["text"] = [text[start:end] for start, end in trimmed]  # text taken from the trimmed offsets
    return row


@contextmanager
def _utf8_xopen():
    """Make the loader read text files as UTF-8 while it runs.

    `datasets` replaces `open` and `Path` in loader modules with its own xopen/xPath,
    so patching pathlib.Path.open has no effect here: xopen is what opens the files.
    """
    from datasets.utils import file_utils

    xopen = file_utils.xopen

    def _xopen(file, mode="r", *args, **kwargs):
        if "b" not in mode:
            kwargs.setdefault("encoding", "utf-8")
        return xopen(file, mode, *args, **kwargs)

    file_utils.xopen = _xopen
    try:
        yield
    finally:
        file_utils.xopen = xopen


def download_split(split: str, data_dir: Path) -> Path:
    """Pull one part from Hugging Face (reading UTF-8), trim its offsets and persist it as JSONL."""
    try:
        from datasets import load_dataset
    except ImportError as exc:
        raise ImportError(
            "Downloading the ChEBI corpus requires the optional 'datasets' dependency. "
            "Install with: uv sync --extra benchmarks"
        ) from exc

    with _utf8_xopen():
        ds = load_dataset(
            HF_DATASET,
            name=HF_CONFIGS[split],
            split=HF_SPLIT,
            trust_remote_code=True,
            revision=HF_REVISION,
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
