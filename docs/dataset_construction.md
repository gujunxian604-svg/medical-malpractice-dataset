# Dataset Construction Record

## Formal set

The formal experimental dataset contains 25 structured medical-malpractice cases. Selection was based on the availability of usable clinical history and an identifiable diagnostic outcome. The resulting distribution is 24 cases from China and one from the United States; it was not designed to balance jurisdictions.

Each full curation record contains:

- a stable study case ID;
- patient demographics;
- OLD CARTS history fields;
- ICE fields generated or inferred during curation;
- past medical and medication history;
- outcome and differential diagnoses;
- key clinical findings;
- provenance and study classification fields.

ICE content and `patient_response_style` are not treated as source-grounded clinical facts and are excluded from the model-facing payload. They must not be used to generate the registered emotion manipulation.

## Experimental separation

The data are separated by role:

| File | Permitted consumer | Prohibited use |
|---|---|---|
| `case_payloads.json` | Patient-simulation component | Outcome scoring |
| `gold_labels.json` after clinical approval | Scoring/analysis component | Patient or physician context |
| `case_database.json` | Curation audit only | Direct model input |

The platform should enforce these permissions in code and log the SHA-256 hash of each frozen input file.

## Outstanding review

Before formal data collection:

- assign one canonical primary diagnosis and accepted synonyms for every case;
- separate secondary diagnoses and complications;
- review all organ-system and error-type labels;
- complete stable source references in `source_manifest.csv`;
- perform manual privacy and data-minimisation review;
- freeze the reviewed files and record their hashes.

## Legacy material

The former 21-case `selected_cases.json` used a different schema and is not part of the formal experiment. It is retained under `archive/legacy/` solely to preserve research history.
