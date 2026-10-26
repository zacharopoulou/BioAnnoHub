# MLEE analytics

## TRAIN

- Documents: **131**
- Entity mentions: **4147** across **130** documents

### Entity counts by type

| type                            |   n_mentions |
|:--------------------------------|-------------:|
| Anatomical_system               |            9 |
| Cell                            |          714 |
| Cellular_component              |           77 |
| DNA_domain_or_region            |           31 |
| Developing_anatomical_structure |            3 |
| Drug_or_compound                |          435 |
| Gene_or_gene_product            |         1461 |
| Immaterial_anatomical_entity    |            8 |
| Multi-tissue_structure          |          259 |
| Organ                           |           82 |
| Organism                        |          359 |
| Organism_subdivision            |           20 |
| Organism_substance              |           56 |
| Pathological_formation          |          382 |
| Protein_domain_or_region        |           17 |
| Tissue                          |          234 |

### Entities per document

|       |     0 |
|:------|------:|
| count | 130   |
| mean  |  31.9 |
| min   |   4   |
| 50%   |  31   |
| max   |  77   |

### Span length (chars)

|       |   span_length |
|:------|--------------:|
| count |        4147   |
| mean  |          10.2 |
| min   |           1   |
| 50%   |           7   |
| max   |          93   |

### Normalization: 0 / 4147 (0.0%)

### Top 5 mentions per entity type (case-insensitive)

#### Anatomical_system

| text_joined            |   n |
|:-----------------------|----:|
| central nervous system |   4 |
| cns                    |   2 |
| vasculature            |   2 |
| cardiovascular         |   1 |

#### Cell

| text_joined       |   n |
|:------------------|----:|
| cell              |  75 |
| endothelial cell  |  52 |
| endothelial cells |  51 |
| ec                |  34 |
| cells             |  31 |

#### Cellular_component

| text_joined          |   n |
|:---------------------|----:|
| extracellular matrix |  14 |
| matrix               |   5 |
| basement membrane    |   5 |
| filopodia            |   4 |
| focal adhesions      |   3 |

#### DNA_domain_or_region

| text_joined                            |   n |
|:---------------------------------------|----:|
| promoter                               |  20 |
| hre                                    |   5 |
| hypoxia-responsive element             |   1 |
| hypoxia-responsive elements            |   1 |
| negative shear stress response element |   1 |

#### Developing_anatomical_structure

| text_joined   |   n |
|:--------------|----:|
| embryos       |   2 |
| seed          |   1 |

#### Drug_or_compound

| text_joined   |   n |
|:--------------|----:|
| thalidomide   |  15 |
| ethanol       |  15 |
| 20-hete       |  13 |
| bevacizumab   |  10 |
| epox          |  10 |

#### Gene_or_gene_product

| text_joined                        |   n |
|:-----------------------------------|----:|
| vegf                               | 186 |
| vascular endothelial growth factor |  49 |
| p53                                |  18 |
| thrombin                           |  16 |
| igf-1                              |  15 |

#### Immaterial_anatomical_entity

| text_joined               |   n |
|:--------------------------|----:|
| lumen                     |   3 |
| perivascular              |   2 |
| extracellular compartment |   1 |
| peritoneal surface area   |   1 |
| vessel lumen              |   1 |

#### Multi-tissue_structure

| text_joined   |   n |
|:--------------|----:|
| blood vessels |  27 |
| vascular      |  24 |
| vessel        |  15 |
| blood vessel  |  13 |
| vessels       |   9 |

#### Organ

| text_joined   |   n |
|:--------------|----:|
| skin          |   9 |
| heart         |   9 |
| eye           |   7 |
| ear           |   4 |
| mandible      |   4 |

#### Organism

| text_joined   |   n |
|:--------------|----:|
| human         |  77 |
| patients      |  75 |
| mice          |  31 |
| rat           |  14 |
| mouse         |  11 |

#### Organism_subdivision

| text_joined   |   n |
|:--------------|----:|
| hind limb     |   3 |
| breast        |   2 |
| limb          |   2 |
| hindlimb      |   2 |
| lower limb    |   2 |

#### Organism_substance

| text_joined   |   n |
|:--------------|----:|
| serum         |  18 |
| blood         |  15 |
| aqueous humor |   5 |
| juice         |   4 |
| granules      |   2 |

#### Pathological_formation

| text_joined       |   n |
|:------------------|----:|
| tumor             | 126 |
| cancer            |  30 |
| tumors            |  29 |
| ccms              |  12 |
| colorectal cancer |  10 |

#### Protein_domain_or_region

