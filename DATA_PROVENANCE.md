# Data Provenance and Compliance Notes

This document records the current provenance and limitations of the dataset. It is a research record, not legal advice or an institutional ethics determination.

## Sources and sample composition

The repository contains structured records recorded as derived from medical-malpractice court materials from China and the United States. Historical curation described those materials as publicly accessible, but current row-level legal-record identity and accessibility have not been independently verified for 24 of the 25 working cases.

| Material | Records | Release layer |
|---|---:|---|
| `data/formal/case_payloads.json` | 25 | Public working candidate; not approved for formal generation |
| `data/public/case_index.csv` | 25 | Public source-minimised case/status index without direct source keys |
| `data/case_database.json` | 25 | Controlled local curation record |
| `data/cn_medical_cases_deidentified.json` | 612 | Controlled Chinese candidate pool |
| `data/us_cases_deidentified.json` | 490 | Controlled US candidate pool |
| `archive/legacy/selected_cases.json` | 21 | Controlled legacy selection; not used formally |

The formal sample contains 24 Chinese cases and one US case. Cases were retained according to availability and structural usability; no jurisdictional balance, population representativeness, or cross-country inference is claimed.

## Data minimisation

The active model-facing file is `data/formal/case_payloads.json`. It excludes final diagnoses, differential diagnoses, diagnostic-error labels, original case titles, clinician findings used for scoring, ICE inferences, and prewritten patient emotional style. Its model-facing values have been normalized to English, but this normalization remains a draft until documented bilingual semantic review is completed.

The full curation file retains outcome, jurisdiction, and original-title metadata for audit and scoring preparation. It does not contain complete row-level citations. It must not be supplied to either conversational model. Record-level legal identity and full titles must be separated into a protected provenance record before a public release is prepared.

The public payload is not certified as irreversibly anonymous. A masked audit on 26 October 2026 found no coded common direct-identifier pattern in the model-facing payload, but it found a residual direct identifier in three controlled working-data paths and exact calendar dates in 11/24 selected Chinese candidate records, including nine explicit birth dates. Those source-linked files have therefore been classified as controlled and removed from the proposed public Git index. Earlier Git history remains a separate, documented issue.

The investigator has chosen to keep the repository public while applying the layered policy in [`docs/LAYERED_DATA_RELEASE_POLICY_2026-10-26.md`](docs/LAYERED_DATA_RELEASE_POLICY_2026-10-26.md). Before designating a release or OSF Data resource, the team must review the exact public payload, obtain the applicable privacy/legal/ethics determination, record the handling of earlier Git history, and freeze a release manifest and hash.

Before formal generation, the research team must also compare every English model-facing value with the source-language curation record and document that translation did not add, omit, or clinically alter any patient-knowable fact.

## Provenance gaps requiring completion

The controlled `data/formal/source_manifest.csv` records jurisdiction and original title. CAS19 now has a verified official appellate-opinion URL, citation, docket numbers, and access date; the other 24 cases still lack a stable source URL or identifier. These fields must be completed and checked before formal generation, but they are not copied into the source-minimised public case index.

A read-only local audit on 25 October 2026 found the earlier 612-record Chinese working file at `med_malpractice_pipeline/data/cn_medical_cases.json`. It contains the same structured sections as the de-identified candidate pool but no source URL, case number, court, judgment date, document identifier, or preserved raw-text field. It therefore cannot repair the 24 missing references. An exact title match within that local pool establishes only the internal derivation link; it is not independent source verification and must not be recorded as a stable court-record citation.

The detailed follow-up recovery audit is retained in the controlled study record because it contains source-linkage evidence. Exact-title, official-domain, and targeted web searches did not establish an authoritative match for any of the 24 unresolved Chinese cases. Similar search results were treated only as leads and were rejected when legal identity or clinical chronology differed. The formal source manifest must remain unchanged until the original extraction keys or an independently verified authoritative record are recovered.

## Clinical verification

Structured fields may contain extraction errors, inferred ICE content, incomplete OLD CARTS elements, or multiple diagnoses in a single outcome string. `data/formal/gold_labels_draft.json` is therefore a review template rather than a frozen gold standard. The formal gold-label file must be approved by qualified clinicians before experimental generation.

The controlled 24 September 2026 payload-readiness audit additionally identified retrospective outcome or diagnosis leakage, mixed clinical timepoints, invalid first-person speaker roles, and insufficient patient-known information. Its case-level remediation register remains in the controlled study record. No current payload is approved for formal generation.

## Legal and ethical status

Public accessibility does not by itself establish unrestricted copyright, database, privacy, or redistribution rights. The repository therefore makes no blanket claim that all source materials share one Creative Commons licence.

Before release, the research team should obtain institution-appropriate confirmation concerning:

- permission or legal basis for redistribution of each source and derived record;
- data-protection and re-identification risk;
- whether ethics review, exemption, or a formal non-human-subject determination is required;
- the licence covering the team's original database structure and documentation.

Code and data licences should be stated separately. A software licence does not automatically apply to source court records or derived data.
