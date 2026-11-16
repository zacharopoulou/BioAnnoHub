"""Download the models of the annotators an image ships, as listed in images.toml.

Runs at image build time, before the bioannohub code is copied in, so it does not
import the package. tests/test_fetch_models.py keeps these names in sync with it.
"""

from __future__ import annotations

import argparse
import subprocess
import tomllib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
IMAGES_FILE = REPO_ROOT / "images.toml"
BENT_PYTHON = REPO_ROOT / "tools" / "bent" / ".venv" / "bin" / "python"

REMOTE_ANNOTATORS = ("pubtator3", "bern2", "medcat")
HF_MODELS = {
    "clinicalbert": "samrawal/bert-base-uncased_clinical-ner",
    "apollo": "Clinical-AI-Apollo/Medical-NER",
    "d4data": "d4data/biomedical-ner-all",
}
FLAIR_TAGGER = "hunflair2"
FLAIR_LINKERS = ("gene-linker", "disease-linker", "chemical-linker", "species-linker")
STANZA_TOKENIZERS = {"i2b2": "mimic", "radiology": "mimic"}
STANZA_DEFAULT_TOKENIZER = "craft"
SCISPACY_LINKER_MODELS = {"scispacy_scibert": "en_core_sci_scibert", "scispacy_md": "en_core_sci_md"}
BENT_MODEL_KINDS = (
    "Anatomical", "Bioprocess", "Cell-Component", "Cell-Line", "Cell-Type",
    "Chemical", "Disease", "Gene", "Organism", "Variant",
)


def read_image(image: str, path: Path = IMAGES_FILE) -> dict:
    with path.open("rb") as handle:
        return tomllib.load(handle)[image]


def fetch_annotator(annotator: str) -> None:
    if annotator in REMOTE_ANNOTATORS:
        return
    if annotator in HF_MODELS:
        from transformers import pipeline

        pipeline("ner", model=HF_MODELS[annotator], tokenizer=HF_MODELS[annotator])
    elif annotator == "flair":
        from flair.nn import Classifier

        Classifier.load(FLAIR_TAGGER)
    elif annotator.startswith("stanza_"):
        import stanza

        model = annotator.removeprefix("stanza_")
        tokenizer = STANZA_TOKENIZERS.get(model, STANZA_DEFAULT_TOKENIZER)
        stanza.download("en", package=None, processors={"tokenize": tokenizer, "ner": model}, verbose=False)
    elif annotator.startswith("scispacy_"):
        # Model packages are Python dependencies; only the UMLS linker data is downloaded.
        if annotator in SCISPACY_LINKER_MODELS:
            import scispacy.linking  # noqa: F401
            import spacy

            spacy.load(SCISPACY_LINKER_MODELS[annotator]).add_pipe("scispacy_linker", config={"linker_name": "umls"})
    elif annotator == "bent":
        script = (
            "from transformers import AutoModelForTokenClassification, AutoTokenizer\n"
            f"for kind in {BENT_MODEL_KINDS!r}:\n"
            "    model = f'pruas/BENT-PubMedBERT-NER-{kind}'\n"
            "    AutoModelForTokenClassification.from_pretrained(model)\n"
            "    AutoTokenizer.from_pretrained(model)\n"
        )
        subprocess.run([str(BENT_PYTHON), "-c", script], check=True)
    else:
        raise ValueError(f"No models known for annotator '{annotator}'.")


def fetch_flair_linkers() -> None:
    from flair.models import EntityMentionLinker

    for linker in FLAIR_LINKERS:
        EntityMentionLinker.load(linker)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("image", choices=("slim", "full"))
    image = read_image(parser.parse_args().image)
    for annotator in image["annotators"]:
        print(f"Fetching models for {annotator}", flush=True)
        fetch_annotator(annotator)
    if image.get("flair_linkers"):
        print("Fetching flair linkers", flush=True)
        fetch_flair_linkers()


if __name__ == "__main__":
    main()
