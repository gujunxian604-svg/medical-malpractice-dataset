# Extraction Logic Documentation

This document describes the field-by-field extraction rules used to convert
raw court opinion text into the standardized 8-field JSON schema.

## Overview

```
Step 1: Get opinion text via CourtListener API
Step 2: Parse text using regex-based field extraction
Step 3: Fill JSON fields according to rules below
Step 4: If a field cannot be extracted, write "Unknown"
Step 5: Save JSON with UTF-8 encoding, indent=2
```

## Field-by-Field Rules

### case_metadata.title
- Extract the complete case title from the opinion header
- US appellate format: combine appellant name + "v." + appellee name
- Fallback: "Unknown"

### case_metadata.document_type
- Default: "Civil Judgment Document"
- If keywords like "criminal", "felony", "murder" appear: "Criminal Judgment Document"

### clinical_facts.patient_demographics
- Extract age (numeric or spelled-out like "seventeen-year-old")
- Extract sex (male/female) based on context near patient references
- If patient is a minor (<18), add "minor"
- If "pediatric" appears, add "pediatric patient"
- Fallback: "Unknown"

### clinical_facts.primary_complaint
- Extract patient's initial symptoms and reason for seeking care
- Look for patterns: "presented with", "complained of", "went to...for"
- Truncate at conjunctions that shift away from complaint (" and died", etc.)
- Fallback: "Unknown"

### clinical_facts.misdiagnosed_condition
- Extract what was initially misdiagnosed or missed
- Look for: "misdiagnosed as", "initially diagnosed with", "failed to diagnose"
- If the case is NOT about diagnostic error (e.g., informed consent, surgical error):
  write "Unknown - [brief explanation]"
- **Never write "N/A"**

### clinical_facts.final_correct_diagnosis
- Extract the actual confirmed disease
- Align with MeSH vocabulary (e.g., "Acute Myocardial Infarction" not "heart attack")
- Check against known disease patterns for reliability
- Fallback: "Unknown"

### organ_system_mapping.primary_system
- **This field name must NEVER be changed**
- Map the diagnosis to ONE of 8 WHO ICD-11 major systems:
  - Cardiovascular, Respiratory, Digestive, Neuropsychiatric
  - Urinary, Endocrine, Reproductive, Musculoskeletal
- Based on keyword matching against diagnosis + surrounding text
- Fallback: "Unknown"

### malpractice_details.diagnostic_error_type
- Classify: misdiagnosis / missed diagnosis / delayed diagnosis
- If case is not about diagnostic error: "Unknown - [explanation]"
- Fallback: "Unknown"

### malpractice_details.expert_appraisal_summary
- Extract specific findings about what the hospital did wrong
- Look for "breach of standard of care", court findings, expert testimony
- Deduplicate similar sentences (word overlap >70%)
- Maximum 3 sentences, 2000 characters
- Fallback: "Unknown"

## Universal Fallback Rule

For ANY field that cannot be extracted or is not applicable:
- Write: `"Unknown"`
- If inapplicable due to case type: `"Unknown - [1-2 sentence explanation]"`
- **NEVER write "N/A" or leave empty**

## Quality Checklist

- [ ] All 8 fields present in the correct structure
- [ ] `primary_system` is exactly one of the 8 allowed values (or "Unknown")
- [ ] No field contains "N/A" or empty string
- [ ] `final_correct_diagnosis` is a proper medical term
- [ ] `expert_appraisal_summary` is specific, not generic
