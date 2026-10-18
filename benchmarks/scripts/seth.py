"""Download the SETH corpus into benchmarks/data/seth/ as one JSONL file.

    uv run python benchmarks/scripts/seth.py

630 abstracts: all mutation (SNP, RS) and Gene mentions, with relations. No normalization.
"""

from __future__ import annotations

import io
import json
import tarfile
import urllib.request
from pathlib import Path
from typing import Any, Iterable

# Pinned repository version: the commit sha of rockt/SETH, i.e. the "sha" field of
# https://api.github.com/repos/rockt/SETH/commits/master (its latest commit when it was pinned).
SETH_COMMIT = "a3d7ce7d767d65865c0fa402cfb357233c8009e1"
SOURCE_URL = f"https://codeload.github.com/rockt/SETH/tar.gz/{SETH_COMMIT}"
CORPUS_DIR = "resources/SETH-corpus"
SPLITS = ("seth",)  # no splits: the whole corpus is one file, seth.jsonl


def _find_project_root() -> Path | None:
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "pyproject.toml").exists():
            return parent
    return None


def _default_data_dir() -> Path:
    root = _find_project_root()
    base = root if root is not None else Path.cwd()
    return base / "benchmarks" / "data" / "seth"


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


def _read_corpus() -> tuple[dict[str, str], dict[str, str]]:
    """Return {pmid: text} from corpus.txt and {pmid: .ann content} from the pinned repository archive."""
    with urllib.request.urlopen(SOURCE_URL, timeout=300) as response:
        archive = tarfile.open(fileobj=io.BytesIO(response.read()), mode="r:gz")
    texts, annotations = {}, {}
    for member in archive.getmembers():
        relative = member.name.split("/", 1)[-1]  # drop the "SETH-<commit>/" prefix
        if relative == f"{CORPUS_DIR}/corpus.txt":
            for line in archive.extractfile(member).read().decode("utf-8").splitlines():
                pmid, text = line.split("\t", 1)
                texts[pmid] = text
        elif relative.startswith(f"{CORPUS_DIR}/annotations/") and relative.endswith(".ann"):
            annotations[Path(relative).stem] = archive.extractfile(member).read().decode("utf-8")
    return texts, annotations


def _to_bigbio_kb(pmid: str, text: str, ann: str) -> dict[str, Any]:
    """Convert one abstract and its BRAT annotations (T = mention, R = relation; E lines repeat a mention)."""
    entities, relations = [], []
    for line in ann.splitlines():
        if line.startswith("T"):
            term_id, type_and_span, surface = line.split("\t")
            entity_type, start, end = type_and_span.split(" ")
            start, end = int(start), int(end)
            if text[start:end] != surface:
                raise ValueError(f"PMID {pmid}/{term_id}: offsets give {text[start:end]!r}, annotation says {surface!r}")
            entities.append(
                {"id": f"{pmid}_{term_id}", "type": entity_type, "text": [surface],
                 "offsets": [[start, end]], "normalized": []}
            )
        elif line.startswith("R"):
            relation_id, body = line.split("\t")[:2]
            relation_type, arg1, arg2 = body.split(" ")
            relations.append(
                {"id": f"{pmid}_{relation_id}", "type": relation_type,
                 "arg1_id": f"{pmid}_{arg1.split(':')[1]}", "arg2_id": f"{pmid}_{arg2.split(':')[1]}",
                 "normalized": []}
            )
    return {
        "id": pmid,
        "document_id": pmid,
        "passages": [{"id": f"{pmid}_text", "type": "abstract", "text": [text], "offsets": [[0, len(text)]]}],
        "entities": entities,
        "events": [],
        "coreferences": [],
        "relations": relations,
    }


def download_split(split: str, data_dir: Path) -> Path:
    """Download the pinned SETH repository, convert the corpus and persist it as JSONL."""
    texts, annotations = _read_corpus()
    if set(texts) != set(annotations):
        raise ValueError("corpus.txt and annotations/ list different PMIDs")
    target = _split_file(data_dir, split)
    _write_jsonl(target, (_to_bigbio_kb(pmid, texts[pmid], annotations[pmid]) for pmid in sorted(texts, key=int)))
    return target


def main() -> None:
    data_dir = _default_data_dir()
    print(f"SETH target directory: {data_dir}")

    for split in SPLITS:
        target = _split_file(data_dir, split)
        if target.exists():
            count = sum(1 for _ in target.open(encoding="utf-8"))
            print(f"  {split:11s} already present ({count} docs) at {target}")
            continue
        print(f"  {split:11s} downloading from GitHub (rockt/SETH) ...")
        path = download_split(split, data_dir)
        count = sum(1 for _ in path.open(encoding="utf-8"))
        print(f"  {split:11s} wrote {count} docs to {path}")

    print("Done.")


if __name__ == "__main__":
    main()
