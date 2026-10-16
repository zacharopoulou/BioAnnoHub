"""Download Species-800 (S800) into benchmarks/data/species_800/ as JSONL splits.

    uv run python benchmarks/scripts/species_800.py

There is no working Hugging Face loader that keeps the S800 character
offsets and NCBI Taxonomy IDs (spyysalo/species_800 only has IOB tokens),
so this script builds the corpus itself, in the same bigbio_kb layout as
the other benchmarks:

1. It downloads the original S800 release from species.jensenlab.org:
   800 PubMed abstracts plus one annotation file (S800.tsv).
2. It splits the abstracts into train, validation and test with the split
   lists from Sampo Pyysalo's S800 repository (the same split the Hugging
   Face IOB version uses). The lists are pinned to a fixed commit.
3. It keeps abstracts without any species mentions (175 of 800), because
   any species an annotator finds in them is a false positive.

S800 end offsets are inclusive (the last character is part of the mention),
so 1 is added to every end offset to match the other benchmarks.
"""

from __future__ import annotations

import io
import json
import re
import tarfile
import urllib.request
from pathlib import Path
from typing import Any, Iterable

S800_URL = "https://species.jensenlab.org/files/S800-1.0.tar.gz"
SPLIT_URL = "https://raw.githubusercontent.com/spyysalo/s800/{commit}/split/{name}.txt"
SPLIT_COMMIT = "f5425e7498930757c8577828eabc41cf88d80348"
SPLITS = ("train", "validation", "test")
# Pyysalo's repository calls the validation split "devel".
SPLIT_NAMES = {"train": "train", "validation": "devel", "test": "test"}

# One annotation line: TAXON_ID <TAB> DOCID:PMID <TAB> START <TAB> END <TAB> TEXT
ANN_LINE_RE = re.compile(r"^(\d+)\t(\S+):(\S+)\t(\d+)\t(\d+)\t(.+)$")


def _find_project_root() -> Path | None:
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "pyproject.toml").exists():
            return parent
    return None


def _default_data_dir() -> Path:
    root = _find_project_root()
    base = root if root is not None else Path.cwd()
    return base / "benchmarks" / "data" / "species_800"


def _split_file(data_dir: Path, split: str) -> Path:
    return data_dir / f"{split}.jsonl"


def _write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, default=str))
            handle.write("\n")


def _fetch(url: str) -> bytes:
    with urllib.request.urlopen(url, timeout=120) as response:
        return response.read()


def _read_release() -> tuple[dict[str, str], dict[str, str], dict[str, list[tuple]]]:
    """Return (text by docid, docid by PMID, annotations by docid) from the S800 tarball."""
    texts: dict[str, str] = {}
    files: dict[str, str] = {}
    with tarfile.open(fileobj=io.BytesIO(_fetch(S800_URL)), mode="r:gz") as tar:
        for member in tar.getmembers():
            if not member.isfile():
                continue
            name = Path(member.name)
            content = tar.extractfile(member).read().decode("utf-8")
            if name.parent.name == "abstracts" and name.suffix == ".txt":
                texts[name.stem] = content
            elif name.name in ("S800.tsv", "pubmedid.tsv"):
                files[name.name] = content

    docid_by_pmid: dict[str, str] = {}
    for line in files["pubmedid.tsv"].splitlines():
        if line.strip():
            docid, pmid = line.split("\t")[:2]
            docid_by_pmid[pmid.replace("PMID:", "")] = docid

    annotations: dict[str, list[tuple]] = {}
    for line in files["S800.tsv"].splitlines():
        match = ANN_LINE_RE.match(line)
        if not match:
            raise ValueError(f"Unexpected S800.tsv line: {line!r}")
        taxon_id, docid, _pmid, start, end, text = match.groups()
        annotations.setdefault(docid, []).append((taxon_id, int(start), int(end) + 1, text))
    return texts, docid_by_pmid, annotations


def _to_bigbio_kb(uid: int, pmid: str, text: str, annotations: list[tuple]) -> dict[str, Any]:
    """Build one bigbio_kb document: title and abstract passages plus species entities."""
    # Each abstract file is the title, a blank line, then the abstract.
    title_end = text.index("\n")
    abstract_start = title_end + len(text[title_end:]) - len(text[title_end:].lstrip("\n"))
    abstract_end = len(text.rstrip())
    passages = [
        {"id": f"{pmid}_title", "type": "title", "text": [text[:title_end]], "offsets": [[0, title_end]]},
        {
            "id": f"{pmid}_abstract",
            "type": "abstract",
            "text": [text[abstract_start:abstract_end]],
            "offsets": [[abstract_start, abstract_end]],
        },
    ]

    entities = []
    for i, (taxon_id, start, end, mention) in enumerate(annotations, start=1):
        if text[start:end] != mention:
            raise ValueError(f"Offset mismatch in PMID {pmid}: {mention!r} vs {text[start:end]!r}")
        entities.append(
            {
                "id": f"{pmid}_T{i}",
                "type": "Species",
                "text": [mention],
                "offsets": [[start, end]],
                "normalized": [{"db_name": "NCBI Taxonomy", "db_id": taxon_id}],
            }
        )

    return {
        "id": str(uid),
        "document_id": pmid,
        "passages": passages,
        "entities": entities,
        "events": [],
        "coreferences": [],
        "relations": [],
    }


def download_all(data_dir: Path, splits: Iterable[str]) -> dict[str, Path]:
    """Build the requested splits from the S800 release and persist them as JSONL on disk."""
    texts, docid_by_pmid, annotations = _read_release()

    written: dict[str, Path] = {}
    uid = 0
    for split in splits:
        pmids = _fetch(SPLIT_URL.format(commit=SPLIT_COMMIT, name=SPLIT_NAMES[split])).decode().split()
        rows = []
        for pmid in pmids:
            docid = docid_by_pmid[pmid]
            rows.append(_to_bigbio_kb(uid, pmid, texts[docid], annotations.get(docid, [])))
            uid += 1
        target = _split_file(data_dir, split)
        _write_jsonl(target, rows)
        written[split] = target
    return written


def main() -> None:
    data_dir = _default_data_dir()
    print(f"Species-800 target directory: {data_dir}")

    missing = []
    for split in SPLITS:
        target = _split_file(data_dir, split)
        if target.exists():
            count = sum(1 for _ in target.open(encoding="utf-8"))
            print(f"  {split:11s} already present ({count} docs) at {target}")
        else:
            missing.append(split)

    if missing:
        print(f"  downloading S800 from {S800_URL} ...")
        for split, path in download_all(data_dir, missing).items():
            count = sum(1 for _ in path.open(encoding="utf-8"))
            print(f"  {split:11s} wrote {count} docs to {path}")

    print("Done.")


if __name__ == "__main__":
    main()
