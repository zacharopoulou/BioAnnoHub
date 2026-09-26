"""Download the miRNA corpus into benchmarks/data/mirna/ as JSONL splits.

    uv run python benchmarks/scripts/mirna.py

The Hugging Face loader for this corpus (bigbio/mirna) cannot be used, so
this script converts the original XML files from Fraunhofer SCAI itself, in
the same bigbio_kb layout as the other benchmarks. The loader has three
problems:

1. It drops every sentence that has no annotations (183 in train, 50 in
   test), so the documents are missing part of their text.
2. The XML stores the sentences of each abstract out of order (for example
   s3, s4, s2, s5, s1, s0), and the loader keeps that order. We sort them
   by their sentence number, which gives back the real abstract: s0 is the
   title, then the abstract sentences in order.
3. It fills the normalization field with each annotation's own ID (such as
   "miRNA-corp.d0.s1.e0"), which is not a database link. The corpus has no
   normalization, so we leave the field empty.

We also leave out the "Relation_Trigger" annotations (words such as
"regulate" that signal a relation), because they are not named entities.
The XML end offsets are inclusive (the last character is part of the
mention), so 1 is added to every end offset.
"""

from __future__ import annotations

import json
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Iterable

SOURCE_BASE = "https://www.scai.fraunhofer.de/content/dam/scai/de/downloads/bioinformatik/miRNA/miRNA-"
SOURCE_FILES = {"train": "Train-Corpus.xml", "test": "Test-Corpus.xml"}
SPLITS = ("train", "test")  # the miRNA corpus has no validation split
SKIP_TYPES = {"Relation_Trigger"}


def _find_project_root() -> Path | None:
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "pyproject.toml").exists():
            return parent
    return None


def _default_data_dir() -> Path:
    root = _find_project_root()
    base = root if root is not None else Path.cwd()
    return base / "benchmarks" / "data" / "mirna"


def _split_file(data_dir: Path, split: str) -> Path:
    return data_dir / f"{split}.jsonl"


def _write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, default=str))
            handle.write("\n")


def _sentence_number(sentence: ET.Element) -> int:
    return int(sentence.get("origId").rsplit(".s", 1)[1])


def _to_bigbio_kb(document: ET.Element) -> dict[str, Any]:
    """Build one document from its sentences, in their original order."""
    pmid = document.get("origId")
    sentences = sorted(document.iter("sentence"), key=_sentence_number)

    pieces: list[str] = []  # stripped sentence texts
    starts: list[int] = []  # where each stripped sentence starts in the document text
    entities: list[dict[str, Any]] = []
    position = 0
    for sentence in sentences:
        raw = sentence.get("text")
        stripped = raw.strip()
        shift = len(raw) - len(raw.lstrip())  # leading spaces removed from this sentence
        if pieces:
            position += 1  # one space between sentences
        starts.append(position)
        pieces.append(stripped)

        for entity in sentence.iter("entity"):
            if entity.get("type") in SKIP_TYPES:
                continue
            offsets = []
            for fragment in entity.get("charOffset").split(","):
                start, end = (int(x) for x in fragment.split("-"))
                offsets.append([position + start - shift, position + end + 1 - shift])
            entities.append(
                {
                    "id": entity.get("id"),
                    "type": entity.get("type"),
                    "text": [entity.get("text")],
                    "offsets": offsets,
                    "normalized": [],
                }
            )
        position += len(stripped)

    text = " ".join(pieces)
    for entity in entities:
        found = " ".join(text[start:end] for start, end in entity["offsets"])
        if found != entity["text"][0]:
            raise ValueError(f"PMID {pmid}: {entity['text'][0]!r} vs {found!r}")

    title_end = len(pieces[0])
    return {
        "id": pmid,
        "document_id": pmid,
        "passages": [
            {"id": f"{pmid}_title", "type": "title", "text": [pieces[0]], "offsets": [[0, title_end]]},
            {
                "id": f"{pmid}_abstract",
                "type": "abstract",
                "text": [text[title_end + 1 :]],
                "offsets": [[title_end + 1, len(text)]],
            },
        ],
        "entities": entities,
        "events": [],
        "coreferences": [],
        "relations": [],
    }


def download_split(split: str, data_dir: Path) -> Path:
    """Download one XML file from Fraunhofer SCAI, convert it and persist it as JSONL."""
    with urllib.request.urlopen(SOURCE_BASE + SOURCE_FILES[split], timeout=300) as response:
        root = ET.fromstring(response.read())
    target = _split_file(data_dir, split)
    _write_jsonl(target, (_to_bigbio_kb(document) for document in root.iter("document")))
    return target


def main() -> None:
    data_dir = _default_data_dir()
    print(f"miRNA target directory: {data_dir}")

    for split in SPLITS:
        target = _split_file(data_dir, split)
        if target.exists():
            count = sum(1 for _ in target.open(encoding="utf-8"))
            print(f"  {split:11s} already present ({count} docs) at {target}")
            continue
        print(f"  {split:11s} downloading from Fraunhofer SCAI ...")
        path = download_split(split, data_dir)
        count = sum(1 for _ in path.open(encoding="utf-8"))
        print(f"  {split:11s} wrote {count} docs to {path}")

    print("Done.")


if __name__ == "__main__":
    main()
