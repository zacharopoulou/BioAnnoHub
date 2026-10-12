# RaTE-NER analytics

## TRAIN

- Documents: **30005**
- Entity mentions: **84218** across **15579** documents

### Entity counts by type

| type            |   n_mentions |
|:----------------|-------------:|
| Abnormality     |        33677 |
| Anatomy         |        34409 |
| Disease         |         9629 |
| Non-Abnormality |         4036 |
| Non-Disease     |         2467 |

### Entities per document

|       |       0 |
|:------|--------:|
| count | 15579   |
| mean  |     5.4 |
| min   |     1   |
| 50%   |     4   |
| max   |    44   |

### Span length (chars)

|       |   span_length |
|:------|--------------:|
| count |       84218   |
| mean  |          23.2 |
| min   |           1   |
| 50%   |          19   |
| max   |         373   |

### Normalization: 0 / 84218 (0.0%)

### Top 5 mentions per entity type (case-insensitive)

#### Abnormality

| text_joined   |   n |
|:--------------|----:|
| enlarged      | 293 |
| normal        | 225 |
| dilated       | 223 |
| large         | 168 |
| small         | 144 |

#### Anatomy

| text_joined   |   n |
|:--------------|----:|
| mass          | 566 |
| liver         | 384 |
| lungs         | 354 |
| uterus        | 222 |
| left kidney   | 206 |

#### Disease

| text_joined         |   n |
|:--------------------|----:|
| mild joint effusion |  35 |
| joint effusion      |  26 |
| cirrhosis           |  25 |
| midline shift       |  22 |
| mass effect         |  22 |

#### Non-Abnormality

| text_joined   |   n |
|:--------------|----:|
| normal        | 407 |
| clear         | 286 |
| intact        | 141 |
| unremarkable  | 131 |
| size normal   |  41 |

#### Non-Disease

| text_joined       |   n |
|:------------------|----:|
| pleural effusion  |  96 |
| pneumothorax      |  73 |
| hydrocephalus     |  46 |
| fracture          |  29 |
| heart size normal |  27 |

## VALIDATION

- Documents: **3600**
- Entity mentions: **10025** across **1853** documents

### Entity counts by type

| type            |   n_mentions |
|:----------------|-------------:|
| Abnormality     |         4006 |
| Anatomy         |         4145 |
| Disease         |         1118 |
| Non-Abnormality |          488 |
| Non-Disease     |          268 |

### Entities per document

|       |      0 |
|:------|-------:|
| count | 1853   |
| mean  |    5.4 |
| min   |    1   |
| 50%   |    4   |
| max   |   27   |

### Span length (chars)

|       |   span_length |
|:------|--------------:|
| count |       10025   |
| mean  |          23.4 |
| min   |           1   |
| 50%   |          19   |
| max   |         231   |

### Normalization: 0 / 10025 (0.0%)

### Top 5 mentions per entity type (case-insensitive)

#### Abnormality

| text_joined   |   n |
|:--------------|----:|
| enlarged      |  35 |
| dilated       |  32 |
| normal        |  24 |
| small         |  14 |
| collapsed     |  13 |

#### Anatomy

| text_joined   |   n |
|:--------------|----:|
| mass          |  66 |
| lungs         |  48 |
| liver         |  38 |
| left kidney   |  27 |
| kidneys       |  25 |

#### Disease

| text_joined                   |   n |
|:------------------------------|----:|
| mass effect                   |   5 |
| subfalcine herniation         |   5 |
| cirrhosis                     |   5 |
| midline shift                 |   4 |
| small vessel ischemic changes |   3 |

#### Non-Abnormality

| text_joined   |   n |
|:--------------|----:|
| normal        |  43 |
| clear         |  40 |
| intact        |  15 |
| unremarkable  |   9 |
| size normal   |   7 |

#### Non-Disease

| text_joined       |   n |
|:------------------|----:|
| pleural effusion  |  13 |
| pneumothorax      |  10 |
| hydrocephalus     |   6 |
| fracture          |   5 |
| heart size normal |   4 |

## TEST

- Documents: **3529**
- Entity mentions: **10265** across **1833** documents

### Entity counts by type

| type            |   n_mentions |
|:----------------|-------------:|
| Abnormality     |         4265 |
| Anatomy         |         4471 |
| Disease         |          741 |
| Non-Abnormality |          605 |
| Non-Disease     |          183 |

### Entities per document

|       |      0 |
|:------|-------:|
| count | 1833   |
| mean  |    5.6 |
| min   |    1   |
| 50%   |    5   |
| max   |   29   |

### Span length (chars)

|       |   span_length |
|:------|--------------:|
| count |       10265   |
| mean  |          20.6 |
| min   |           2   |
| 50%   |          18   |
| max   |         154   |

### Normalization: 0 / 10265 (0.0%)

### Top 5 mentions per entity type (case-insensitive)

#### Abnormality

| text_joined   |   n |
|:--------------|----:|
| enlarged      |  42 |
| normal        |  42 |
| fracture      |  36 |
| thickening    |  28 |
| dilated       |  25 |

#### Anatomy

| text_joined   |   n |
|:--------------|----:|
| lungs         |  41 |
| mass          |  36 |
| liver         |  32 |
| spleen        |  31 |
| uterus        |  22 |

#### Disease

| text_joined       |   n |
|:------------------|----:|
| hydrocephalus     |   8 |
| pneumothorax      |   5 |
| pneumomediastinum |   5 |
| mass effect       |   4 |
| acute infarction  |   4 |

#### Non-Abnormality

| text_joined   |   n |
|:--------------|----:|
| normal        |  54 |
| clear         |  45 |
| intact        |  16 |
| preserved     |   8 |
| effusion      |   8 |

#### Non-Disease

| text_joined      |   n |
|:-----------------|----:|
| pneumothorax     |   8 |
| fracture         |   8 |
| hydrocephalus    |   7 |
| lymphadenopathy  |   7 |
| pneumoperitoneum |   5 |
