from __future__ import annotations

from functools import lru_cache
from typing import Any, Callable, Iterable

from bio_annotation.entity_proposal._shared import make_annotation
from bio_annotation.schemas.document import Document
from bio_annotation.schemas.entity import Annotation

SpanKey = tuple[int | None, int | None, str]
LinkInfo = tuple[str | None, str | None, Any]


def _extract_flair_label(span: Any) -> tuple[Any, Any]:
    if hasattr(span, "get_label"):
        label = span.get_label("ner")
        return getattr(label, "value", None), getattr(label, "score", None)

    labels = getattr(span, "labels", None)
    if labels:
        first = labels[0]
        return getattr(first, "value", None), getattr(first, "score", None)

    return getattr(span, "tag", None), getattr(span, "score", None)


def _span_key(span: Any) -> SpanKey:
    text = getattr(span, "text", None)
    if text is None and hasattr(span, "to_original_text"):
        text = span.to_original_text()
    return (
        getattr(span, "start_position", None),
        getattr(span, "end_position", None),
        str(text or "").strip(),
    )


def _parse_link_value(value: Any) -> tuple[str | None, str | None]:
    if value is None:
        return None, None

    text = str(value).strip()
    if not text:
        return None, None

    canonical_id, separator, metadata = text.partition("/name=")
    canonical_name = metadata.strip() if separator else None
    return canonical_id.strip() or None, canonical_name or None


def _flair_links_by_span(labels: Iterable[Any] | None) -> dict[SpanKey, LinkInfo]:
    links: dict[SpanKey, LinkInfo] = {}
    for label in labels or []:
        span = getattr(label, "data_point", None)
        if span is None:
            continue
        canonical_id, canonical_name = _parse_link_value(getattr(label, "value", None))
        if canonical_id is None:
            continue
        links.setdefault(
            _span_key(span),
            (canonical_id, canonical_name, getattr(label, "score", None)),
        )
    return links


def _get_sentence_labels(sentence: Any, label_type: str) -> Iterable[Any]:
    try:
        return sentence.get_labels(label_type)
    except TypeError:
        if label_type == "ner":
            return sentence.get_labels()
        return []


def parse_flair_spans(
    document: Document,
    spans: Iterable[Any],
    *,
    link_labels: Iterable[Any] | None = None,
) -> list[Annotation]:
    annotations: list[Annotation] = []
    links_by_span = _flair_links_by_span(link_labels)
    for span in spans:
        label, score = _extract_flair_label(span)
        text = getattr(span, "text", None)
        if text is None and hasattr(span, "to_original_text"):
            text = span.to_original_text()
        if not text:
            continue
        canonical_id, canonical_name, link_score = links_by_span.get(
            _span_key(span),
            (None, None, None),
        )

        annotations.append(
            make_annotation(
                document=document,
                source="flair",
                span_text=text,
                entity_type=label,
                start=getattr(span, "start_position", None),
                end=getattr(span, "end_position", None),
                canonical_id=canonical_id,
                canonical_name=canonical_name,
                confidence=score if score is not None else link_score,
            )
        )

    return annotations


@lru_cache(maxsize=4)
def _load_flair_tagger(model: str) -> Any:
    from flair.models import SequenceTagger

    return SequenceTagger.load(model)


def parse_flair_labels(
    document: Document,
    labels: Iterable[Any],
    *,
    link_labels: Iterable[Any] | None = None,
) -> list[Annotation]:
    annotations: list[Annotation] = []
    links_by_span = _flair_links_by_span(link_labels)
    for label in labels:
        span = getattr(label, "data_point", None)
        if span is None:
            continue
        text = getattr(span, "text", None)
        if not text:
            continue
        canonical_id, canonical_name, link_score = links_by_span.get(
            _span_key(span),
            (None, None, None),
        )

        annotations.append(
            make_annotation(
                document=document,
                source="flair",
                span_text=text,
                entity_type=getattr(label, "value", None),
                start=getattr(span, "start_position", None),
                end=getattr(span, "end_position", None),
                canonical_id=canonical_id,
                canonical_name=canonical_name,
                confidence=(
                    getattr(label, "score", None)
                    if getattr(label, "score", None) is not None
                    else link_score
                ),
            )
        )

    return annotations


def annotate_with_flair(
    document: Document,
    *,
    spans: Iterable[Any] | None = None,
    tagger: Any = None,
    linkers: Iterable[Any] | None = None,
    model: str | None = None,
    tagger_loader: Callable[[str], Any] | None = None,
    sentence_factory: Callable[[str], Any] | None = None,
) -> list[Annotation]:
    if spans is not None:
        return parse_flair_spans(document, spans)

    if tagger is None and model:
        loader = tagger_loader or _load_flair_tagger
        tagger = loader(model)

    if tagger is not None:
        if sentence_factory is None:
            try:
                from flair.data import Sentence
            except ImportError:
                return []
            sentence = Sentence(document.text)
        else:
            sentence = sentence_factory(document.text)

        tagger.predict(sentence)
        for linker in linkers or []:
            linker.predict(sentence)
        if hasattr(sentence, "get_labels"):
            return parse_flair_labels(
                document,
                _get_sentence_labels(sentence, "ner"),
                link_labels=_get_sentence_labels(sentence, "link"),
            )
        if hasattr(sentence, "get_spans"):
            link_labels = sentence.get_labels("link") if hasattr(sentence, "get_labels") else None
            return parse_flair_spans(document, sentence.get_spans("ner"), link_labels=link_labels)
        return []

    return []
