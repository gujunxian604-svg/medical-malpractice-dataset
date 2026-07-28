# Data Provenance and Compliance Notes

This document records the current provenance and limitations of the dataset. It is a research record, not legal advice or an institutional ethics determination.

## Sources and sample composition

The repository contains structured records derived from publicly accessible medical-malpractice court judgments from China and the United States.

| Material | Records | Role |
|---|---:|---|
| `data/case_database.json` | 25 | Formal curated experimental sample |
| `data/cn_medical_cases_deidentified.json` | 612 | Supporting Chinese candidate pool |
| `data/us_cases_deidentified.json` | 490 | Supporting US candidate pool |
| `archive/legacy/selected_cases.json` | 21 | Legacy intermediate selection; not used formally |

The formal sample contains 24 Chinese cases and one US case. Cases were retained according to availability and structural usability; no jurisdictional balance, population representativeness, or cross-country inference is claimed.

## Data minimisation

The active model-facing file is `data/formal/case_payloads.json`. It excludes final diagnoses, differential diagnoses, diagnostic-error labels, original case titles, clinician findings used for scoring, ICE inferences, and prewritten patient emotional style.

The full curation file retains outcome and citation metadata for audit and scoring preparation. It must not be supplied to either conversational model. Public case titles are retained as provenance metadata and should not be treated as patient dialogue content.

Automated de-identification reduces but does not eliminate re-identification risk. Before publication or redistribution, the research team must perform a documented manual review for names, institutions, locations, dates, case identifiers, and rare combinations of clinical facts.

## Provenance gaps requiring completion

`data/formal/source_manifest.csv` currently records jurisdiction and original title, but stable source URLs or source identifiers are missing for the formal cases. These fields must be completed and checked before manuscript submission so that each case has an auditable derivation path.

## Clinical verification

Structured fields may contain extraction errors, inferred ICE content, incomplete OLD CARTS elements, or multiple diagnoses in a single outcome string. `data/formal/gold_labels_draft.json` is therefore a review template rather than a frozen gold standard. The formal gold-label file must be approved by qualified clinicians before experimental generation.

## Legal and ethical status

Public accessibility does not by itself establish unrestricted copyright, database, privacy, or redistribution rights. The repository therefore makes no blanket claim that all source materials share one Creative Commons licence.

Before release, the research team should obtain institution-appropriate confirmation concerning:

- permission or legal basis for redistribution of each source and derived record;
- data-protection and re-identification risk;
- whether ethics review, exemption, or a formal non-human-subject determination is required;
- the licence covering the team's original database structure and documentation.

Code and data licences should be stated separately. A software licence does not automatically apply to source court records or derived data.
