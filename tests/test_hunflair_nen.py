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


def test_flair_processes_title_and_abstract_separately_and_shifts_body_offsets() -> None:
    document = Document(
        document_id="doc1",
        title="Study of PTEN",
        abstract="PTEN is a gene.",
        source="test",
    )
    seen_texts: list[str] = []

    class FakeTagger:
        def predict(self, sentence: FakeSentence) -> None:
            sentence.ner_labels = []
            if sentence.text == document.abstract:
                span = FakeSpan(text="PTEN", start_position=0, end_position=4)
                sentence.ner_labels = [FakeLabel(value="Gene", score=0.99, data_point=span)]

    def sentence_factory(text: str) -> FakeSentence:
        seen_texts.append(text)
        return FakeSentence(text)

    annotations = annotate_with_flair(
        document,
        tagger=FakeTagger(),
        sentence_factory=sentence_factory,
    )

    assert seen_texts == [document.title, document.abstract]
    assert len(annotations) == 1
    annotation = annotations[0]
    assert annotation.start == len(document.title) + 2
    assert document.text[annotation.start : annotation.end] == annotation.span_text == "PTEN"


def test_hunflair_disease_ids_include_mesh_and_omim() -> None:
    assert normalization_databases("disease", "flair") == ("MeSH", "OMIM")
    assert normalization_databases("chemical", "flair") == ("MeSH",)
