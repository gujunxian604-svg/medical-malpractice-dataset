# Data Dictionary

## `data/formal/case_payloads.json`

| Field | Meaning |
|---|---|
| `case_id` | Stable study identifier; joins dialogue, rating, and gold-label records |
| `patient_demographics` | Available age, sex, and occupation fields |
| `old_carts` | Onset, location, duration, character, aggravating/alleviating factors, radiation, temporal pattern, and severity |
| `past_medical_history` | Source-derived prior medical history available to the simulated patient |
| `medication_history` | Source-derived medication history available to the simulated patient |

`Unknown` means that the source-derived structured record does not contain usable information. It must not be replaced by invented facts.

## Controlled local file: `data/formal/gold_labels_draft.json`

This scoring-side file is deliberately untracked in the public layer. Its schema is documented here so authorised reviewers can interpret the controlled record without exposing its values.

| Field | Meaning |
|---|---|
| `primary_gold_diagnosis` | Canonical primary diagnosis; currently unset pending clinical review |
| `accepted_synonyms` | Clinician-approved equivalent diagnostic expressions |
| `secondary_diagnoses` | Diagnoses or complications not used as the primary S1 target |
| `original_final_diagnosis` | Original compound diagnosis string retained for audit |
| `differential_diagnoses` | Curated alternative diagnoses |
| `misdiagnosed_condition` | Condition initially diagnosed or missed, when available |
| `key_clinical_findings` | Findings retained for clinical review and scoring support |
| `organ_system` | Prespecified broad clinical category; CAS19 is `Other/Ophthalmology` |
| `included_in_eight_category_subgroup` | Whether the case belongs to one of the eight prespecified categories |
| `error_type` | Curated diagnostic-error classification |
| `source_jurisdiction` | `CN` or `US`; not a patient-model variable |
| `clinician_verification_status` | Review state of the scoring label |
| `clinical_review_required` | Must be false before the file is frozen for formal scoring |
