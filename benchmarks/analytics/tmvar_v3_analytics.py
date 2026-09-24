"""Per-split summary of the tmVar3 corpus (entities, normalization, top mentions).

    uv run python benchmarks/analytics/tmvar_v3_analytics.py
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

SPLITS = ("tmvar_v3",)  # tmVar3 has no splits: the whole corpus is one file, tmvar_v3.jsonl
VARIANT_TYPES = (
    "SNP",
    "DNAMutation",
    "ProteinMutation",
    "OtherMutation",
    "DNAAllele",
    "ProteinAllele",
    "AcidChange",
)


def _project_root() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "pyproject.toml").exists():
            return parent
    return here.parent


DATA_DIR = _project_root() / "benchmarks" / "data" / "tmvar_v3"


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


def analyze_split(name: str, df: pd.DataFrame) -> str:
    ent = entities_table(df)

    parts: list[str] = []
    parts.append(f"## {name.upper()}\n")
    parts.append(f"- Documents: **{len(df)}**")
    parts.append(
        f"- Entity mentions: **{len(ent)}** across **{ent['document_id'].nunique()}** documents\n"
    )

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

    # Variants (tmVar3-specific). The bigbio_kb mapping stores two different
    # things under db_name "dbSNP": real rsIDs (digits only) and tmVar
    # normalized strings such as "c|SUB|G|Ex2+860|C". Its "NCBI Gene" IDs on
    # variant mentions are the gene the variant sits on, not the variant itself.
    var = ent[ent["type"].isin(VARIANT_TYPES)]
    if len(var) > 0:
        var_ids = (
            var[["normalized"]]
            .explode("normalized")
            .dropna(subset=["normalized"])
            .reset_index()
            .pipe(lambda d: d.join(pd.json_normalize(d["normalized"])).drop(columns=["normalized"]))
        )
        dbsnp = var_ids[var_ids["db_name"] == "dbSNP"]
        is_rsid = dbsnp["db_id"].str.fullmatch(r"\d+")
        with_rsid = dbsnp.loc[is_rsid, "index"].nunique()
        with_gene = var_ids.loc[var_ids["db_name"] == "NCBI Gene", "index"].nunique()

        parts.append("### Variants\n")
        parts.append(f"- Variant mentions ({', '.join(VARIANT_TYPES)}): **{len(var)}**")
        parts.append(
            f"- With a real dbSNP rsID: **{with_rsid}** / {len(var)} "
            f"({with_rsid / len(var) * 100:.1f}%)"
        )
        parts.append(
            f"- With a corresponding gene (NCBI Gene): **{with_gene}** / {len(var)} "
            f"({with_gene / len(var) * 100:.1f}%)"
        )
        parts.append(
            f"- IDs under db_name dbSNP: **{int(is_rsid.sum())}** rsIDs, "
            f"**{int((~is_rsid).sum())}** tmVar normalized strings\n"
        )

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
    print(f"tmVar3 analytics, data dir: {DATA_DIR}\n")
    if not DATA_DIR.is_dir():
        raise SystemExit(
            f"Data directory not found: {DATA_DIR}\n"
            "Run benchmarks/scripts/tmvar_v3.py first to download the corpus."
        )

    chunks: list[str] = ["# tmVar3 analytics\n"]
    for split in SPLITS:
        target = DATA_DIR / f"{split}.jsonl"
        if not target.exists():
            print(f"Skipping {split}: {target} not found.\n")
            continue
        df = load_split(split)
        chunks.append(analyze_split(split, df))

    summary_path = DATA_DIR / "TMVAR_V3_ANALYTICS_SUMMARY.md"
    summary_path.write_text("\n".join(chunks), encoding="utf-8")
    print(f"\nSaved to: {summary_path}")


if __name__ == "__main__":
    main()
