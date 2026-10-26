from __future__ import annotations

import logging
from functools import lru_cache
from typing import Any, Callable, Iterable

from bio_annotation.entity_proposal._shared import make_annotation
from bio_annotation.schemas.document import Document
from bio_annotation.schemas.entity import Annotation

SCISPACY_INSTALL_HINT = (
    "The scispaCy annotators require scispaCy and the supported model packages. "
    "Install them with: uv sync --extra scispacy"
)

SCISPACY_MODEL_BY_ANNOTATOR: dict[str, str] = {
    "scispacy_jnlpba": "en_ner_jnlpba_md",
    "scispacy_bc5cdr": "en_ner_bc5cdr_md",
    "scispacy_bionlp13cg": "en_ner_bionlp13cg_md",
    "scispacy_craft": "en_ner_craft_md",
    "scispacy_scibert": "en_core_sci_scibert",
    "scispacy_md": "en_core_sci_md",
}
SCISPACY_SCIBERT_ANNOTATOR = "scispacy_scibert"
SCISPACY_UMLS_LINKER = "scispacy_linker"
logger = logging.getLogger(__name__)

# The general scispaCy models (en_core_sci_scibert, en_core_sci_md) detect
# entities and link them to a knowledge base (UMLS by default). One linker per
# general model; the corpus NER models above do not link. linker_name is a config
# option and defaults to umls for these.
SCISPACY_LINKER_NAME_BY_ANNOTATOR: dict[str, str] = {
    "scispacy_scibert": "umls",
    "scispacy_md": "umls",
}
SCISPACY_LINKER_ANNOTATORS = frozenset(SCISPACY_LINKER_NAME_BY_ANNOTATOR)


@lru_cache(maxsize=8)
def _load_scispacy_model(model: str, *, linker_name: str | None = None) -> Any:
    try:
        import scispacy  # noqa: F401
        import scispacy.linking  # noqa: F401
        import spacy
    except ImportError as exc:
        raise RuntimeError(SCISPACY_INSTALL_HINT) from exc

    try:
        nlp = spacy.load(model)
    except OSError as exc:
        raise RuntimeError(
            f"scispaCy model '{model}' is not installed. {SCISPACY_INSTALL_HINT}"
        ) from exc
    if linker_name and SCISPACY_UMLS_LINKER not in nlp.pipe_names:
        nlp.add_pipe(
            SCISPACY_UMLS_LINKER,
            config={"resolve_abbreviations": True, "linker_name": linker_name},
        )
    return nlp


def _entity_kb_ents(entity: Any) -> list[tuple[str, float]]:
    extension = getattr(entity, "_", None)
    candidates = getattr(extension, "kb_ents", None) if extension is not None else None
    return list(candidates or [])


def _linker_canonical_name(linker: Any, cui: str) -> str | None:
    kb = getattr(linker, "kb", None)
    entity_by_cui = getattr(kb, "cui_to_entity", {}) if kb is not None else {}
    linked = entity_by_cui.get(cui) if hasattr(entity_by_cui, "get") else None
    canonical_name = getattr(linked, "canonical_name", None)
    return str(canonical_name).strip() if canonical_name else None


def _align_scispacy_offsets(
    document_text: str,
    span_text: str,
    start: Any,
    end: Any,
) -> tuple[int | None, int | None]:
    """Trim offset edges only when the selected text verifies that exact trim."""
    normalized_span = span_text.strip()
    try:
        start_offset, end_offset = int(start), int(end)
    except (TypeError, ValueError):
        return None, None

    if start_offset < 0 or end_offset < start_offset or end_offset > len(document_text):
        return None, None

    selected_text = document_text[start_offset:end_offset]
    if selected_text == normalized_span:
        return start_offset, end_offset
    if selected_text.strip() != normalized_span:
        return None, None

    leading_whitespace = len(selected_text) - len(selected_text.lstrip())
    trailing_whitespace = len(selected_text) - len(selected_text.rstrip())
    start_offset += leading_whitespace
    end_offset -= trailing_whitespace
    if document_text[start_offset:end_offset] != normalized_span:
        return None, None
    return start_offset, end_offset