| text_joined                    |   n |
|:-------------------------------|----:|
| d5                             |   8 |
| domain 5                       |   2 |
| fc fragment                    |   1 |
| t(163                          |   1 |
| c-terminal ca2+-binding region |   1 |

#### Tissue

| text_joined   |   n |
|:--------------|----:|
| tissue        |  16 |
| capillary     |  13 |
| tissues       |  13 |
| bone          |   9 |
| fat tissue    |   9 |

## VALIDATION

- Documents: **44**
- Entity mentions: **1431** across **44** documents

### Entity counts by type

| type                            |   n_mentions |
|:--------------------------------|-------------:|
| Anatomical_system               |            1 |
| Cell                            |          152 |
| Cellular_component              |           28 |
| DNA_domain_or_region            |            4 |
| Developing_anatomical_structure |            1 |
| Drug_or_compound                |          202 |
| Gene_or_gene_product            |          500 |
| Immaterial_anatomical_entity    |            3 |
| Multi-tissue_structure          |           89 |
| Organ                           |           41 |
| Organism                        |          126 |
| Organism_subdivision            |            7 |
| Organism_substance              |           26 |
| Pathological_formation          |          171 |
| Protein_domain_or_region        |           10 |
| Tissue                          |           70 |

### Entities per document

|       |    0 |
|:------|-----:|
| count | 44   |
| mean  | 32.5 |
| min   |  6   |
| 50%   | 30.5 |
| max   | 80   |

### Span length (chars)

|       |   span_length |
|:------|--------------:|
| count |        1431   |
| mean  |          10.3 |
| min   |           1   |
| 50%   |           8   |
| max   |          74   |

### Normalization: 0 / 1431 (0.0%)

### Top 5 mentions per entity type (case-insensitive)

#### Anatomical_system

| text_joined   |   n |
|:--------------|----:|
| vasculature   |   1 |

#### Cell

| text_joined                 |   n |
|:----------------------------|----:|
| endothelial cell            |  11 |
| cell                        |  11 |
| endothelial cells           |   9 |
| capillary endothelial cells |   5 |
| csc                         |   5 |

#### Cellular_component

| text_joined           |   n |
|:----------------------|----:|
| membrane              |   8 |
| matrix                |   4 |
| nascent focal complex |   3 |
| focal complex         |   3 |
| cell surface          |   2 |

#### DNA_domain_or_region

| text_joined   |   n |
|:--------------|----:|
| promoter      |   4 |

#### Developing_anatomical_structure

| text_joined        |   n |
|:-------------------|----:|
| transgenic embryos |   1 |

#### Drug_or_compound

| text_joined    |   n |
|:---------------|----:|
| verteporfin    |  14 |
| l-name         |  10 |
| spironolactone |  10 |
| fluorescein    |   9 |
| cediranib      |   9 |

#### Gene_or_gene_product

| text_joined                        |   n |
|:-----------------------------------|----:|
| vegf                               |  48 |
| endosialin                         |  14 |
| vascular endothelial growth factor |  14 |
| vegf-c                             |  12 |
| sflt-1                             |  11 |

#### Immaterial_anatomical_entity

| text_joined   |   n |
|:--------------|----:|
| marrow cavity |   1 |
| intracranial  |   1 |
| lumen         |   1 |

#### Multi-tissue_structure

| text_joined     |   n |
|:----------------|----:|
| vessels         |   6 |
| vascular        |   6 |
| conjunctival    |   6 |
| vessel          |   5 |
| vascular bundle |   4 |

#### Organ

| text_joined   |   n |
|:--------------|----:|
| eyes          |  11 |
| heart         |   5 |
| brain         |   5 |
| pulmonary     |   5 |
| bone          |   2 |

#### Organism

| text_joined   |   n |
|:--------------|----:|
| patients      |  44 |
| human         |  23 |
| mice          |  12 |
| rat           |   7 |
| patient       |   6 |

#### Organism_subdivision

| text_joined      |   n |
|:-----------------|----:|
| hindlimb         |   4 |
| limb             |   2 |
| gastrointestinal |   1 |

#### Organism_substance

| text_joined        |   n |
|:-------------------|----:|
| gse                |  11 |
| blood              |   5 |
| serum              |   4 |
| plasma             |   2 |
| grape seed extract |   2 |

#### Pathological_formation

| text_joined    |   n |
|:---------------|----:|
| tumor          |  43 |
| tumors         |  12 |
| tumour         |  12 |
| cancer         |   5 |
| ovarian cancer |   5 |

#### Protein_domain_or_region

| text_joined           |   n |
|:----------------------|----:|
| plasminogen kringle 1 |   2 |
| y951                  |   1 |
| y996                  |   1 |
| y1059                 |   1 |
| y1175                 |   1 |

#### Tissue

| text_joined   |   n |
|:--------------|----:|
| macular       |   6 |
| capillary     |   6 |
| microvessel   |   4 |
| tube          |   3 |
| endothelium   |   3 |

## TEST

- Documents: **87**
- Entity mentions: **2713** across **87** documents

### Entity counts by type

| type                            |   n_mentions |
|:--------------------------------|-------------:|
| Anatomical_system               |            8 |
| Cell                            |          332 |
| Cellular_component              |           40 |
| Developing_anatomical_structure |            2 |
| Drug_or_compound                |          307 |
| Gene_or_gene_product            |         1001 |
| Immaterial_anatomical_entity    |            4 |
| Multi-tissue_structure          |          166 |
| Organ                           |           53 |
| Organism                        |          237 |
| Organism_subdivision            |           22 |
| Organism_substance              |           60 |
| Pathological_formation          |          357 |
| Protein_domain_or_region        |            2 |
| Tissue                          |          122 |

### Entities per document

|       |    0 |
|:------|-----:|
| count | 87   |
| mean  | 31.2 |
| min   |  5   |
| 50%   | 30   |
| max   | 61   |

### Span length (chars)

|       |   span_length |
|:------|--------------:|
| count |          2713 |
| mean  |            10 |
| min   |             1 |
| 50%   |             7 |
| max   |           117 |

### Normalization: 0 / 2713 (0.0%)

### Top 5 mentions per entity type (case-insensitive)

#### Anatomical_system

| text_joined           |   n |
|:----------------------|----:|
| vasculature           |   4 |
| pulmonary system      |   1 |
| skeletal              |   1 |
| vascular network      |   1 |
| embryonic vasculature |   1 |

#### Cell

| text_joined       |   n |
|:------------------|----:|
| endothelial cell  |  41 |
| endothelial cells |  34 |
| cell              |  34 |
| cells             |  13 |
| pericyte          |   8 |

#### Cellular_component

| text_joined          |   n |
|:---------------------|----:|
| extracellular matrix |   9 |
| ve                   |   7 |
| ecm                  |   6 |
| microtubule          |   6 |
| matrix components    |   1 |

#### Developing_anatomical_structure

| text_joined   |   n |
|:--------------|----:|
| fetus         |   1 |
| fetuses       |   1 |

#### Drug_or_compound

| text_joined   |   n |
|:--------------|----:|
| heparin       |  20 |
| dmba          |  14 |
| plga          |  11 |
| no            |   8 |
| 317615 x 2hcl |   8 |

#### Gene_or_gene_product

| text_joined   |   n |
|:--------------|----:|
| vegf          |  70 |
| il-8          |  30 |
| bfgf          |  30 |
| tsp-1         |  20 |
| p53           |  20 |

#### Immaterial_anatomical_entity

| text_joined         |   n |
|:--------------------|----:|
| preperitoneal space |   2 |
| subretinal space    |   1 |
| subretinally        |   1 |

#### Multi-tissue_structure

| text_joined   |   n |
|:--------------|----:|
| vascular      |  26 |
| blood vessels |  15 |
| vasculature   |  11 |
| vessels       |   9 |
| vessel        |   7 |

#### Organ

| text_joined   |   n |
|:--------------|----:|
| bone          |  10 |
| lung          |   9 |
| placental     |   5 |
| brain         |   4 |
| placenta      |   3 |

#### Organism

| text_joined   |   n |
|:--------------|----:|
| patients      |  65 |
| human         |  39 |
| mice          |  25 |
| mouse         |  14 |
| patient       |   8 |

#### Organism_subdivision

| text_joined   |   n |
|:--------------|----:|
| breast        |   4 |
| foot          |   4 |
| caruncles     |   3 |
| periodontal   |   3 |
| right groin   |   1 |

#### Organism_substance

| text_joined   |   n |
|:--------------|----:|
| serum         |  20 |
| urine         |  11 |
| blood         |   9 |
| prp           |   6 |
| ppp           |   3 |

#### Pathological_formation

| text_joined   |   n |
|:--------------|----:|
| tumor         |  99 |
| tumors        |  28 |
| tumour        |  12 |
| cancer        |  11 |
| cc-rcc        |  10 |

#### Protein_domain_or_region

| text_joined         |   n |
|:--------------------|----:|
| hs chains           |   1 |
| two serine residues |   1 |

#### Tissue

| text_joined       |   n |
|:------------------|----:|
| tissue            |  20 |
| microvessel       |  12 |
| breast tissue     |   6 |
| capillary         |   5 |
| connective tissue |   4 |
