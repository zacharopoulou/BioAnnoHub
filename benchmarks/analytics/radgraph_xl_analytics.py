"""Summary of the local RadGraph-XL conversion (entities, relations, top mentions).

The summary quotes report text (top mentions), so it stays local: like the data,
it is in .gitignore and must not be shared.

    uv run python benchmarks/analytics/radgraph_xl_analytics.py
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

SPLITS = ("radgraph_xl",)  # no splits: all 300 reports are in one file, radgraph_xl.jsonl


def _project_root() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "pyproject.toml").exists():
            return parent
    return here.parent


DATA_DIR = _project_root() / "benchmarks" / "data" / "radgraph_xl"


def load_split(split: str) -> pd.DataFrame:
    return pd.read_json(DATA_DIR / f"{split}.jsonl", lines=True, dtype={"document_id": str})


def entities_table(df: pd.DataFrame) -> pd.DataFrame:
    ent = (
        df[["document_id", "entities"]]
        .explode("entities")
        .dropna(subset=["entities"])
        .reset_index(drop=True)
    )
    ent = ent.join(pd.json_normalize(ent["entities"])).drop(columns=["entities"])
    ent["text_joined"] = ent["text"].apply(lambda xs: " ".join(xs) if isinstance(xs, list) else "")
    ent["span_length"] = ent["text_joined"].str.len()
    ent["norm_count"] = ent["normalized"].apply(lambda xs: len(xs) if isinstance(xs, list) else 0)
    return ent


def relations_table(df: pd.DataFrame) -> pd.DataFrame:
    """One row per relation, with the type and IDs of both arguments joined in."""
    rows: list[dict] = []
    for _, doc_row in df.iterrows():
        entities = doc_row.get("entities")
        relations = doc_row.get("relations")
        if not isinstance(entities, list) or not isinstance(relations, list):
            continue

        ent_by_id = {
            ent["id"]: {
                "type": ent.get("type", ""),
                "ids": ",".join(sorted(str(n.get("db_id", "")) for n in ent.get("normalized") or [])),
            }
            for ent in entities
            if isinstance(ent, dict) and ent.get("id")
        }

        for rel in relations:
            if not isinstance(rel, dict):
                continue
            arg1 = ent_by_id.get(rel.get("arg1_id"), {})
            arg2 = ent_by_id.get(rel.get("arg2_id"), {})
            rows.append({
                "document_id": doc_row.get("document_id"),
                "type": rel.get("type", ""),
                "arg_types": " - ".join(sorted([arg1.get("type", ""), arg2.get("type", "")])),
                "arg1_ids": arg1.get("ids", ""),
                "arg2_ids": arg2.get("ids", ""),
            })
    return pd.DataFrame(rows)


def analyze_split(name: str, df: pd.DataFrame) -> str:
    ent = entities_table(df)
    rel = relations_table(df)

    parts: list[str] = []
    parts.append(f"## {name.upper()}\n")
    parts.append(f"- Documents: **{len(df)}**")
    parts.append(
        f"- Entity mentions: **{len(ent)}** across **{ent['document_id'].nunique()}** documents"
    )
    parts.append(f"- Relations: **{len(rel)}** mention pairs\n")

    parts.append("### Entity counts by type\n")
    parts.append(ent.groupby("type").size().rename("n_mentions").to_markdown())
    parts.append("")

    parts.append("### Entities per document\n")
    parts.append(
        ent.groupby("document_id")
        .size()
        .describe()[["count", "mean", "min", "50%", "max"]]
        .round(1)
        .to_markdown()
    )
    parts.append("")

    parts.append("### Span length (chars)\n")
    parts.append(
        ent["span_length"]
        .describe()[["count", "mean", "min", "50%", "max"]]
        .round(1)
        .to_markdown()
    )
    parts.append("")

    with_norm = int((ent["norm_count"] > 0).sum())
    pct = with_norm / len(ent) * 100 if len(ent) else 0.0
    parts.append(f"### Normalization: {with_norm} / {len(ent)} ({pct:.1f}%)\n")
    if with_norm > 0:
        norm_long = (
            ent.loc[ent["norm_count"] > 0, ["normalized"]]
            .explode("normalized")
            .reset_index(drop=True)
            .pipe(lambda d: d.join(pd.json_normalize(d["normalized"])).drop(columns=["normalized"]))
        )
        parts.append(norm_long.groupby("db_name").size().rename("n_ids").to_markdown())
        parts.append("")

    parts.append("### Top 5 mentions per entity type (case-insensitive)\n")
    for type_name, group in ent.groupby("type"):
        top5 = group["text_joined"].str.lower().value_counts().head(5).rename("n")
        parts.append(f"#### {type_name}\n")
        parts.append(top5.to_markdown())
        parts.append("")

    # Relations. Unlike BioRED, RadGraph relations link two mentions, not two
    # concepts, and nothing is normalized, so the "concept pair" count below
    # only removes repeated relations of the same type in one report.
    if len(rel) > 0:
        concept = rel.drop_duplicates(["document_id", "type", "arg1_ids", "arg2_ids"])
        parts.append(f"### Relations: {len(rel)} mention pairs, {len(concept)} concept pairs\n")
        parts.append(
            pd.DataFrame(
                {
                    "mention_pairs": rel.groupby("type").size(),
                    "concept_pairs": concept.groupby("type").size(),
                }
            ).to_markdown()
        )
        parts.append("")

        parts.append("#### Concept pairs by argument types\n")
        parts.append(
            concept.groupby("arg_types").size().rename("n").sort_values(ascending=False).to_markdown()
        )
        parts.append("")

    text = "\n".join(parts)
    print(text)
    return text


def main() -> None:
    print(f"RadGraph-XL analytics, data dir: {DATA_DIR}\n")
    if not DATA_DIR.is_dir():
        raise SystemExit(
            f"Data directory not found: {DATA_DIR}\n"
            "Run benchmarks/scripts/radgraph_xl.py first to convert your local download."
        )

    chunks: list[str] = ["# RadGraph-XL analytics\n"]
    for split in SPLITS:
        target = DATA_DIR / f"{split}.jsonl"
        if not target.exists():
            print(f"Skipping {split}: {target} not found.\n")
            continue
        df = load_split(split)
        chunks.append(analyze_split(split, df))

    summary_path = DATA_DIR / "RADGRAPH_XL_ANALYTICS_SUMMARY.md"
    summary_path.write_text("\n".join(chunks), encoding="utf-8")
    print(f"\nSaved to: {summary_path}")


if __name__ == "__main__":
    main()
