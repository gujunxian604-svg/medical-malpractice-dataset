# Dataset Construction Record

## Formal set

The formal experimental dataset contains 25 structured medical-malpractice cases. Selection was based on the availability of usable clinical history and an identifiable diagnostic outcome. The resulting distribution is 24 cases from China and one from the United States; it was not designed to balance jurisdictions.

These are candidate curation records, not a formal-generation release or a certification of anonymity. As of 26 October 2026, only CAS19 has an established legal-record identity, its clinical abstraction still requires reconstruction, and the 24 Chinese legal records remain unresolved. The investigator chose a public/controlled split: the model-facing candidate and source-minimised status index remain public, while source-linked curation, candidate pools, diagnoses, detailed recovery audits, and review evidence are controlled. See `docs/LAYERED_DATA_RELEASE_POLICY_2026-10-26.md` for the public classification rule.

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

The latter two materials, the source manifest, both candidate pools, legacy files, raw or licensed source records, and all review work remain controlled and are excluded from the proposed public Git index. The public layer uses case identifiers without direct source keys, a minimal status index, and the separately reviewed model-facing candidate; repository proximity is not an access-control mechanism, and no claim of irreversible unlinkability is made.

The platform should enforce these permissions in code and log the SHA-256 hash of each frozen input file.

## Outstanding review

Before formal data collection:

- complete and document bilingual semantic review of every English model-facing field;
- establish each legal-record identity and record its authoritative source;
- compare the authoritative source with the clinical abstraction, correct discrepancies, and only then assign one canonical primary diagnosis and accepted synonyms;
- separate secondary diagnoses and complications;
- review all organ-system and error-type labels;
- complete stable source references in `source_manifest.csv`;
- perform manual privacy and data-minimisation review and record the disposition of the earlier public Git history;
- freeze the reviewed files and record their hashes.

## Legacy material

The former 21-case `selected_cases.json` used a different schema and is not part of the formal experiment. It is retained locally under `archive/legacy/` as a controlled research-history record and is not tracked in the proposed public branch.
