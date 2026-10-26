"""Download the UMLS semantic type list into benchmarks/data/medmentions/.

    uv run python benchmarks/scripts/umls_semantic_types.py

MedMentions stores only the semantic type ID of each mention (for example
T060), not its name. This script downloads NLM's list of all 127 UMLS
semantic types (abbreviation|ID|name, for example diap|T060|Diagnostic
Procedure), so the IDs can be looked up. It needs no extra dependencies.

The list is published with MetaMap (SemanticTypes_2018AB.txt).
"""

from __future__ import annotations

import re
import urllib.request
from pathlib import Path

SOURCE_URL = (
    "https://wayback.archive-it.org/7867/20241213202140/"
    "https://lhncbc.nlm.nih.gov/ii/tools/MetaMap/Docs/SemanticTypes_2018AB.txt"
)
FILE_NAME = "SemanticTypes_2018AB.txt"
EXPECTED_TYPES = 127
LINE_PATTERN = re.compile(r"^[a-z]{4}\|T\d{3}\|.+$")


def _find_project_root() -> Path | None:
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "pyproject.toml").exists():
            return parent
    return None


def _default_data_dir() -> Path:
    root = _find_project_root()
    base = root if root is not None else Path.cwd()
    return base / "benchmarks" / "data" / "medmentions"


def download(data_dir: Path) -> Path:
    """Download the semantic type list, check its format and save it unchanged."""
    with urllib.request.urlopen(SOURCE_URL, timeout=120) as response:
        text = response.read().decode("utf-8")
    lines = [line for line in text.splitlines() if line.strip()]
    bad = [line for line in lines if not LINE_PATTERN.match(line)]
    if bad:
        raise ValueError(f"unexpected lines in {SOURCE_URL}: {bad[:3]!r}")
    if len(lines) != EXPECTED_TYPES:
        raise ValueError(f"expected {EXPECTED_TYPES} semantic types, got {len(lines)}")
    target = data_dir / FILE_NAME
    target.parent.mkdir(parents=True, exist_ok=True)
    # Write to <name>.part and rename it once complete, so an interrupted run leaves no partial file.
    partial = target.with_name(target.name + ".part")
    try:
        partial.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
        partial.replace(target)
    except BaseException:
        partial.unlink(missing_ok=True)
        raise
    return target


def main() -> None:
    data_dir = _default_data_dir()
    print(f"UMLS semantic types target directory: {data_dir}")

    target = data_dir / FILE_NAME
    if target.exists():
        count = sum(1 for line in target.open(encoding="utf-8") if line.strip())
        print(f"  already present ({count} types) at {target}")
    else:
        print(f"  downloading from {SOURCE_URL} ...")
        path = download(data_dir)
        print(f"  wrote {EXPECTED_TYPES} types to {path}")

    print("Done.")


if __name__ == "__main__":
    main()
