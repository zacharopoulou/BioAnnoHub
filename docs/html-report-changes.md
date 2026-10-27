# HTML report changes (branch `html-report-fixes`)

Draft summary of what was added to the HTML report (`results.html`).

## 1. Every annotator is now visible

Before, only some entity types had colours, so tags from ClinicalBERT, d4data, MedCAT, Stanza radiology and scispaCy did not show in the text.

- **Colour families:** every entity type belongs to one of 10 families, each with its own colour:
  Gene / protein, Chemical / drug, Disease / problem, Species, Variant, Cell, Anatomy, Test / treatment, Clinical detail, Other.
  Unknown types fall into "Other", so nothing is invisible!
- **Type label in each highlight:** a small label inside the box (can be switched off with "Show type labels".)
- **Filters:** checkboxes to show or hide each annotator and entity family. When several annotators tag the same words, only one tag can be shown; hiding an annotator reveals the tag of the next one underneath.

- **Annotator order:** when highlights overlap, known annotators win first (PubTator3, BERN2, ..), then the others alphabetically.
- **Legend, stats and histogram** use the same family colours.
- **Layout:** the "Bioconcepts" panels scroll at a fixed height instead of stretching the page.

## 2. Popup and label details

- **Normalization score:** shown when an annotator gives one (e.g. scispaCy, MedCAT), in the popup 
- **MedCAT semantic types:** codes are shown with their UMLS name, e.g. `T191 · Neoplastic Process`. The 127 names are stored in `src/bio_annotation/report/umls_semantic_types.py` (from UMLS 2018AB), so the report does not need the benchmark data.
- **Extra spaces:** highlights no longer include spaces before or after the entity, and "Breast  cancer " and "breast cancer" count as the same keyword.
- "Variant / mutation" label kept as it is.

## 3. Entity graph added

- **Nodes:** one circle per entity, coloured by family, sized by number of mentions(same text found by different annotators is one circle -case and extra spaces ignored)
- **Links:** two entities are linked when mentioned in the **same sentence** (default) or the **same document** (dropdown). Thicker line means together more ofte (links are made regardless of which annotator found each entity)

- **Filters:** the annotator and entity type checkboxes also apply to the graph.
- Circles can be dragged.
- **Technical:** plain JavaScript and SVG, no libraries, so the report stays one file that works offline. Python (`build_graph_data` in  `src/bio_annotation/report/html_report.py`) only collects entities, sentences and mentions-> the browser builds the links and the layout (a simple force-directed layout).

## Files changed

| File | Change |
| --- | --- |
| `src/bio_annotation/report/html_report.py` | report data and HTML |
| `src/bio_annotation/report/template.html` | styles, filters, graph |
| `src/bio_annotation/report/umls_semantic_types.py` | new: UMLS type names |
| `tests/test_html_report.py` | 7 new tests |

## Still to do

- Phase 4: tests for every input type (PMIDs, PMID file, plain text, text table, documents without a title).
