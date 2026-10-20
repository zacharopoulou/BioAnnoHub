# BioNLP11EPI analytics

## TRAIN

- Documents: **600**
- Entity mentions: **8226** across **600** documents

### Entity counts by type

| type    |   n_mentions |
|:--------|-------------:|
| Entity  |          631 |
| Protein |         7595 |

### Entities per document

|       |     0 |
|:------|------:|
| count | 600   |
| mean  |  13.7 |
| min   |   1   |
| 50%   |  12   |
| max   |  49   |

### Span length (chars)

|       |   span_length |
|:------|--------------:|
| count |        8226   |
| mean  |           7.4 |
| min   |           1   |
| 50%   |           5   |
| max   |          75   |

### Normalization: 0 / 8226 (0.0%)

### Top 5 mentions per entity type (case-insensitive)

#### Entity

| text_joined   |   n |
|:--------------|----:|
| promoter      |  45 |
| k9            |  31 |
| k4            |  20 |
| lysine 9      |  16 |
| lysine        |  15 |

#### Protein

| text_joined   |   n |
|:--------------|----:|
| histone       | 221 |
| ubiquitin     | 216 |
| h3            | 160 |
| p53           | 109 |
| histone h3    |  94 |

## VALIDATION

- Documents: **200**
- Entity mentions: **2712** across **200** documents

### Entity counts by type

| type    |   n_mentions |
|:--------|-------------:|
| Entity  |          213 |
| Protein |         2499 |

### Entities per document

|       |     0 |
|:------|------:|
| count | 200   |
| mean  |  13.6 |
| min   |   1   |
| 50%   |  12   |
| max   |  46   |

### Span length (chars)

|       |   span_length |
|:------|--------------:|
| count |        2712   |
| mean  |           7.5 |
| min   |           1   |
| 50%   |           5   |
| max   |          78   |

### Normalization: 0 / 2712 (0.0%)

### Top 5 mentions per entity type (case-insensitive)

#### Entity

| text_joined   |   n |
|:--------------|----:|
| promoter      |  30 |
| k4            |  11 |
| k27           |   8 |
| k79           |   8 |
| lysine 4      |   7 |

#### Protein

| text_joined   |   n |
|:--------------|----:|
| histone       |  76 |
| ubiquitin     |  68 |
| h3            |  67 |
| hif-1alpha    |  48 |
| cd44          |  33 |

## TEST

- Documents: **440**
- Entity mentions: **5737** across **440** documents

### Entity counts by type

| type    |   n_mentions |
|:--------|-------------:|
| Protein |         5737 |

### Entities per document

|       |   0 |
|:------|----:|
| count | 440 |
| mean  |  13 |
| min   |   1 |
| 50%   |  11 |
| max   |  50 |

### Span length (chars)

|       |   span_length |
|:------|--------------:|
| count |        5737   |
| mean  |           7.1 |
| min   |           1   |
| 50%   |           5   |
| max   |          85   |

### Normalization: 0 / 5737 (0.0%)

### Top 5 mentions per entity type (case-insensitive)

#### Protein

| text_joined   |   n |
|:--------------|----:|
| ubiquitin     | 153 |
| h3            | 143 |
| histone       | 140 |
| p53           |  79 |
| hif-1alpha    |  69 |
