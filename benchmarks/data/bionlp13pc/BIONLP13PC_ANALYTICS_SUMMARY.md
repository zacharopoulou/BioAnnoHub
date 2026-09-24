# BioNLP13PC analytics

## TRAIN

- Documents: **260**
- Entity mentions: **7855** across **260** documents

### Entity counts by type

| type                 |   n_mentions |
|:---------------------|-------------:|
| Cellular_component   |          478 |
| Complex              |          729 |
| Gene_or_gene_product |         5468 |
| Simple_chemical      |         1180 |

### Entities per document

|       |     0 |
|:------|------:|
| count | 260   |
| mean  |  30.2 |
| min   |   2   |
| 50%   |  28   |
| max   |  90   |

### Span length (chars)

|       |   span_length |
|:------|--------------:|
| count |          7855 |
| mean  |             8 |
| min   |             1 |
| 50%   |             5 |
| max   |           102 |

### Normalization: 0 / 7855 (0.0%)

### Top 5 mentions per entity type (case-insensitive)

#### Cellular_component

| text_joined   |   n |
|:--------------|----:|
| nuclear       |  89 |
| nucleus       |  32 |
| membrane      |  19 |
| cytoplasm     |  18 |
| chromatin     |  18 |

#### Complex

| text_joined           |   n |
|:----------------------|----:|
| nf-kappab             | 214 |
| nf-kappa b            |  41 |
| ikk                   |  22 |
| nuclear factor-kappab |  16 |
| mtorc1                |  15 |

#### Gene_or_gene_product

| text_joined   |   n |
|:--------------|----:|
| p53           | 125 |
| e2f           | 107 |
| mtor          |  84 |
| e2f1          |  71 |
| wnt           |  63 |

#### Simple_chemical

| text_joined   |   n |
|:--------------|----:|
| lps           |  35 |
| glucose       |  21 |
| rapamycin     |  21 |
| tyrosine      |  12 |
| serine        |  12 |

## VALIDATION

- Documents: **90**
- Entity mentions: **2734** across **90** documents

### Entity counts by type

| type                 |   n_mentions |
|:---------------------|-------------:|
| Cellular_component   |          203 |
| Complex              |          244 |
| Gene_or_gene_product |         1836 |
| Simple_chemical      |          451 |

### Entities per document

|       |    0 |
|:------|-----:|
| count | 90   |
| mean  | 30.4 |
| min   |  9   |
| 50%   | 30   |
| max   | 67   |

### Span length (chars)

|       |   span_length |
|:------|--------------:|
| count |        2734   |
| mean  |           7.6 |
| min   |           1   |
| 50%   |           5   |
| max   |          64   |

### Normalization: 0 / 2734 (0.0%)

### Top 5 mentions per entity type (case-insensitive)

#### Cellular_component

| text_joined   |   n |
|:--------------|----:|
| nuclear       |  22 |
| chromatin     |  14 |
| spindle       |  11 |
| chromosomal   |  11 |
| cytoplasmic   |  10 |

#### Complex

| text_joined   |   n |
|:--------------|----:|
| nf-kappab     |  75 |
| ikk           |  11 |
| nf-kappa b    |  11 |
| swi/snf       |  11 |
| dna-pk        |   9 |

#### Gene_or_gene_product

| text_joined   |   n |
|:--------------|----:|
| p53           |  98 |
| mdm2          |  49 |
| beta-catenin  |  30 |
| e2f1          |  28 |
| e2f           |  27 |

#### Simple_chemical

| text_joined   |   n |
|:--------------|----:|
| tyrosine      |  18 |
| lps           |  12 |
| rapamycin     |  11 |
| dhpg          |   8 |
| heme          |   8 |

## TEST

- Documents: **175**
- Entity mentions: **5312** across **175** documents

### Entity counts by type

| type                 |   n_mentions |
|:---------------------|-------------:|
| Cellular_component   |          332 |
| Complex              |          529 |
| Gene_or_gene_product |         3587 |
| Simple_chemical      |          864 |

### Entities per document

|       |     0 |
|:------|------:|
| count | 175   |
| mean  |  30.4 |
| min   |   6   |
| 50%   |  29   |
| max   |  72   |

### Span length (chars)

|       |   span_length |
|:------|--------------:|
| count |        5312   |
| mean  |           7.9 |
| min   |           1   |
| 50%   |           5   |
| max   |          70   |

### Normalization: 0 / 5312 (0.0%)

### Top 5 mentions per entity type (case-insensitive)

#### Cellular_component

| text_joined   |   n |
|:--------------|----:|
| nuclear       |  58 |
| nucleus       |  25 |
| chromatin     |  22 |
| cytoplasmic   |  16 |
| mitochondrial |  14 |

#### Complex

| text_joined   |   n |
|:--------------|----:|
| nf-kappab     | 138 |
| nf-kappa b    |  37 |
| mtorc1        |  31 |
| ikk           |  28 |
| nfkappab      |  11 |

#### Gene_or_gene_product

| text_joined   |   n |
|:--------------|----:|
| p53           | 111 |
| e2f           |  46 |
| p65           |  45 |
| p73           |  41 |
| wnt           |  34 |

#### Simple_chemical

| text_joined        |   n |
|:-------------------|----:|
| lps                |  42 |
| biotin             |  16 |
| lipopolysaccharide |  15 |
| camp               |  15 |
| na+                |  13 |
