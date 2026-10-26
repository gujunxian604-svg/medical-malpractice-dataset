# Medical Malpractice Case Dataset

This public repository contains the minimised research layer for a clinical dialogue experiment using medical-malpractice cases recorded as derived from court materials. Source-linked curation, candidate pools, draft diagnoses, and reviewer records are maintained separately as controlled research records. The current model-facing payload remains a **working candidate, not an approved formal input**.

Keeping the repository public does not designate it as the study's final OSF Data resource. Do not link it as OSF Data until the exact public candidate has passed manual privacy, clinical, legal, and institutional review and has a frozen release hash. The public/controlled split is specified in [`docs/LAYERED_DATA_RELEASE_POLICY_2026-10-26.md`](docs/LAYERED_DATA_RELEASE_POLICY_2026-10-26.md).

## Formal experimental sample

The formal sample contains **25 cases selected on the basis of data availability and structural usability**. It is not a jurisdiction-balanced sample:

- China: 24 cases
- United States: 1 case

The sample must not be used for China–US comparisons or interpreted as representative of either jurisdiction. Cases span eight prespecified broad clinical categories. These categories are study-specific groupings, not a complete or official WHO ICD-11 classification.

One ophthalmology case (CAS19) falls outside those eight categories and is labelled `Other/Ophthalmology`. It remains in the overall experiment but is excluded from analyses stratified by the eight prespecified categories unless the analysis plan is amended transparently.

## Files

```text
data/
├── formal/
│   └── case_payloads.json
│       English model-facing candidate fields only. The current normalization
│       remains a draft pending bilingual, clinical, temporal, and privacy review.
├── public/
│   ├── case_index.csv
│   │   Source-minimised case ID, jurisdiction, and provenance-completion status;
│   │   no direct source key is included.
│   └── public_layer_manifest.json
│       Canonical UTF-8/LF public-file hashes and explicit non-authorisation flags.
├── review/
│   ├── clinical_review_queue.v1.json
│   │   Reviewer-only source, payload, risk, and blank adjudication record.
│   ├── clinical_review_decisions_template.csv
│   │   Earlier compact summary worksheet; not sufficient for independent review.
│   ├── clinical_review_independent_template.v2.csv
│   │   Two blank independent decision rows (R1 and R2) for every case.
│   ├── clinical_review_adjudication_template.v2.csv
│   │   One blank final decision/adjudication row for every case.
│   ├── source_recovery_queue.v1.json
│   │   Protected 24-case source-recovery queue; never model-facing.
│   ├── source_recovery_decisions_template.v1.csv
│   │   Blank legal-identity and clinical-abstraction recovery worksheet.
│   ├── drafts/
│   │   Reviewer-only evidence summaries for CAS01-CAS25; not clinical sign-off.
│   ├── review_artifacts.sha256
│   │   Current hashes for the protected local review records.
│   └── protected_layer_manifest.json
│       Hash-only inventory of controlled local files; ignored by Git.

archive/legacy/
└── README.md
    The legacy selection itself is controlled and untracked.
```

The controlled local layer includes `data/case_database.json`, both candidate pools, `data/formal/gold_labels_draft.json`, `data/formal/source_manifest.csv`, and `archive/legacy/selected_cases.json`. These paths are ignored and must not be re-added to the public branch.

## Leakage prevention

The dialogue platform must read only `data/formal/case_payloads.json` when constructing patient-model context. It must never load `data/case_database.json` or `data/formal/gold_labels_draft.json` into the patient or physician model context.

Prompt instructions such as “do not reveal the diagnosis” are not an adequate substitute for this separation: information already present in model context may still influence generated dialogue even when it is not reproduced verbatim.

Gold labels must be accessed only after dialogue generation by the scoring and analysis components.

## Required clinical review before data collection

The English normalization of `case_payloads.json` must undergo documented bilingual semantic review against the source-language curation records before it is frozen for generation. Reviewers must verify that no temporal detail, symptom, severity statement, or patient-knowable fact was added, omitted, or clinically altered during translation.

Record the field-level review and whole-file sign-off in the controlled review record. Review evidence is provenance-only and must not enter model context or the public data layer.

The controlled 24 September 2026 readiness audit found that the current candidate is not suitable for formal generation: all 25 reference labels remain unsigned, and every payload requires clinical, temporal, speaker-role, information-sufficiency, or leakage remediation. The 25 case IDs are a fixed candidate roster, not yet a frozen formal input release.

The controlled file `data/formal/gold_labels_draft.json` intentionally leaves `primary_gold_diagnosis` unset. A qualified clinician must review every case and provide:

1. one canonical primary diagnosis;
2. accepted diagnostic synonyms or equivalent terms;
3. secondary diagnoses, when applicable;
4. confirmation of organ-system and diagnostic-error labels.

After review, save the frozen result as `gold_labels.json`, record the version or commit hash in the protocol, and do not alter it after formal generation begins except through a documented amendment.

## Fail-closed release audit

Prepare and audit the layered public candidate with:

```powershell
node .\prepare_layered_data_release.mjs
node .\audit_layer_separation.mjs
```

The public-layer audit verifies that the six controlled paths are absent from the proposed public Git index and that the public payload/index do not contain the coded direct-identifier patterns. Automated success never grants public-release or formal-generation authority.

Additional source-recovery, clinical-review, and formal-readiness tools operate on the controlled layer and are maintained in the access-controlled study workspace. They are intentionally absent from this public candidate until their own content and dependencies have been reviewed for public release. Their success cannot authorise formal generation.

## Archived material

The previous 21-case selection and the earlier extraction code were removed from the active dataset because they do not define the formal 25-case experiment. Experimental platform code, prompts, internal-model measurement code, rating instruments, and statistical analysis code will be maintained in a separate experiment repository.

## Data provenance and use

See [DATA_PROVENANCE.md](DATA_PROVENANCE.md) and [docs/dataset_construction.md](docs/dataset_construction.md). The repository does not currently grant a blanket licence for the underlying court materials. Users must verify applicable source terms and legal, ethical, and institutional requirements before reuse.
