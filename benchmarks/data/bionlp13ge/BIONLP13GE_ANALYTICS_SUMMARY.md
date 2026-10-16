# BioNLP13GE analytics

## TRAIN

- Documents: **222**
- Entity mentions: **3797** across **194** documents

### Entity counts by type

| type     |   n_mentions |
|:---------|-------------:|
| Anaphora |          105 |
| Entity   |          121 |
| Protein  |         3571 |

### Entities per document

|       |     0 |
|:------|------:|
| count | 194   |
| mean  |  19.6 |
| min   |   1   |
| 50%   |  11   |
| max   | 122   |

### Span length (chars)

|       |   span_length |
|:------|--------------:|
| count |        3797   |
| mean  |           5.7 |
| min   |           1   |
| 50%   |           5   |
| max   |          70   |

### Normalization: 0 / 3797 (0.0%)

### Top 5 mentions per entity type (case-insensitive)

#### Anaphora

| text_joined   |   n |
|:--------------|----:|
| its           |  14 |
| which         |   9 |
| it            |   6 |
| this          |   5 |
| both proteins |   2 |

#### Entity

| text_joined   |   n |
|:--------------|----:|
| ser276        |  37 |
| ser536        |  17 |
| nuclear       |  10 |
| promoter      |   8 |
| nucleus       |   5 |

#### Protein

| text_joined   |   n |
|:--------------|----:|
| lmp1          | 206 |
| foxp3         | 194 |
| il-10         | 160 |
| hoip          | 154 |
| irf-4         | 134 |

## VALIDATION

- Documents: **249**
- Entity mentions: **4570** across **212** documents

### Entity counts by type

| type     |   n_mentions |
|:---------|-------------:|
| Anaphora |          117 |
| Binding  |            1 |
| Entity   |          314 |
| Protein  |         4138 |

### Entities per document

|       |     0 |
|:------|------:|
| count | 212   |
| mean  |  21.6 |
| min   |   1   |
| 50%   |  11   |
| max   | 186   |

### Span length (chars)

|       |   span_length |
|:------|--------------:|
| count |        4570   |
| mean  |           5.9 |
| min   |           1   |
| 50%   |           5   |
| max   |          62   |

### Normalization: 0 / 4570 (0.0%)

### Top 5 mentions per entity type (case-insensitive)

#### Anaphora

| text_joined   |   n |
|:--------------|----:|
| its           |  17 |
| it            |  13 |
| which         |   8 |
| they          |   5 |
| the repressor |   3 |

#### Binding

| text_joined   |   n |
|:--------------|----:|
| association   |   1 |

#### Entity

| text_joined   |   n |
|:--------------|----:|
| nuclear       | 105 |
| promoter      |  46 |
| s209          |  37 |
| nucleus       |  10 |
| gc-box        |   7 |

#### Protein

| text_joined   |   n |
|:--------------|----:|
| foxp3         | 339 |
| tat           | 188 |
| rps3          | 180 |
| cd4           | 166 |
| p65           | 158 |

## TEST

- Documents: **305**
- Entity mentions: **4359** across **256** documents

### Entity counts by type

| type    |   n_mentions |
|:--------|-------------:|
| Protein |         4359 |

### Entities per document

|       |   0 |
|:------|----:|
| count | 256 |
| mean  |  17 |
| min   |   1 |
| 50%   |  10 |
| max   | 208 |

### Span length (chars)

|       |   span_length |
|:------|--------------:|
| count |        4359   |
| mean  |           6.6 |
| min   |           1   |
| 50%   |           5   |
| max   |          76   |

### Normalization: 0 / 4359 (0.0%)

### Top 5 mentions per entity type (case-insensitive)

#### Protein

| text_joined   |   n |
|:--------------|----:|
| serpinb2      | 170 |
| ccr5          | 153 |
| nfat5         | 138 |
| tnfalpha      | 135 |
| il-1ra        | 131 |
