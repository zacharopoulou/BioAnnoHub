# Annotator guide

## Supported annotators and entity types

The 24 entries include model-specific integrations from the same tool family, such as scispaCy and Stanza. `NER` identifies mentions; `NEN` links mentions to concepts or identifiers. HunFlair requires its linkers for NEN. MedCAT's available labels depend on its loaded model pack. Optional models and services may need separate installation or configuration.

| Annotator | Domain | NER | NEN | Entity types |
|---|---|:---:|:---:|---|
| PubTator3 | Biomedical | Yes | Yes | Gene / protein, disease, chemical / drug, species, variant / mutation, cell line |
| BERN2 | Biomedical | Yes | Yes | Gene / protein, disease, chemical / drug, species, variant / mutation, cell line, cell type, DNA, RNA |
| Flair / HunFlair | Biomedical | Yes | Yes¹ | Gene / protein, disease, chemical / drug, species, cell line |
| MedCAT | Clinical | Yes | Yes | Labels and concepts defined by the loaded model pack |
| scispaCy `en_core_sci_scibert` | Biomedical | Yes | Yes² | Generic biomedical mention (`ENTITY`) |
| scispaCy `en_core_sci_md` | Biomedical | Yes | Yes² | Generic biomedical mention (`ENTITY`) |
| scispaCy `en_ner_bc5cdr_md` | Biomedical | Yes | No | Disease, chemical / drug |
| scispaCy `en_ner_jnlpba_md` | Biomedical | Yes | No | DNA, RNA, gene / protein, cell type, cell line |
| scispaCy `en_ner_bionlp13cg_md` | Biomedical | Yes | No | Amino acid, anatomical system, cancer, cell, cellular component, developing anatomical structure, gene, immaterial anatomical entity, multi-tissue structure, organ, species, organism subdivision, organism substance, pathological formation, chemical / drug, tissue |
| scispaCy `en_ner_craft_md` | Biomedical | Yes | No | Gene / protein, chemical, cell type, species, Gene Ontology, Sequence Ontology |
| BENT | Biomedical | Yes | Yes | Disease, chemical / drug, gene / protein, species, biological process, anatomical entity, cellular component, cell type, cell line, variant / mutation |
| ClinicalBERT | Clinical | Yes | No | Problem, test, treatment |
| Clinical-AI-Apollo Medical-NER | Clinical | Yes | No | MACCROBAT label set³ |
| d4data `biomedical-ner-all` | Clinical | Yes | No | MACCROBAT label set³ |
| Stanza BC5CDR | Biomedical | Yes | No | Disease, chemical / drug |
| Stanza BioNLP13CG | Biomedical | Yes | No | Amino acid, anatomical system, cancer, cell, cellular component, developing anatomical structure, gene, immaterial anatomical entity, multi-tissue structure, organ, species, organism subdivision, organism substance, pathological formation, chemical / drug, tissue |
| Stanza JNLPBA | Biomedical | Yes | No | Gene / protein, DNA, RNA, cell line, cell type |
| Stanza AnatEM | Biomedical | Yes | No | Anatomical entity |
| Stanza BC4CHEMD | Biomedical | Yes | No | Chemical / drug |
| Stanza Linnaeus | Biomedical | Yes | No | Species |
| Stanza NCBI-Disease | Biomedical | Yes | No | Disease |
| Stanza S800 | Biomedical | Yes | No | Species |
| Stanza i2b2 | Clinical | Yes | No | Problem, test, treatment |
| Stanza radiology | Clinical | Yes | No | Anatomy, anatomy modifier, observation, observation modifier, uncertainty |

¹ HunFlair NEN is available when its entity linkers are enabled. ² These general scispaCy models link generic `ENTITY` mentions to UMLS; the linker does not assign biomedical entity categories such as disease or gene. ³ The MACCROBAT labels are disease/disorder, medication, activity, administration, age, area, biological attribute, biological structure, clinical event, color, coreference, date, detailed description, diagnostic procedure, distance, dosage, duration, family history, frequency, height, history, lab value, mass, nonbiological location, occupation, other entity, other event, outcome, personal background, qualitative concept, quantitative concept, severity, sex, shape, sign/symptom, subject, texture, therapeutic procedure, time, volume, and weight.
