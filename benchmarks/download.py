"""Download the benchmark corpora: all of them, or the ones picked from a list.

    uv run --extra benchmarks python benchmarks/download.py            # pick from a list
    uv run --extra benchmarks python benchmarks/download.py --all      # everything public
    uv run python benchmarks/download.py --list                        # just shows the table

Each benchmark has its own script in benchmarks/scripts/. This script runs them one
after the other and prints a little summary. A benchmark whose files are already on
disk is skipped by its script, so running this again is safe.

RadGraph-XL is never part of --all: it is PhysioNet credentialed data that
each user downloads by hand. 
"""

from __future__ import annotations

import argparse
import importlib.util
import os
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table
from rich.text import Text
from rich.theme import Theme

try:
    from bio_annotation.terminal_theme import TOTALANNOTATOR_THEME as THEME
except ImportError:  # running without the package installed
    THEME = Theme(
        {
            "brand": "bold cyan",
            "accent": "bold magenta",
            "muted": "cyan",
            "panel.border": "bright_cyan",
            "table.header": "bold cyan",
            "table.title": "bold magenta",
            "field": "bold cyan",
            "ok": "bold green",
            "warning": "bold yellow",
            "path": "bright_blue",
        }
    )

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT / "benchmarks" / "scripts"
console = Console(theme=THEME, highlight=False)

NAMES = {
    "anatem": "AnatEM",
    "bc2gm": "BC2GM",
    "bc4chemd": "BC4CHEMD",
    "bc5cdr": "BC5CDR",
    "bioid": "BioID",
    "bionlp09": "BioNLP09",
    "bionlp11epi": "BioNLP11EPI",
    "bionlp11id": "BioNLP11ID",
    "bionlp13cg": "BioNLP13CG",
    "bionlp13ge": "BioNLP13GE",
    "bionlp13pc": "BioNLP13PC",
    "biored": "BioRED",
    "cellfinder": "CellFinder",
    "chebi": "ChEBI",
    "chemprot": "ChemProt",
    "craft": "CRAFT",
    "ddi": "DDI",
    "dna_methylation": "DNA Methylation",
    "europepmc": "Europe PMC",
    "fsu_prge": "FSU_PRGE",
    "gnormplus": "GNormPlus",
    "jnlpba": "JNLPBA",
    "linnaeus": "LINNAEUS",
    "maccrobat": "MACCROBAT",
    "mantra": "Mantra (English)",
    "medmentions": "MedMentions",
    "mirna": "miRNA",
    "mlee": "MLEE",
    "mtor": "mTOR",
    "ncbi": "NCBI Disease",
    "nlm_gene": "NLM-Gene",
    "nlmchem": "NLM-Chem",
    "pgxcorpus": "PGxCorpus",
    "phaedra": "PHAEDRA",
    "radgraph_xl": "RadGraph-XL",
    "rate_ner": "RaTE-NER (Radiopaedia)",
    "scai_disease": "SCAI Disease",
    "snpphena": "SNPPhenA",
    "species_800": "Species-800",
    "tmvar_v3": "tmVar3",
    "umls_semantic_types": "UMLS semantic type names",
}
# Entity types of each benchmark, as found in its data files (long lists are ...ed).
ENTITIES = {
    "anatem": "12 anatomy types: Organ, Tissue, Cell, Cellular_component, Cancer, Pathological_formation, ...",
    "bc2gm": "Gene (IOB tags)",
    "bc4chemd": "Chemical",
    "bc5cdr": "Chemical, Disease",
    "bioid": "anatomy, assay, cell, cellline, chemical, gene, molecule, organism, protein, rna, species, subcellular, tissue",
    "bionlp09": "Protein, Entity",
    "bionlp11epi": "Protein, Entity",
    "bionlp11id": "Protein, Chemical, Organism, Regulon-operon, Two-component-system, Entity",
    "bionlp13cg": "18 types: Gene_or_gene_product, Simple_chemical, Cancer, Cell, Organ, Tissue, Organism, ...",
    "bionlp13ge": "Protein, Entity, Anaphora, Binding",
    "bionlp13pc": "Gene_or_gene_product, Simple_chemical, Complex, Cellular_component",
    "biored": "Gene, Disease/Phenotype, Chemical, Organism, Variant, CellLine",
    "cellfinder": "GeneProtein, CellType, CellLine, CellComponent, Anatomy, Species",
    "chebi": "Chemical, Chemical_Structure, Metabolite, Protein, Species, Biological_Activity, Spectral_Data",
    "chemprot": "CHEMICAL, GENE-Y, GENE-N",
    "craft": "ontology classes: CHEBI, CL, GO_BP, GO_CC, GO_MF, MONDO, MOP, NCBITaxon, PR, SO, UBERON",
    "ddi": "DRUG, BRAND, GROUP, DRUG_N",
    "dna_methylation": "Protein",
    "europepmc": "GP (gene/protein), DS (disease), OG (organism)",
    "fsu_prge": "protein, protein_complex, protein_enum, protein_familiy_or_group, protein_variant",
    "gnormplus": "Gene, FamilyName, DomainMotif",
    "jnlpba": "protein, DNA, RNA, cell_line, cell_type",
    "linnaeus": "species",
    "maccrobat": "41 clinical types: Disease_disorder, Sign_symptom, Medication, Diagnostic_procedure, Lab_value, ...",
    "mantra": "UMLS semantic groups: DISO, CHEM, PROC, ANAT, LIVB, PHYS, PHEN, OBJC, DEVI, GEOG",
    "medmentions": "UMLS semantic types (21 in st21pv, 127 in full) with UMLS concept IDs",
    "mirna": "Specific_miRNAs, Non-Specific_miRNAs, Genes/Proteins, Diseases, Species",
    "mlee": "16 types: Gene_or_gene_product, Drug_or_compound, Cell, Organ, Tissue, Organism, ...",
    "mtor": "Protein, Complex, Drug, Ion, RNA, Receptor, Simple_molecule, Tag",
    "ncbi": "Disease (SpecificDisease, DiseaseClass, CompositeMention, Modifier)",
    "nlm_gene": "Gene, GENERIF, STARGENE, Domain, Other",
    "nlmchem": "Chemical",
    "pgxcorpus": "Chemical, Disease, Gene_or_protein, Phenotype, Genomic_variation, Haplotype, ...",
    "phaedra": "Pharmacological_substance, Disorder, Subject",
    "radgraph_xl": "Anatomy, Observation (each definitely present / absent / uncertain)",
    "rate_ner": "Anatomy, Abnormality, Disease, Non-Abnormality, Non-Disease",
    "scai_disease": "DISEASE, ADVERSE",
    "snpphena": "SNP, Phenotype",
    "species_800": "Species",
    "tmvar_v3": "DNAMutation, ProteinMutation, SNP, Gene, Species, CellLine, ...",
    "umls_semantic_types": "names of the 127 UMLS semantic types (for MedMentions)",
}
LOCAL_ONLY = {"radgraph_xl"}  # !credentialed data, converted from a zip the user downloads


