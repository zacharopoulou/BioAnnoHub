"""Download the SCAI SNP corpus into benchmarks/data/scai_snp/ as one JSONL file.

    uv run python benchmarks/scripts/scai_snp.py

296 abstracts: variants with a dbSNP ID only, PSM (protein) and NSM (nucleotide).
Abstracts are fetched from PubMed. Academic use only.
"""

from __future__ import annotations

import io
import json
import tarfile
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Iterable

SOURCE_URL = "https://www.scai.fraunhofer.de/content/dam/scai/de/downloads/bioinformatik/normalization-variation-corpus.gz"
PUBMED_EFETCH = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
SPLITS = ("scai_snp",)  # no splits: the whole corpus is one file, scai_snp.jsonl
MAX_SHIFT = 20  # how far (in characters) a mention may have moved since 2011


def _find_project_root() -> Path | None:
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "pyproject.toml").exists():
            return parent
    return None


def _default_data_dir() -> Path:
    root = _find_project_root()
    base = root if root is not None else Path.cwd()
    return base / "benchmarks" / "data" / "scai_snp"


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


def _read_annotations() -> list[dict[str, Any]]:
    """Download the corpus archive and read annotations.txt (one mention per line)."""
    with urllib.request.urlopen(SOURCE_URL, timeout=120) as response:
        archive = tarfile.open(fileobj=io.BytesIO(response.read()), mode="r:gz")
    lines = archive.extractfile("annotations.txt").read().decode("utf-8").splitlines()
    annotations = []
    for line in lines:
        if not line.strip():
            continue
        pmid, mention, _snp, start, end, rs, kind = line.split("\t")
        annotations.append(
            {"pmid": pmid, "mention": mention.strip("'"), "start": int(start), "end": int(end),
             "rs": rs.strip(), "type": kind.strip()}
        )
    return annotations


def _fetch_abstracts(pmids: list[str]) -> dict[str, tuple[str, str]]:
    """Fetch title and abstract of each PMID from PubMed (labels kept as in 2011, except UNLABELLED)."""
    body = urllib.parse.urlencode({"db": "pubmed", "id": ",".join(pmids), "retmode": "xml", "tool": "bioannohub"})
    with urllib.request.urlopen(PUBMED_EFETCH, data=body.encode(), timeout=300) as response:
        root = ET.fromstring(response.read())
    articles = {}
    for article in root.iter("PubmedArticle"):
        pmid = article.findtext(".//MedlineCitation/PMID")
        title = "".join(article.find(".//ArticleTitle").itertext())
        sections = []
        for part in article.findall(".//Abstract/AbstractText"):
            label = part.get("Label")
            text = "".join(part.itertext())
            sections.append(f"{label}: {text}" if label and label != "UNLABELLED" else text)
        articles[pmid] = (title, " ".join(sections))
    return articles


def _locate(text: str, mention: str, start: int) -> int | None:
    """Where the mention is: at its stated start, or the nearest occurrence within MAX_SHIFT characters."""
    if text[start:start + len(mention)] == mention:
        return start
    nearby = [
        i for i in range(max(0, start - MAX_SHIFT), start + MAX_SHIFT + 1)
        if text.startswith(mention, i)
    ]
    return min(nearby, key=lambda i: abs(i - start)) if nearby else None


def _build_documents(annotations: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], int, list[str]]:
    by_pmid: dict[str, list[dict[str, Any]]] = {}
    for annotation in annotations:
        by_pmid.setdefault(annotation["pmid"], []).append(annotation)
    articles = _fetch_abstracts(sorted(by_pmid))

    documents, moved, dropped = [], 0, []
    for pmid in sorted(by_pmid, key=int):
        if pmid not in articles:
            dropped += [f"{pmid}: {a['mention']!r} (abstract not found in PubMed)" for a in by_pmid[pmid]]
            continue
        title, abstract = articles[pmid]
        text = f"{title}  {abstract}"
        entities = []
        for index, annotation in enumerate(by_pmid[pmid]):
            start = _locate(text, annotation["mention"], annotation["start"])
            if start is None:
                dropped.append(f"{pmid}: {annotation['mention']!r} (not found near position {annotation['start']})")
                continue
            moved += start != annotation["start"]
            end = start + len(annotation["mention"])
            while start < end and text[start].isspace():  # a few source mentions include a space at an edge
                start += 1
            while end > start and text[end - 1].isspace():
                end -= 1
            entities.append(
                {
                    "id": f"{pmid}_T{index}",
                    "type": annotation["type"],
                    "text": [text[start:end]],
                    "offsets": [[start, end]],
                    "normalized": [{"db_name": "dbSNP", "db_id": annotation["rs"]}],
                }
            )
        abstract_start = len(title) + 2
        documents.append(
            {
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
        )
    return documents, moved, dropped


def download_split(split: str, data_dir: Path) -> Path:
    """Download the annotations, fetch the abstracts from PubMed and persist the corpus as JSONL."""
    documents, moved, dropped = _build_documents(_read_annotations())
    kept = sum(len(d["entities"]) for d in documents)
    print(f"  {split:11s} {kept} mentions kept ({moved} found a few characters from their 2011 position), "
          f"{len(dropped)} left out")
    for reason in dropped:
        print(f"    left out: {reason}")
    target = _split_file(data_dir, split)
    _write_jsonl(target, documents)
    return target


def main() -> None:
    data_dir = _default_data_dir()
    print(f"SCAI SNP target directory: {data_dir}")

    for split in SPLITS:
        target = _split_file(data_dir, split)
        if target.exists():
            count = sum(1 for _ in target.open(encoding="utf-8"))
            print(f"  {split:11s} already present ({count} docs) at {target}")
            continue
        print(f"  {split:11s} downloading from Fraunhofer SCAI and PubMed ...")
        path = download_split(split, data_dir)
        count = sum(1 for _ in path.open(encoding="utf-8"))
        print(f"  {split:11s} wrote {count} docs to {path}")

    print("Done.")


if __name__ == "__main__":
    main()
