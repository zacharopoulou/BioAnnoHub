"""Summary of the BioID corpus (captions, entities, normalization, top mentions).

    uv run python benchmarks/analytics/bioid_analytics.py
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

SPLITS = ("bioid",)  # BioID has no splits: the whole released corpus is one file, bioid.jsonl


def _project_root() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "pyproject.toml").exists():
            return parent
    return here.parent


DATA_DIR = _project_root() / "benchmarks" / "data" / "bioid"


def load_split(split: str) -> pd.DataFrame:
    return pd.read_json(DATA_DIR / f"{split}.jsonl", lines=True, dtype={"document_id": str})


def entities_table(df: pd.DataFrame) -> pd.DataFrame:
    # BioID rows are figure-panel captions; document_id is the PMC article, so
    # several rows share it. The row `id` is the unique caption key.
    ent = (
        df[["id", "document_id", "entities"]]
        .rename(columns={"id": "caption_id"})
        .explode("entities")
        .dropna(subset=["entities"])
        .reset_index(drop=True)
    )
    ent = ent.join(pd.json_normalize(ent["entities"])).drop(columns=["entities"])
    ent["text_joined"] = ent["text"].apply(lambda xs: " ".join(xs) if isinstance(xs, list) else "")
    ent["span_length"] = ent["text_joined"].str.len()
    ent["norm_count"] = ent["normalized"].apply(lambda xs: len(xs) if isinstance(xs, list) else 0)
    return ent


def analyze_split(name: str, df: pd.DataFrame) -> str:
    ent = entities_table(df)

    parts: list[str] = []
    parts.append(f"## {name.upper()}\n")
    parts.append(
        f"- Figure-panel captions: **{len(df)}** from **{df['document_id'].nunique()}** "
        "articles (document_id = PMC article)"
    )
    parts.append(
        f"- Entity mentions: **{len(ent)}** across **{ent['caption_id'].nunique()}** captions "
        f"({len(df) - ent['caption_id'].nunique()} captions have no annotations)\n"
    )

    parts.append("### Entity counts by type\n")
    parts.append(
        ent.groupby("type")
        .agg(n_mentions=("type", "size"), n_normalized=("norm_count", lambda s: int((s > 0).sum())))
        .to_markdown()
    )
    parts.append("")

    parts.append("### Entities per caption\n")
    parts.append(
        ent.groupby("caption_id")
        .size()
        .describe()[["count", "mean", "min", "50%", "max"]]
        .round(1)
        .to_markdown()
    )
    parts.append("")

    parts.append("### Captions per article\n")
    parts.append(
        df.groupby("document_id")
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

    text = "\n".join(parts)
    print(text)
    return text


def main() -> None:
    print(f"BioID analytics, data dir: {DATA_DIR}\n")
    if not DATA_DIR.is_dir():
        raise SystemExit(
            f"Data directory not found: {DATA_DIR}\n"
            "Run benchmarks/scripts/bioid.py first to download the corpus."
        )

    chunks: list[str] = ["# BioID analytics\n"]
    for split in SPLITS:
        target = DATA_DIR / f"{split}.jsonl"
        if not target.exists():
            print(f"Skipping {split}: {target} not found.\n")
            continue
        df = load_split(split)
        chunks.append(analyze_split(split, df))

    summary_path = DATA_DIR / "BIOID_ANALYTICS_SUMMARY.md"
    summary_path.write_text("\n".join(chunks), encoding="utf-8")
    print(f"\nSaved to: {summary_path}")


if __name__ == "__main__":
    main()
