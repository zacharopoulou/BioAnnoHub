# CellFinder analytics

## TRAIN

- Documents: **5**
- Entity mentions: **2713** across **5** documents

### Entity counts by type

| type          |   n_mentions |
|:--------------|-------------:|
| Anatomy       |          423 |
| CellComponent |          131 |
| CellLine      |           96 |
| CellType      |          824 |
| GeneProtein   |         1010 |
| Species       |          229 |

### Entities per document

|       |     0 |
|:------|------:|
| count |   5   |
| mean  | 542.6 |
| min   | 220   |
| 50%   | 552   |
| max   | 849   |

### Span length (chars)

|       |   span_length |
|:------|--------------:|
| count |        2713   |
| mean  |           8.1 |
| min   |           2   |
| 50%   |           6   |
| max   |          44   |

### Normalization: 0 / 2713 (0.0%)

### Top 5 mentions per entity type (case-insensitive)

#### Anatomy

| text_joined   |   n |
|:--------------|----:|
| myofiber      |  51 |
| myogenic      |  46 |
| embryonic     |  35 |
| neural        |  20 |
| skeletal      |  16 |

#### CellComponent

| text_joined    |   n |
|:---------------|----:|
| dna            |  26 |
| nuclei         |  23 |
| nuclear        |   8 |
| multinucleated |   6 |
| chromatin      |   5 |

#### CellLine

| text_joined   |   n |
|:--------------|----:|
| sd56          |  26 |
| bg01          |  14 |
| k562          |  14 |
| ntera-2       |   7 |
| bg03          |   6 |

#### CellType

| text_joined     |   n |
|:----------------|----:|
| hescs           | 183 |
| hnscs           |  71 |
| satellite cells |  47 |
| stem cells      |  38 |
| myofibers       |  33 |

#### GeneProtein

| text_joined   |   n |
|:--------------|----:|
| oct4          |  48 |
| desmin        |  33 |
| dnasei        |  23 |
| nanog         |  20 |
| tal1          |  20 |

#### Species

| text_joined   |   n |
|:--------------|----:|
| mouse         | 101 |
| human         |  66 |
| rats          |  14 |
| mice          |  14 |
| goat          |   4 |

## TEST

- Documents: **5**
- Entity mentions: **3185** across **5** documents

### Entity counts by type

| type          |   n_mentions |
|:--------------|-------------:|
| Anatomy       |          529 |
| CellComponent |           72 |
| CellLine      |          344 |
| CellType      |         1248 |
| GeneProtein   |          740 |
| Species       |          252 |

### Entities per document

|       |   0 |
|:------|----:|
| count |   5 |
| mean  | 637 |
| min   | 445 |
| 50%   | 496 |
| max   | 905 |

### Span length (chars)

|       |   span_length |
|:------|--------------:|
| count |        3185   |
| mean  |           8.5 |
| min   |           1   |
| 50%   |           6   |
| max   |          59   |

### Normalization: 0 / 3185 (0.0%)

### Top 5 mentions per entity type (case-insensitive)

#### Anatomy

| text_joined   |   n |
|:--------------|----:|
| embryonic     |  32 |
| fetal         |  30 |
| neuronal      |  29 |
| ebs           |  26 |
| liver         |  24 |

#### CellComponent

| text_joined          |   n |
|:---------------------|----:|
| rna                  |  29 |
| dna                  |   6 |
| cdna                 |   5 |
| nuclei               |   3 |
| extracellular matrix |   3 |

#### CellLine

| text_joined   |   n |
|:--------------|----:|
| hues6         |  42 |
| cyt-es        |  41 |
| hues6-es      |  27 |
| ntera2        |  20 |
| bg01          |  20 |

#### CellType

| text_joined   |   n |
|:--------------|----:|
| hescs         | 167 |
| macrophages   | 116 |
| hcns-sc       |  87 |
| hcns-scns     |  78 |
| nps           |  70 |

#### GeneProtein

| text_joined   |   n |
|:--------------|----:|
| cd34          |  91 |
| nanog         |  23 |
| nestin        |  18 |
| sox1          |  15 |
| slk           |  14 |

#### Species

| text_joined   |   n |
|:--------------|----:|
| human         | 125 |
| mouse         |  28 |
| hiv-1         |  20 |
| lentiviral    |  14 |
| hiv           |  13 |
