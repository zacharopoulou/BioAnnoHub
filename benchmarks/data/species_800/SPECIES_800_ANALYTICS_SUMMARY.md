# Species-800 analytics

## TRAIN

- Documents: **560** (PubMed abstracts)
- Entity mentions: **2557** across **437** documents (123 documents have no species mentions)

### Species: 527 unique NCBI Taxonomy IDs

#### Top 10 NCBI Taxonomy IDs

|   ncbi_taxon_id |   n_mentions |
|----------------:|-------------:|
|            9606 |           68 |
|            4932 |           57 |
|             562 |           57 |
|           11676 |           40 |
|            4530 |           37 |
|           10090 |           37 |
|          162425 |           34 |
|          746128 |           32 |
|           11176 |           31 |
|           11103 |           30 |

### Entity counts by type

| type    |   n_mentions |
|:--------|-------------:|
| Species |         2557 |

### Entities per document

|       |     0 |
|:------|------:|
| count | 437   |
| mean  |   5.9 |
| min   |   1   |
| 50%   |   5   |
| max   |  35   |

### Span length (chars)

|       |   span_length |
|:------|--------------:|
| count |        2557   |
| mean  |          13.3 |
| min   |           1   |
| 50%   |          12   |
| max   |          54   |

### Normalization: 2557 / 2557 (100.0%)

| db_name       |   n_ids |
|:--------------|--------:|
| NCBI Taxonomy |    2557 |

### Top 5 mentions per entity type (case-insensitive)

#### Species

| text_joined      |   n |
|:-----------------|----:|
| human            |  58 |
| yeast            |  33 |
| escherichia coli |  33 |
| hiv-1            |  30 |
| hiv              |  27 |

## VALIDATION

- Documents: **80** (PubMed abstracts)
- Entity mentions: **384** across **63** documents (17 documents have no species mentions)

### Species: 100 unique NCBI Taxonomy IDs

#### Top 10 NCBI Taxonomy IDs

|   ncbi_taxon_id |   n_mentions |
|----------------:|-------------:|
|           11723 |           20 |
|            9606 |           15 |
|           11676 |           13 |
|            5518 |           12 |
|           11234 |           10 |
|           10359 |            9 |
|             959 |            9 |
|          369451 |            9 |
|          670155 |            8 |
|          670154 |            8 |

### Entity counts by type

| type    |   n_mentions |
|:--------|-------------:|
| Species |          384 |

### Entities per document

|       |    0 |
|:------|-----:|
| count | 63   |
| mean  |  6.1 |
| min   |  1   |
| 50%   |  5   |
| max   | 28   |

### Span length (chars)

|       |   span_length |
|:------|--------------:|
| count |         384   |
| mean  |          12.6 |
| min   |           2   |
| 50%   |          11   |
| max   |          38   |

### Normalization: 384 / 384 (100.0%)

| db_name       |   n_ids |
|:--------------|--------:|
| NCBI Taxonomy |     384 |

### Top 5 mentions per entity type (case-insensitive)

#### Species

| text_joined   |   n |
|:--------------|----:|
| human         |  13 |
| hiv-1         |  10 |
| sivmac239     |   7 |
| hcmv          |   7 |
| hiv           |   7 |

## TEST

- Documents: **160** (PubMed abstracts)
- Entity mentions: **767** across **125** documents (35 documents have no species mentions)

### Species: 188 unique NCBI Taxonomy IDs

#### Top 10 NCBI Taxonomy IDs

|   ncbi_taxon_id |   n_mentions |
|----------------:|-------------:|
|           11320 |           46 |
|            9606 |           29 |
|            5518 |           20 |
|           11676 |           19 |
|             562 |           17 |
|           10090 |           14 |
|          318829 |           12 |
|            4577 |           12 |
|           12092 |           12 |
|            4932 |           11 |

### Entity counts by type

| type    |   n_mentions |
|:--------|-------------:|
| Species |          767 |

### Entities per document

|       |     0 |
|:------|------:|
| count | 125   |
| mean  |   6.1 |
| min   |   1   |
| 50%   |   4   |
| max   |  28   |

### Span length (chars)

|       |   span_length |
|:------|--------------:|
| count |         767   |
| mean  |          13.3 |
| min   |           2   |
| 50%   |          12   |
| max   |          48   |

### Normalization: 767 / 767 (100.0%)

| db_name       |   n_ids |
|:--------------|--------:|
| NCBI Taxonomy |     767 |

### Top 5 mentions per entity type (case-insensitive)

#### Species

| text_joined      |   n |
|:-----------------|----:|
| human            |  26 |
| hiv-1            |  16 |
| maize            |  10 |
| escherichia coli |  10 |
| yc6903           |   8 |
