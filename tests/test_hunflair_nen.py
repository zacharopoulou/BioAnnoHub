from __future__ import annotations

from dataclasses import dataclass, field

from bio_annotation.annotators.flair import annotate_with_flair
from bio_annotation.entity_types import normalization_databases
from bio_annotation.schemas.document import Document


@dataclass
class FakeLabel:
    value: str
    score: float
    data_point: object | None = None
    metadata: dict[str, object] = field(default_factory=dict)


@dataclass
class FakeSpan:
    text: str
    start_position: int
    end_position: int


class FakeSentence:
    def __init__(self, text: str) -> None:
        self.text = text
        self.ner_labels: list[FakeLabel] = []
        self.link_labels: list[FakeLabel] = []

    def get_labels(self, label_type: str | None = None) -> list[FakeLabel]:
        if label_type == "link":
            return self.link_labels
        return self.ner_labels


class FakeTagger:
    def __init__(self, label: FakeLabel) -> None:
        self.label = label

    def predict(self, sentence: FakeSentence) -> None:
        sentence.ner_labels = [self.label]


class FakeLinker:
    def __init__(self, label: FakeLabel) -> None:
        self.label = label

    def predict(self, sentence: FakeSentence) -> None:
        sentence.link_labels = [self.label]


def test_hunflair_linker_reads_name_metadata_and_keeps_scores_separate() -> None:
    document = Document(
        document_id="doc1",
        title="PTEN study",
        abstract="",
        source="test",
    )
    span = FakeSpan(text="PTEN", start_position=0, end_position=4)
    ner_label = FakeLabel(value="Gene", score=0.99, data_point=span)
    link_label = FakeLabel(
        value="NCBIGene:5728",
        score=211.5,
        data_point=span,
        metadata={"name": "PTEN"},
    )

    annotations = annotate_with_flair(
        document,
        tagger=FakeTagger(ner_label),
        linkers=[FakeLinker(link_label)],
        sentence_factory=FakeSentence,
    )

    assert len(annotations) == 1
    annotation = annotations[0]
    assert annotation.canonical_id == "NCBIGene:5728"
    assert annotation.canonical_name == "PTEN"
    assert annotation.confidence == 0.99
    assert annotation.normalization_score == 211.5


def test_hunflair_disease_and_chemical_ids_are_mesh() -> None:
    assert normalization_databases("disease", "flair") == ("MeSH",)
    assert normalization_databases("chemical", "flair") == ("MeSH",)
