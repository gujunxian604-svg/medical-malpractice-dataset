# Layered Data Release Policy

**Decision date:** 26 October 2026
**Investigator decision:** keep the repository public and separate public research materials from controlled provenance and review materials
**Current status:** local cleanup candidate; no commit, push, release, or Git-history rewrite has been performed

## Public layer

The public layer may contain:

- the current model-facing candidate payload, after automated and manual privacy review;
- case IDs without direct source keys, plus jurisdiction and provenance-completion status only;
- prompts, code, schemas, analysis specifications, aggregate results, and documentation; and
- a release manifest containing exact hashes and explicit authority flags.

The public case index must not contain original titles, source URLs, court or docket identifiers, names, exact dates, source diagnosis, clinical scoring labels, or a key that restores a one-to-one source link.

`data/formal/case_payloads.json` remains a working candidate rather than an approved formal input. Its inclusion in the public layer does not authorise formal generation, prove anonymisation, or replace manual review of rare combinations and quasi-identifiers.

## Controlled layer

The following paths are controlled research records and must not be re-added to the public branch:

- `archive/legacy/selected_cases.json`;
- `data/case_database.json`;
- `data/cn_medical_cases_deidentified.json`;
- `data/us_cases_deidentified.json`;
- `data/formal/gold_labels_draft.json`; and
- `data/formal/source_manifest.csv`.

These files remain available in the authorised local working environment and are recorded by hash in the ignored `data/review/protected_layer_manifest.json`. The protected layer may also contain source-recovery logs, raw or licensed judgments, reviewer identities and decisions, source wording, and adjudication records.

## Operational rule

Run:

```powershell
node .\prepare_layered_data_release.mjs
node .\audit_layer_separation.mjs
```

The preparation step creates only a source-minimised public case index, a public candidate manifest, and a protected hash manifest. Public text-file hashes use UTF-8 after BOM removal and newline normalization to LF, so the recorded digest is stable across ordinary Windows and Unix checkouts. The step never copies original titles, source URLs, diagnoses, exact dates, or free-text source material into the public index. The absence of direct source keys is not presented as proof that rare clinical combinations cannot be linked externally.

The automated audit must pass before a public commit is proposed, but its success never grants public-release or formal-generation authority. The exact public candidate still requires manual privacy, clinical, legal, and investigator review.

## Git-history boundary

Removing controlled files from the current branch prevents them from appearing in future snapshots but does not erase earlier public commits or copies. The investigator has chosen to keep the repository public. History treatment therefore remains a separate, explicit decision: either retain the dated historical record with a transparent correction notice, or perform a coordinated history rewrite after preserving an authorised evidence snapshot. No history rewrite is authorised by this policy.
