# BioNLP09 analytics

## TRAIN

- Documents: **800**
- Entity mentions: **9734** across **756** documents

### Entity counts by type

| type    |   n_mentions |
|:--------|-------------:|
| Entity  |          434 |
| Protein |         9300 |

### Entities per document

|       |     0 |
|:------|------:|
| count | 756   |
| mean  |  12.9 |
| min   |   1   |
| 50%   |  11.5 |
| max   |  51   |

### Span length (chars)

|       |   span_length |
|:------|--------------:|
| count |        9734   |
| mean  |           7.5 |
| min   |           1   |
| 50%   |           5   |
| max   |         107   |

### Normalization: 0 / 9734 (0.0%)

### Top 5 mentions per entity type (case-insensitive)

#### Entity

| text_joined   |   n |
|:--------------|----:|
| promoter      | 184 |
| nuclear       |  44 |
| tyrosine      |  29 |
| nucleus       |  15 |
| enhancer      |  14 |

#### Protein

| text_joined   |   n |
|:--------------|----:|
| il-2          | 428 |
| tnf-alpha     | 212 |
| il-4          | 207 |
| p50           | 190 |
| p65           | 162 |

## VALIDATION

- Documents: **150**
- Entity mentions: **2174** across **150** documents

### Entity counts by type

| type    |   n_mentions |
|:--------|-------------:|
| Entity  |           94 |
| Protein |         2080 |

### Entities per document

|       |     0 |
|:------|------:|
| count | 150   |
| mean  |  14.5 |
| min   |   1   |
| 50%   |  12.5 |
| max   |  39   |

### Span length (chars)

|       |   span_length |
|:------|--------------:|
| count |        2174   |
| mean  |           7.7 |
| min   |           1   |
| 50%   |           5   |
| max   |          72   |

### Normalization: 0 / 2174 (0.0%)

### Top 5 mentions per entity type (case-insensitive)

#### Entity

| text_joined                   |   n |
|:------------------------------|----:|
| promoter                      |  39 |
| tyrosine                      |   9 |
| nuclear                       |   8 |
| promoter-enhancer             |   3 |
| transcription initiation site |   2 |

#### Protein

| text_joined   |   n |
|:--------------|----:|
| il-2          |  98 |
| tnf-alpha     |  56 |
| p65           |  40 |
| p50           |  39 |
| gm-csf        |  37 |

## TEST

- Documents: **260**
- Entity mentions: **3589** across **260** documents

### Entity counts by type

| type    |   n_mentions |
|:--------|-------------:|
| Protein |         3589 |

### Entities per document

|       |     0 |
|:------|------:|
| count | 260   |
| mean  |  13.8 |
| min   |   1   |
| 50%   |  12.5 |
| max   |  56   |

### Span length (chars)

|       |   span_length |
|:------|--------------:|
| count |        3589   |
| mean  |           7.3 |
| min   |           1   |
| 50%   |           5   |
| max   |          72   |

### Normalization: 0 / 3589 (0.0%)

### Top 5 mentions per entity type (case-insensitive)

#### Protein

| text_joined   |   n |
|:--------------|----:|
| il-2          | 153 |
| il-10         |  63 |
| stat3         |  61 |
| p65           |  56 |
| il-4          |  53 |
