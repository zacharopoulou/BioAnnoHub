# miRNA analytics

## TRAIN

- Documents: **201**
- Entity mentions: **4500** across **201** documents

### Entity counts by type

| type                |   n_mentions |
|:--------------------|-------------:|
| Diseases            |         1521 |
| Genes/Proteins      |          734 |
| Non-Specific_miRNAs |         1170 |
| Species             |          546 |
| Specific_miRNAs     |          529 |

### Entities per document

|       |     0 |
|:------|------:|
| count | 201   |
| mean  |  22.4 |
| min   |   2   |
| 50%   |  21   |
| max   |  56   |

### Span length (chars)

|       |   span_length |
|:------|--------------:|
| count |        4500   |
| mean  |           8.8 |
| min   |           2   |
| 50%   |           6   |
| max   |          90   |

### Normalization: 0 / 4500 (0.0%)

### Top 5 mentions per entity type (case-insensitive)

#### Diseases

| text_joined         |   n |
|:--------------------|----:|
| ad                  | 109 |
| cancer              |  55 |
| alzheimer's disease |  48 |
| tumor               |  46 |
| glioma              |  34 |

#### Genes/Proteins

| text_joined   |   n |
|:--------------|----:|
| bace1         |  34 |
| app           |  33 |
| ifn-beta      |  21 |
| rest          |  18 |
| p53           |  15 |

#### Non-Specific_miRNAs

| text_joined   |   n |
|:--------------|----:|
| mirnas        | 500 |
| mirna         | 375 |
| micrornas     | 159 |
| microrna      | 115 |
| mirs          |   7 |

#### Species

| text_joined   |   n |
|:--------------|----:|
| human         | 167 |
| patients      | 158 |
| mouse         |  35 |
| mice          |  34 |
| patient       |  27 |

#### Specific_miRNAs

| text_joined   |   n |
|:--------------|----:|
| mir-21        |  41 |
| mirna-146a    |  24 |
| mir-107       |  17 |
| let-7         |  15 |
| mir-124       |  13 |

## TEST

- Documents: **100**
- Entity mentions: **1858** across **100** documents

### Entity counts by type

| type                |   n_mentions |
|:--------------------|-------------:|
| Diseases            |          640 |
| Genes/Proteins      |          324 |
| Non-Specific_miRNAs |          336 |
| Species             |          182 |
| Specific_miRNAs     |          376 |

### Entities per document

|       |     0 |
|:------|------:|
| count | 100   |
| mean  |  18.6 |
| min   |   1   |
| 50%   |  19   |
| max   |  42   |

### Span length (chars)

|       |   span_length |
|:------|--------------:|
| count |        1858   |
| mean  |           9.2 |
| min   |           2   |
| 50%   |           7   |
| max   |          83   |

### Normalization: 0 / 1858 (0.0%)

### Top 5 mentions per entity type (case-insensitive)

#### Diseases

| text_joined   |   n |
|:--------------|----:|
| glioblastoma  |  61 |
| stroke        |  34 |
| glioma        |  33 |
| tumor         |  29 |
| cancer        |  28 |

#### Genes/Proteins

| text_joined     |   n |
|:----------------|----:|
| grn             |  21 |
| myocardin       |  15 |
| alpha-synuclein |  12 |
| xiap            |  12 |
| tau             |  11 |

#### Non-Specific_miRNAs

| text_joined   |   n |
|:--------------|----:|
| micrornas     |  99 |
| mirna         |  75 |
| mirnas        |  70 |
| microrna      |  68 |
| mirs          |   8 |

#### Species

| text_joined   |   n |
|:--------------|----:|
| human         |  49 |
| patients      |  47 |
| mice          |  30 |
| mouse         |  17 |
| rat           |  12 |

#### Specific_miRNAs

| text_joined   |   n |
|:--------------|----:|
| mir-21        |  45 |
| mir-210       |  17 |
| mir-145       |  15 |
| let-7         |  13 |
| mir-29b       |  13 |