@dataclass
class Benchmark:
    key: str
    module: ModuleType

    @property
    def name(self) -> str:
        return NAMES.get(self.key, self.key)

    @property
    def needs_datasets(self) -> bool:
        return "load_dataset" in (SCRIPTS_DIR / f"{self.key}.py").read_text(encoding="utf-8")


def load_benchmarks() -> list[Benchmark]:
    benchmarks = []
    for path in sorted(SCRIPTS_DIR.glob("*.py")):
        if path.stem.startswith("_"):
            continue
        spec = importlib.util.spec_from_file_location(f"benchmark_script_{path.stem}", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        benchmarks.append(Benchmark(path.stem, module))
    # The UMLS semantic type list is a lookup file, not a corpus-> shows in the end
    return sorted(benchmarks, key=lambda b: (b.key == "umls_semantic_types", b.name.lower()))


def show_table(benchmarks: list[Benchmark]) -> None:
    table = Table(box=box.ROUNDED, border_style="panel.border", header_style="table.header")
    table.add_column("#", justify="right", style="muted")
    table.add_column("Benchmark", style="field", no_wrap=True)
    table.add_column("Entities", style="muted", max_width=70)
    for number, bench in enumerate(benchmarks, start=1):
        table.add_row(str(number), bench.name, ENTITIES.get(bench.key, ""))
    console.print(table)


def banner() -> None:
    body = Text.assemble(
        ("Benchmarks\n", "brand"),
        ("Download corpora into benchmarks/data/", "muted"),
    )
    console.print(Panel(body, box=box.ROUNDED, border_style="panel.border", padding=(1, 2), expand=False))


def parse_choice(answer: str, benchmarks: list[Benchmark]) -> list[Benchmark]:
    """Turn '1,3,5-8', 'biored ncbi' or 'all' into benchmarks."""
    answer = answer.strip().lower()
    if answer == "all":
        return [b for b in benchmarks if b.key not in LOCAL_ONLY]
    by_key = {b.key: b for b in benchmarks}
    by_name = {b.name.lower(): b for b in benchmarks}
    chosen: list[Benchmark] = []
    for token in answer.replace(",", " ").split():
        if "-" in token and all(part.isdigit() for part in token.split("-", 1)):
            first, last = (int(part) for part in token.split("-", 1))
            chosen.extend(benchmarks[i - 1] for i in range(first, last + 1) if 1 <= i <= len(benchmarks))
        elif token.isdigit() and 1 <= int(token) <= len(benchmarks):
            chosen.append(benchmarks[int(token) - 1])
        elif token in by_key or token in by_name:
            chosen.append(by_key.get(token) or by_name[token])
        else:
            raise ValueError(token)
    return list({b.key: b for b in chosen}.values())  


def ask(benchmarks: list[Benchmark]) -> list[Benchmark]:
    console.print(
        Text.assemble(
            ("Choose by number ", "muted"), ("1,3,5-8", "field"),
            (", by name ", "muted"), ("biored ncbi", "field"),
            (" or ", "muted"), ("all", "field"),
            (". Press Enter to quit.", "muted"),
        )
    )
    while True:
        answer = Prompt.ask("[brand]Download[/]", default="", show_default=False, console=console)
        if not answer.strip():
            return []
        try:
            return parse_choice(answer, benchmarks)
        except ValueError as exc:
            console.print(f"[warning]Not a number, name or group:[/] {exc}")


def datasets_available() -> bool:
    return importlib.util.find_spec("datasets") is not None


def local_input_available(bench: Benchmark) -> bool:
    """RadGraph-XL can run if it is already converted or its zip is in ~/Downloads."""
    module = bench.module
    converted = module._split_file(module._default_data_dir(), module.SPLITS[0])
    return converted.exists() or (Path.home() / "Downloads" / module.ZIP_NAME).is_file()


def run(selected: list[Benchmark]) -> int:
    has_datasets = datasets_available()
    results: list[tuple[Benchmark, str, float]] = []
    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    for index, bench in enumerate(selected, start=1):
        console.rule(f"[brand]{index}/{len(selected)}[/]  [field]{bench.name}[/]", style="panel.border")
        if bench.needs_datasets and not has_datasets:
            console.print("[warning]Skipped:[/] needs the 'datasets' package. Run: uv sync --extra benchmarks")
            results.append((bench, "skipped: no datasets", 0.0))
            continue
        if bench.key in LOCAL_ONLY and not local_input_available(bench):
            console.print(
                "[warning]Skipped:[/] RadGraph-XL needs its zip from PhysioNet (credentialed access) in "
                "~/Downloads, or run benchmarks/scripts/radgraph_xl.py with the zip's path."
            )
            results.append((bench, "skipped: no zip", 0.0))
            continue
        start = time.monotonic()
        code = subprocess.run([sys.executable, str(SCRIPTS_DIR / f"{bench.key}.py")], cwd=ROOT, env=env).returncode
        results.append((bench, "ok" if code == 0 else f"failed (exit {code})", time.monotonic() - start))

    summary = Table(box=box.ROUNDED, border_style="panel.border", header_style="table.header",
                    title="Summary", title_style="table.title")
    summary.add_column("Benchmark", style="field")
    summary.add_column("Result")
    summary.add_column("Time", justify="right", style="muted")
    for bench, result, seconds in results:
        style = "ok" if result == "ok" else ("warning" if result.startswith("skipped") else "bold red")
        summary.add_row(bench.name, Text(result, style=style), f"{seconds:.0f} s")
    console.print()
    console.print(summary)
    failed = [r for r in results if r[1].startswith("failed")]
    if failed:
        console.print(f"[bold red]{len(failed)} failed.[/] Scroll up for the error, or run its script on its own.")
    return 1 if failed else 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Download benchmark corpora into benchmarks/data/.")
    parser.add_argument("--all", action="store_true", help="download every public benchmark")
    parser.add_argument("--list", action="store_true", help="show the table and exit")
    args = parser.parse_args()

    benchmarks = load_benchmarks()
    banner()
    if args.list:
        show_table(benchmarks)
        return 0
    if args.all:
        selected = parse_choice("all", benchmarks)
    else:
        show_table(benchmarks)
        selected = ask(benchmarks)
    if not selected:
        console.print("[muted]Nothing selected.[/]")
        return 0
    console.print(f"[muted]Selected {len(selected)}:[/] " + ", ".join(b.name for b in selected))
    return run(selected)


if __name__ == "__main__":
    sys.exit(main())
