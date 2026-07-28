# Medical Malpractice Case Dataset

This repository contains the data materials for a clinical dialogue experiment using de-identified medical-malpractice cases derived from publicly accessible court judgments.

## Formal experimental sample

The formal sample contains **25 cases selected on the basis of data availability and structural usability**. It is not a jurisdiction-balanced sample:

- China: 24 cases
- United States: 1 case

The sample must not be used for China–US comparisons or interpreted as representative of either jurisdiction. Cases span eight prespecified broad clinical categories. These categories are study-specific groupings, not a complete or official WHO ICD-11 classification.

One ophthalmology case (CAS19) falls outside those eight categories and is labelled `Other/Ophthalmology`. It remains in the overall experiment but is excluded from analyses stratified by the eight prespecified categories unless the analysis plan is amended transparently.

## Files

```text
data/
├── case_database.json
│   Full curation record for the 25 formal cases. Contains outcome information
│   and MUST NOT be supplied directly to a patient-simulation model.
├── formal/
│   ├── case_payloads.json
│   │   Model-facing, patient-knowable fields only.
│   ├── gold_labels_draft.json
│   │   Draft scoring-side labels. Primary diagnoses and accepted synonyms
│   │   require clinician verification before the formal experiment.
│   └── source_manifest.csv
│       Provenance checklist; stable source identifiers/URLs remain to be added.
├── cn_medical_cases_deidentified.json
│   Supporting Chinese candidate pool; not the formal experimental sample.
└── us_cases_deidentified.json
    Supporting US candidate pool; not the formal experimental sample.

archive/legacy/
└── selected_cases.json
    Legacy 21-case intermediate selection. Not used in the formal experiment.
```

## Leakage prevention

The dialogue platform must read only `data/formal/case_payloads.json` when constructing patient-model context. It must never load `data/case_database.json` or `data/formal/gold_labels_draft.json` into the patient or physician model context.

Prompt instructions such as “do not reveal the diagnosis” are not an adequate substitute for this separation: information already present in model context may still influence generated dialogue even when it is not reproduced verbatim.

Gold labels must be accessed only after dialogue generation by the scoring and analysis components.

## Required clinical review before data collection

The file `gold_labels_draft.json` intentionally leaves `primary_gold_diagnosis` unset. A qualified clinician must review every case and provide:

1. one canonical primary diagnosis;
2. accepted diagnostic synonyms or equivalent terms;
3. secondary diagnoses, when applicable;
4. confirmation of organ-system and diagnostic-error labels.

After review, save the frozen result as `gold_labels.json`, record the version or commit hash in the protocol, and do not alter it after formal generation begins except through a documented amendment.

## Archived material

The previous 21-case selection and the earlier extraction code were removed from the active dataset because they do not define the formal 25-case experiment. Experimental platform code, prompts, internal-model measurement code, rating instruments, and statistical analysis code will be maintained in a separate experiment repository.

## Data provenance and use

See [DATA_PROVENANCE.md](DATA_PROVENANCE.md) and [docs/dataset_construction.md](docs/dataset_construction.md). The repository does not currently grant a blanket licence for the underlying court materials. Users must verify applicable source terms and legal, ethical, and institutional requirements before reuse.
