# NLM-Chem analytics

## TRAIN

- Documents: **80** (full-text articles)
- Passages: **5555**
- Entity mentions: **21218** across **80** documents

### Document length (chars)

|       |   char_length |
|:------|--------------:|
| count |          80   |
| mean  |       33574.8 |
| min   |        5032   |
| 50%   |       32301.5 |
| max   |       71842   |

### Passages per document

|       |     0 |
|:------|------:|
| count |  80   |
| mean  |  69.4 |
| min   |  23   |
| 50%   |  66   |
| max   | 150   |

### Top 10 passage types

| type             |   n_passages |
|:-----------------|-------------:|
| paragraph        |         2758 |
| title_2          |          834 |
| fig_caption      |          461 |
| title_1          |          428 |
| footnote         |          179 |
| abstract         |          161 |
| title            |          109 |
| table_footnote   |          108 |
| table_caption    |           98 |
| abstract_title_1 |           90 |

### Entity counts by type

| type     |   n_mentions |
|:---------|-------------:|
| Chemical |        21218 |

### Entities per document

|       |     0 |
|:------|------:|
| count |  80   |
| mean  | 265.2 |
| min   |  19   |
| 50%   | 234.5 |
| max   | 673   |

### Span length (chars)

|       |   span_length |
|:------|--------------:|
| count |       21218   |
| mean  |           7.5 |
| min   |           1   |
| 50%   |           5   |
| max   |         135   |

### Normalization: 21044 / 21218 (99.2%)

- Mentions with more than one ID: **1503**

| db_name   |   n_ids |
|:----------|--------:|
| MESH      |   23295 |

### Top 5 mentions per entity type (case-insensitive)

#### Chemical

| text_joined   |   n |
|:--------------|----:|
| bh4           | 293 |
| water         | 260 |
| ca2+          | 256 |
| nahs          | 227 |
| hydrogen      | 200 |

## VALIDATION

- Documents: **20** (full-text articles)
- Passages: **1285**
- Entity mentions: **5349** across **20** documents

### Document length (chars)

|       |   char_length |
|:------|--------------:|
| count |          20   |
| mean  |       33070.4 |
| min   |        5244   |
| 50%   |       33605.5 |
| max   |       44885   |

### Passages per document

|       |    0 |
|:------|-----:|
| count | 20   |
| mean  | 64.2 |
| min   | 46   |
| 50%   | 64.5 |
| max   | 81   |

### Top 10 passage types

| type             |   n_passages |
|:-----------------|-------------:|
| paragraph        |          641 |
| title_2          |          226 |
| fig_caption      |          121 |
| title_1          |          111 |
| abstract         |           36 |
| title            |           29 |
| front            |           20 |
| abstract_title_1 |           18 |
| footnote         |           16 |
| title_3          |           14 |

### Entity counts by type

| type     |   n_mentions |
|:---------|-------------:|
| Chemical |         5349 |

### Entities per document

|       |     0 |
|:------|------:|
| count |  20   |
| mean  | 267.4 |
| min   |   6   |
| 50%   | 249   |
| max   | 676   |

### Span length (chars)

|       |   span_length |
|:------|--------------:|
| count |        5349   |
| mean  |           7.2 |
| min   |           1   |
| 50%   |           6   |
| max   |         123   |

### Normalization: 5295 / 5349 (99.0%)

- Mentions with more than one ID: **350**

| db_name   |   n_ids |
|:----------|--------:|
| MESH      |    5794 |

### Top 5 mentions per entity type (case-insensitive)

#### Chemical

| text_joined   |   n |
|:--------------|----:|
| no            | 356 |
| cys           | 211 |
| ptx           | 163 |
| ropivacaine   | 131 |
| hocl          | 129 |

## TEST

- Documents: **50** (full-text articles)
- Passages: **3470**
- Entity mentions: **11772** across **50** documents

### Document length (chars)

|       |   char_length |
|:------|--------------:|
| count |          50   |
| mean  |       30273.6 |
| min   |       11940   |
| 50%   |       27715   |
| max   |       64337   |

### Passages per document

|       |     0 |
|:------|------:|
| count |  50   |
| mean  |  69.4 |
| min   |  35   |
| 50%   |  62   |
| max   | 141   |

### Top 10 passage types

| type             |   n_passages |
|:-----------------|-------------:|
| paragraph        |         1737 |
| title_2          |          489 |
| title_1          |          282 |
| fig_caption      |          238 |
| abstract         |          109 |
| table_caption    |           78 |
| footnote         |           76 |
| title_3          |           70 |
| abstract_title_1 |           69 |
| table_footnote   |           58 |

### Entity counts by type

| type     |   n_mentions |
|:---------|-------------:|
| Chemical |        11772 |

### Entities per document

|       |     0 |
|:------|------:|
| count |  50   |
| mean  | 235.4 |
| min   |   2   |
| 50%   | 242.5 |
| max   | 682   |

### Span length (chars)

|       |   span_length |
|:------|--------------:|
| count |       11772   |
| mean  |           7.8 |
| min   |           1   |
| 50%   |           6   |
| max   |         162   |

### Normalization: 11660 / 11772 (99.0%)

- Mentions with more than one ID: **458**

| db_name   |   n_ids |
|:----------|--------:|
| MESH      |   12211 |

### Top 5 mentions per entity type (case-insensitive)

#### Chemical

| text_joined   |   n |
|:--------------|----:|
| paclitaxel    | 224 |
| salt          | 192 |
| fisetin       | 156 |
| gemcitabine   | 138 |
| dha           | 134 |
