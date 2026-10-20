"""Download the OSIRIS corpus into benchmarks/data/osiris/ as one JSONL file.

    uv run python benchmarks/scripts/osiris.py

105 abstracts: genes (NCBI Gene) and variants (dbSNP when given). Positions are
computed from the XML tags around each mention.
"""

from __future__ import annotations

import io
import json
import tarfile
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Iterable

# Pinned repository version: the commit sha of rockt/SETH, i.e. the "sha" field of
# https://api.github.com/repos/rockt/SETH/commits/master (its latest commit when it was pinned).
SETH_COMMIT = "a3d7ce7d767d65865c0fa402cfb357233c8009e1"
SOURCE_URL = f"https://codeload.github.com/rockt/SETH/tar.gz/{SETH_COMMIT}"
CORPUS_FILE = "resources/OSIRIS/corpus.xml"
SPLITS = ("osiris",)  # no splits: the whole corpus is one file, osiris.jsonl


def _find_project_root() -> Path | None:
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "pyproject.toml").exists():
            return parent
    return None


def _default_data_dir() -> Path:
    root = _find_project_root()
    base = root if root is not None else Path.cwd()
    return base / "benchmarks" / "data" / "osiris"


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


def _read_corpus_xml() -> ET.Element:
    with urllib.request.urlopen(SOURCE_URL, timeout=300) as response:
        archive = tarfile.open(fileobj=io.BytesIO(response.read()), mode="r:gz")
    member = next(m for m in archive.getmembers() if m.name.split("/", 1)[-1] == CORPUS_FILE)
    return ET.fromstring(archive.extractfile(member).read())


def _normalized(tag: ET.Element) -> list[dict[str, str]]:
    if tag.tag == "gene":  # g_id "No" means the corpus gives no NCBI Gene ID
        gene_id = tag.get("g_id")
        return [{"db_name": "NCBI Gene", "db_id": gene_id}] if gene_id and gene_id.isdigit() else []
    rs = tag.get("v_id")
    return [{"db_name": "dbSNP", "db_id": f"rs{rs}"}] if rs and rs.isdigit() else []


def _passage_text(part: ET.Element, offset: int, pmid: str, entities: list[dict[str, Any]]) -> str:
    """Flatten a Title/Abstract element to text, adding one entity per gene/variant tag."""
    pieces = [part.text or ""]
    position = offset + len(pieces[0])
    for tag in part:
        inner = "".join(tag.itertext())
        start, end = position, position + len(inner)
        start += len(inner) - len(inner.lstrip())  # a few tags include a space at an edge
        end -= len(inner) - len(inner.rstrip())
        entities.append(
            {"id": f"{pmid}_T{len(entities)}", "type": tag.tag, "text": [inner.strip()],
             "offsets": [[start, end]], "normalized": _normalized(tag)}
        )
        pieces += [inner, tag.tail or ""]
        position += len(inner) + len(tag.tail or "")
    return "".join(pieces)


def _to_bigbio_kb(article: ET.Element) -> dict[str, Any]:
    pmid = article.findtext("Pmid")
    entities: list[dict[str, Any]] = []
    title = _passage_text(article.find("Title"), 0, pmid, entities)
    abstract_start = len(title) + 1
    abstract = _passage_text(article.find("Abstract"), abstract_start, pmid, entities)
    text = f"{title} {abstract}"
    for entity in entities:
        (start, end), = entity["offsets"]
        if text[start:end] != entity["text"][0]:
            raise ValueError(f"PMID {pmid}: offsets give {text[start:end]!r}, tag says {entity['text'][0]!r}")
    return {
        "id": pmid,
        "document_id": pmid,
        "passages": [
            {"id": f"{pmid}_title", "type": "title", "text": [title], "offsets": [[0, len(title)]]},
            {"id": f"{pmid}_abstract", "type": "abstract", "text": [abstract],
             "offsets": [[abstract_start, len(text)]]},
        ],
        "entities": entities,
        "events": [],
        "coreferences": [],
        "relations": [],
    }


def download_split(split: str, data_dir: Path) -> Path:
    """Download the pinned SETH repository, convert the OSIRIS corpus and persist it as JSONL."""
    root = _read_corpus_xml()
    target = _split_file(data_dir, split)
    _write_jsonl(target, (_to_bigbio_kb(article) for article in root.iter("Article")))
    return target


def main() -> None:
    data_dir = _default_data_dir()
    print(f"OSIRIS target directory: {data_dir}")

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
