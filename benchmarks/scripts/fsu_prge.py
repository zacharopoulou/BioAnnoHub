"""Download the FSU_PRGE corpus into benchmarks/data/fsu_prge/ as one JSONL file.

    uv run python benchmarks/scripts/fsu_prge.py

FSU_PRGE (FSU PRotein GEne corpus, JULIE Lab Jena) is not on Hugging Face.
This script downloads release v1.1 from JULIE Lab and reads the IOB export
that ships inside it (one file per abstract, one token and tag per line,
sentences separated by blank lines). It needs no extra dependencies.

IOB files have no character offsets, so the text is rebuilt the same way as
for JNLPBA: tokens are joined with single spaces (and sentences with a
space), and the B-/I- tags are merged into one entity per mention with real
character offsets into that rebuilt text (_to_bigbio_kb).
"""

from __future__ import annotations

import io
import json
import tarfile
import urllib.request
from pathlib import Path
from typing import Any, Iterable

SOURCE_URL = "https://julielab.de/downloads/resources/fsu_prge_release_v1_1.tgz"
SPLITS = ("fsu_prge",)  # FSU_PRGE has no splits: the whole corpus is one file, fsu_prge.jsonl


def _find_project_root() -> Path | None:
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "pyproject.toml").exists():
            return parent
    return None


def _default_data_dir() -> Path:
    root = _find_project_root()
    base = root if root is not None else Path.cwd()
    return base / "benchmarks" / "data" / "fsu_prge"


def _split_file(data_dir: Path, split: str) -> Path:
    return data_dir / f"{split}.jsonl"


def _write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, default=str))
            handle.write("\n")


def _read_iob(content: str) -> list[tuple[str, str]]:
    """Return (token, tag) pairs for one document; sentence breaks do not affect offsets."""
    pairs = []
    for line in content.splitlines():
        if line.strip():
            token, tag = line.split("\t")
            pairs.append((token, tag))
    return pairs


def _to_bigbio_kb(doc_id: str, subcorpus: str, pairs: list[tuple[str, str]]) -> dict[str, Any]:
    text = ""
    entities: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None

    def flush() -> None:
        nonlocal current
        if current is not None:
            entities.append(
                {
                    "id": f"{doc_id}_{len(entities)}",
                    "type": current["type"],
                    "text": [text[current["start"] : current["end"]]],
                    "offsets": [[current["start"], current["end"]]],
                    "normalized": [],
                }
            )
            current = None

    for token, tag in pairs:
        if text:
            text += " "
        start = len(text)
        text += token
        end = len(text)
        if tag == "O":
            flush()
            continue
        prefix, _, entity_type = tag.partition("-")
        if prefix == "B" or current is None or current["type"] != entity_type:
            flush()
            current = {"type": entity_type, "start": start, "end": end}
        else:  # I- continuing the same entity type
            current["end"] = end
    flush()

    return {
        "id": doc_id,
        "document_id": doc_id,
        "subcorpus": subcorpus,
        "passages": [{"id": f"{doc_id}_p0", "type": "abstract", "text": [text], "offsets": [[0, len(text)]]}],
        "entities": entities,
        "events": [],
        "coreferences": [],
        "relations": [],
    }


def download_split(split: str, data_dir: Path) -> Path:
    """Download release v1.1, convert every IOB file and persist the corpus as JSONL."""
    with urllib.request.urlopen(SOURCE_URL, timeout=300) as response:
        archive = tarfile.open(fileobj=io.BytesIO(response.read()), mode="r:gz")

    rows = []
    for member in sorted(archive.getmembers(), key=lambda m: m.name):
        path = Path(member.name)
        if not member.isfile() or path.suffix != ".iob" or path.parent.name != "iob":
            continue
        subcorpus = path.parent.parent.name
        content = archive.extractfile(member).read().decode("utf-8")
        rows.append(_to_bigbio_kb(path.stem, subcorpus, _read_iob(content)))

    target = _split_file(data_dir, split)
    _write_jsonl(target, rows)
    return target


def main() -> None:
    data_dir = _default_data_dir()
    print(f"FSU_PRGE target directory: {data_dir}")

    for split in SPLITS:
        target = _split_file(data_dir, split)
        if target.exists():
            count = sum(1 for _ in target.open(encoding="utf-8"))
            print(f"  {split:11s} already present ({count} docs) at {target}")
            continue
        print(f"  {split:11s} downloading from {SOURCE_URL} ...")
        path = download_split(split, data_dir)
        count = sum(1 for _ in path.open(encoding="utf-8"))
        print(f"  {split:11s} wrote {count} docs to {path}")

    print("Done.")


if __name__ == "__main__":
    main()