def parse_scispacy_response(
    document: Document,
    payload: Iterable[Any] | None,
    *,
    source: str,
    linker: Any = None,
) -> list[Annotation]:
    if not payload:
        return []

    annotations: list[Annotation] = []
    unplaced_span_count = 0
    for entity in payload:
        raw_span_text = getattr(entity, "text", None)
        label = getattr(entity, "label_", None)
        start = getattr(entity, "start_char", None)
        end = getattr(entity, "end_char", None)
        canonical_id = None
        canonical_name = None
        normalization_score = None
        if source in SCISPACY_LINKER_ANNOTATORS:
            candidates = _entity_kb_ents(entity)
            if candidates:
                canonical_id, normalization_score = candidates[0]
                canonical_name = _linker_canonical_name(linker, str(canonical_id))
        if not raw_span_text:
            continue
        if source == SCISPACY_SCIBERT_ANNOTATOR:
            start, end = _align_scispacy_offsets(document.text, str(raw_span_text), start, end)
            if start is None or end is None:
                unplaced_span_count += 1
        annotations.append(
            make_annotation(
                document=document,
                source=source,
                span_text=raw_span_text,
                entity_type=label,
                start=start,
                end=end,
                canonical_id=canonical_id,
                canonical_name=canonical_name,
                normalization_score=normalization_score,
                infer_missing_offsets=source != SCISPACY_SCIBERT_ANNOTATOR,
            )
        )
    if unplaced_span_count:
        logger.warning(
            "scispaCy SciBERT returned %d spans for %s that could not be aligned to the document text; left unplaced",
            unplaced_span_count,
            document.document_id,
        )
    return annotations


def annotate_with_scispacy(
    document: Document,
    *,
    source: str,
    model: str,
    response: Any = None,
    request_fn: Callable[[Document], Any] | None = None,
    nlp: Any = None,
    model_loader: Callable[[str], Any] | None = None,
    linker_name: str | None = None,
) -> list[Annotation]:
    payload = response
    if payload is None and request_fn is not None:
        payload = request_fn(document)
    if payload is None:
        if nlp is None:
            loader = model_loader or _load_scispacy_model
            if source in SCISPACY_LINKER_ANNOTATORS:
                nlp = loader(
                    model,
                    linker_name=linker_name
                    or SCISPACY_LINKER_NAME_BY_ANNOTATOR.get(source, "umls"),
                )
            else:
                nlp = loader(model)
        parsed = nlp(document.text)
        payload = getattr(parsed, "ents", None)
    linker = None
    if source in SCISPACY_LINKER_ANNOTATORS and nlp is not None:
        try:
            linker = nlp.get_pipe(SCISPACY_UMLS_LINKER)
        except (KeyError, AttributeError):
            linker = None
    return parse_scispacy_response(document, payload, source=source, linker=linker)


def annotate_with_scispacy_jnlpba(
    document: Document,
    **kwargs: Any,
) -> list[Annotation]:
    model = kwargs.pop("model", SCISPACY_MODEL_BY_ANNOTATOR["scispacy_jnlpba"])
    return annotate_with_scispacy(
        document,
        source="scispacy_jnlpba",
        model=model,
        **kwargs,
    )


def annotate_with_scispacy_bc5cdr(
    document: Document,
    **kwargs: Any,
) -> list[Annotation]:
    model = kwargs.pop("model", SCISPACY_MODEL_BY_ANNOTATOR["scispacy_bc5cdr"])
    return annotate_with_scispacy(
        document,
        source="scispacy_bc5cdr",
        model=model,
        **kwargs,
    )


def annotate_with_scispacy_bionlp13cg(
    document: Document,
    **kwargs: Any,
) -> list[Annotation]:
    model = kwargs.pop("model", SCISPACY_MODEL_BY_ANNOTATOR["scispacy_bionlp13cg"])
    return annotate_with_scispacy(
        document,
        source="scispacy_bionlp13cg",
        model=model,
        **kwargs,
    )


def annotate_with_scispacy_craft(
    document: Document,
    **kwargs: Any,
) -> list[Annotation]:
    model = kwargs.pop("model", SCISPACY_MODEL_BY_ANNOTATOR["scispacy_craft"])
    return annotate_with_scispacy(
        document,
        source="scispacy_craft",
        model=model,
        **kwargs,
    )


def annotate_with_scispacy_scibert(
    document: Document,
    **kwargs: Any,
) -> list[Annotation]:
    model = kwargs.pop("model", SCISPACY_MODEL_BY_ANNOTATOR[SCISPACY_SCIBERT_ANNOTATOR])
    return annotate_with_scispacy(
        document,
        source=SCISPACY_SCIBERT_ANNOTATOR,
        model=model,
        linker_name=kwargs.pop("linker_name", "umls"),
        **kwargs,
    )


def annotate_with_scispacy_md(
    document: Document,
    **kwargs: Any,
) -> list[Annotation]:
    model = kwargs.pop("model", SCISPACY_MODEL_BY_ANNOTATOR["scispacy_md"])
    return annotate_with_scispacy(
        document,
        source="scispacy_md",
        model=model,
        linker_name=kwargs.pop("linker_name", "umls"),
        **kwargs,
    )
