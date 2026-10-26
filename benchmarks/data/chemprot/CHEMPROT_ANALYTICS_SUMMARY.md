# ChemProt analytics

## TRAIN

- Documents: **1020**
- Entity mentions: **25752** across **1020** documents

### Entity counts by type

| type     |   n_mentions |
|:---------|-------------:|
| CHEMICAL |        13017 |
| GENE-N   |         4387 |
| GENE-Y   |         8348 |

### Entities per document

|       |      0 |
|:------|-------:|
| count | 1020   |
| mean  |   25.2 |
| min   |    1   |
| 50%   |   24   |
| max   |   85   |

### Span length (chars)

|       |   span_length |
|:------|--------------:|
| count |         25752 |
| mean  |            10 |
| min   |             1 |
| 50%   |             8 |
| max   |           160 |

### Normalization: 0 / 25752 (0.0%)

### Top 5 mentions per entity type (case-insensitive)

#### CHEMICAL

| text_joined   |   n |
|:--------------|----:|
| glucose       | 161 |
| dopamine      | 112 |
| serotonin     |  90 |
| cholesterol   |  78 |
| ca(2+)        |  76 |

#### GENE-N

| text_joined   |   n |
|:--------------|----:|
| nf-κb         |  67 |
| insulin       |  60 |
| akt           |  40 |
| erk1/2        |  35 |
| hdl           |  33 |

#### GENE-Y

| text_joined   |   n |
|:--------------|----:|
| insulin       | 142 |
| cox-2         |  84 |
| dat           |  64 |
| ache          |  49 |
| inos          |  48 |

## VALIDATION

- Documents: **612**
- Entity mentions: **15567** across **612** documents

### Entity counts by type

| type     |   n_mentions |
|:---------|-------------:|
| CHEMICAL |         8004 |
| GENE-N   |         2412 |
| GENE-Y   |         5151 |

### Entities per document

|       |     0 |
|:------|------:|
| count | 612   |
| mean  |  25.4 |
| min   |   2   |
| 50%   |  24   |
| max   |  80   |

### Span length (chars)

|       |   span_length |
|:------|--------------:|
| count |         15567 |
| mean  |            10 |
| min   |             1 |
| 50%   |             8 |
| max   |           116 |

### Normalization: 0 / 15567 (0.0%)

### Top 5 mentions per entity type (case-insensitive)

#### CHEMICAL

| text_joined   |   n |
|:--------------|----:|
| glucose       |  89 |
| dopamine      |  76 |
| cholesterol   |  56 |
| glutathione   |  54 |
| amino acid    |  51 |

#### GENE-N

| text_joined   |   n |
|:--------------|----:|
| insulin       |  49 |
| mapk          |  28 |
| p38           |  26 |
| creb          |  26 |
| akt           |  25 |

#### GENE-Y

| text_joined   |   n |
|:--------------|----:|
| cox-2         |  57 |
| p53           |  54 |
| ache          |  51 |
| insulin       |  50 |
| er            |  28 |

## TEST

- Documents: **800**
- Entity mentions: **20828** across **800** documents

### Entity counts by type

| type     |   n_mentions |
|:---------|-------------:|
| CHEMICAL |        10810 |
| GENE-N   |         3360 |
| GENE-Y   |         6658 |

### Entities per document

|       |   0 |
|:------|----:|
| count | 800 |
| mean  |  26 |
| min   |   2 |
| 50%   |  24 |
| max   | 113 |

### Span length (chars)

|       |   span_length |
|:------|--------------:|
| count |       20828   |
| mean  |          10.3 |
| min   |           1   |
| 50%   |           8   |
| max   |         174   |

### Normalization: 0 / 20828 (0.0%)

### Top 5 mentions per entity type (case-insensitive)

#### CHEMICAL

| text_joined   |   n |
|:--------------|----:|
| glucose       | 121 |
| cholesterol   |  72 |
| calcium       |  65 |
| histamine     |  64 |
| atp           |  61 |

#### GENE-N

| text_joined   |   n |
|:--------------|----:|
| akt           |  49 |
| insulin       |  42 |
| kinase        |  37 |
| ampk          |  32 |
| cytokines     |  28 |

#### GENE-Y

| text_joined   |   n |
|:--------------|----:|
| insulin       | 107 |
| cox-2         |  92 |
| egfr          |  57 |
| erα           |  46 |
| ache          |  31 |
