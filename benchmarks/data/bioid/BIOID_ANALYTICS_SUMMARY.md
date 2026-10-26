# BioID analytics

## BIOID

- Figure-panel captions: **13697** from **570** articles (document_id = PMC article)
- Entity mentions: **102717** across **13573** captions (124 captions have no annotations)

### Entity counts by type

| type        |   n_mentions |   n_normalized |
|:------------|-------------:|---------------:|
| anatomy     |         5774 |           5774 |
| assay       |           23 |             23 |
| cell        |         4868 |           4560 |
| cellline    |         5783 |           5783 |
| chemical    |        10517 |          10517 |
| gene        |        22844 |          20875 |
| molecule    |          761 |              0 |
| organism    |           25 |              0 |
| protein     |        35983 |          23725 |
| rna         |          156 |            156 |
| species     |         7949 |           7949 |
| subcellular |         7486 |           7259 |
| tissue      |          548 |              0 |

### Entities per caption

|       |       0 |
|:------|--------:|
| count | 13573   |
| mean  |     7.6 |
| min   |     1   |
| 50%   |     6   |
| max   |    73   |

### Captions per article

|       |   0 |
|:------|----:|
| count | 570 |
| mean  |  24 |
| min   |   1 |
| 50%   |  24 |
| max   |  64 |

### Span length (chars)

|       |   span_length |
|:------|--------------:|
| count |      102717   |
| mean  |           5.5 |
| min   |           1   |
| 50%   |           4   |
| max   |          52   |

### Normalization: 86621 / 102717 (84.3%)

| db_name     |   n_ids |
|:------------|--------:|
| BAO         |      23 |
| CHEBI       |    9867 |
| CL          |    4635 |
| Cellosaurus |    5783 |
| Corum       |      24 |
| GO          |    7308 |
| NCBI gene   |   21764 |
| NCBI taxon  |    7952 |
| PubChem     |     694 |
| Rfam        |     167 |
| Uberon      |    5867 |
| Uniprot     |   30210 |

### Top 5 mentions per entity type (case-insensitive)

#### anatomy

| text_joined   |   n |
|:--------------|----:|
| liver         | 330 |
| brain         | 221 |
| lung          | 182 |
| serum         | 122 |
| muscle        |  86 |

#### assay

| text_joined   |   n |
|:--------------|----:|
| ihc           |  10 |
| dic           |   8 |
| em            |   3 |
| tem           |   2 |

#### cell

| text_joined   |   n |
|:--------------|----:|
| neurons       | 261 |
| fibroblasts   | 167 |
| macrophages   | 146 |
| t cells       | 130 |
| bmdms         | 100 |

#### cellline

| text_joined   |    n |
|:--------------|-----:|
| hela          | 1045 |
| mefs          |  598 |
| u2os          |  236 |
| hek293t       |  213 |
| hek293        |  185 |

#### chemical

| text_joined   |   n |
|:--------------|----:|
| dna           | 301 |
| dmso          | 297 |
| rapamycin     | 187 |
| h2o2          | 183 |
| glucose       | 174 |

#### gene

| text_joined   |   n |
|:--------------|----:|
| atg5          | 262 |
| tau           | 224 |
| cre           | 214 |
| p53           | 191 |
| lc3           | 181 |

#### molecule

| text_joined   |   n |
|:--------------|----:|
| gold          |  41 |
| 24f4a         |  32 |
| cy            |  23 |
| idu           |  22 |
| gst           |  21 |

#### organism

| text_joined    |   n |
|:---------------|----:|
| col‐0          |  10 |
| mice           |   4 |
| adenoviruses   |   2 |
| n. benthamiana |   2 |
| female         |   1 |

#### protein

| text_joined   |    n |
|:--------------|-----:|
| gfp           | 3775 |
| lc3           | 1578 |
| flag          | 1197 |
| ha            | 1059 |
| myc           |  584 |

#### rna

| text_joined   |   n |
|:--------------|----:|
| u2            |  44 |
| mir-155       |  30 |
| let-7         |  14 |
| hhr           |  11 |
| mir-24        |   9 |

#### species

| text_joined   |    n |
|:--------------|-----:|
| mice          | 3020 |
| mouse         |  416 |
| human         |  253 |
| embryos       |  181 |
| hcv           |  169 |

#### subcellular

| text_joined   |   n |
|:--------------|----:|
| mitochondria  | 503 |
| nuclei        | 348 |
| mitochondrial | 298 |
| nuclear       | 238 |
| er            | 193 |

#### tissue

| text_joined   |   n |
|:--------------|----:|
| tumor         | 143 |
| tumors        | 113 |
| metastases    |  28 |
| leaves        |  26 |
| root          |  24 |
