# BioNLP11ID analytics

## TRAIN

- Documents: **152**
- Entity mentions: **6553** across **151** documents

### Entity counts by type

| type                 |   n_mentions |
|:---------------------|-------------:|
| Chemical             |          596 |
| Entity               |           28 |
| Organism             |         2184 |
| Protein              |         3405 |
| Regulon-operon       |           72 |
| Two-component-system |          268 |

### Entities per document

|       |     0 |
|:------|------:|
| count | 151   |
| mean  |  43.4 |
| min   |   1   |
| 50%   |  34   |
| max   | 164   |

### Span length (chars)

|       |   span_length |
|:------|--------------:|
| count |        6553   |
| mean  |           7.3 |
| min   |           1   |
| 50%   |           5   |
| max   |          53   |

### Normalization: 0 / 6553 (0.0%)

### Top 5 mentions per entity type (case-insensitive)

#### Chemical

| text_joined   |   n |
|:--------------|----:|
| atp           |  77 |
| mg2+          |  33 |
| lps           |  22 |
| iron          |  20 |
| magnesium     |  15 |

#### Entity

| text_joined             |   n |
|:------------------------|----:|
| promoter region         |  12 |
| promoter                |   4 |
| p                       |   3 |
| atpase domain           |   1 |
| intergenic region (igr) |   1 |

#### Organism

| text_joined       |   n |
|:------------------|----:|
| y. enterocolitica | 136 |
| p. luminescens    | 134 |
| flea              | 101 |
| y. pestis         |  93 |
| p. aeruginosa     |  87 |

#### Protein

| text_joined   |   n |
|:--------------|----:|
| rv2623        | 148 |
| phop          | 117 |
| srca          |  97 |
| ssrb          |  71 |
| semac         |  71 |

#### Regulon-operon

| text_joined   |   n |
|:--------------|----:|
| pa3552-pa3559 |  14 |
| spy0127-0130  |   6 |
| dlt           |   3 |
| stm3117-3120  |   2 |
| eutabc        |   2 |

#### Two-component-system

| text_joined   |   n |
|:--------------|----:|
| bvrr/bvrs     |  35 |
| grars         |  34 |
| phopq         |  16 |
| ssra/ssrb     |  15 |
| vicrk         |  14 |

## VALIDATION

- Documents: **46**
- Entity mentions: **1996** across **46** documents

### Entity counts by type

| type                 |   n_mentions |
|:---------------------|-------------:|
| Chemical             |          131 |
| Entity               |           20 |
| Organism             |          521 |
| Protein              |         1156 |
| Regulon-operon       |           49 |
| Two-component-system |          119 |

### Entities per document

|       |     0 |
|:------|------:|
| count |  46   |
| mean  |  43.4 |
| min   |   2   |
| 50%   |  40.5 |
| max   | 166   |

### Span length (chars)

|       |   span_length |
|:------|--------------:|
| count |        1996   |
| mean  |           6.2 |
| min   |           1   |
| 50%   |           4   |
| max   |          50   |

### Normalization: 0 / 1996 (0.0%)

### Top 5 mentions per entity type (case-insensitive)

#### Chemical

| text_joined   |   n |
|:--------------|----:|
| glucose       |  20 |
| mg2+          |  13 |
| fe3+          |  11 |
| polymyxin b   |  10 |
| mannose       |   8 |

#### Entity

| text_joined         |   n |
|:--------------------|----:|
| p3 promoter         |   6 |
| promoter            |   4 |
| upstream            |   3 |
| promoters           |   3 |
| 190-270-bp upstream |   1 |

#### Organism

| text_joined   |   n |
|:--------------|----:|
| salmonella    |  52 |
| ss2           |  36 |
| deltasalkr    |  33 |
| p. aeruginosa |  32 |
| tb            |  29 |

#### Protein

| text_joined   |   n |
|:--------------|----:|
| salk          | 106 |
| mlc           |  93 |
| hile          |  77 |
| r             |  74 |
| cheb2         |  64 |

#### Regulon-operon

| text_joined   |   n |
|:--------------|----:|
| sigmae        |  17 |
| invfa         |   5 |
| invfd         |   4 |
| pho           |   2 |
| mlc           |   2 |

#### Two-component-system

| text_joined   |   n |
|:--------------|----:|
| salkr         |  71 |
| salk/salr     |  24 |
| ssrab         |   7 |
| pmra/pmrb     |   3 |
| hilc/d        |   2 |

## TEST

- Documents: **118**
- Entity mentions: **4239** across **117** documents

### Entity counts by type

| type                 |   n_mentions |
|:---------------------|-------------:|
| Chemical             |          248 |
| Organism             |         1388 |
| Protein              |         2396 |
| Regulon-operon       |          102 |
| Two-component-system |          105 |

### Entities per document

|       |     0 |
|:------|------:|
| count | 117   |
| mean  |  36.2 |
| min   |   2   |
| 50%   |  31   |
| max   | 142   |

### Span length (chars)

|       |   span_length |
|:------|--------------:|
| count |        4239   |
| mean  |           6.9 |
| min   |           1   |
| 50%   |           4   |
| max   |          50   |

### Normalization: 0 / 4239 (0.0%)

### Top 5 mentions per entity type (case-insensitive)

#### Chemical

| text_joined   |   n |
|:--------------|----:|
| lps           |  32 |
| opg           |  20 |
| c-di-gmp      |  19 |
| iron          |  16 |
| myo-inositol  |  11 |

#### Organism

| text_joined    |   n |
|:---------------|----:|
| og1rf          | 100 |
| p. entomophila |  88 |
| p. temperata   |  59 |
| v583           |  59 |
| salmonella     |  56 |

#### Protein

| text_joined   |   n |
|:--------------|----:|
| hfq           | 148 |
| ssrb          | 110 |
| speb          |  92 |
| apra          |  79 |
| ropb          |  74 |

#### Regulon-operon

| text_joined           |   n |
|:----------------------|----:|
| flhdc                 |  13 |
| iol                   |  12 |
| speb operon           |   8 |
| sls operon            |   3 |
| streptolysin s operon |   3 |

#### Two-component-system

| text_joined   |   n |
|:--------------|----:|
| covr/s        |  17 |
| covrs         |  15 |
| sak188/sak189 |  15 |
| gacs/gaca     |   9 |
| ssra-ssrb     |   8 |
