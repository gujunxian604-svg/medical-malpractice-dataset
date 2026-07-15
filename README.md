# Medical Malpractice Case Dataset

A reproducible pipeline for extracting structured medical malpractice cases
from US court opinions and Chinese court judgments, then selecting a balanced
set of representative cases for clinical AI evaluation research.

## Pipeline Overview

```
Step 1: Download US cases       (CourtListener API)
Step 2: Extract with LLM         (DeepSeek V3)
Step 3: Merge US + CN data       (CN data manually extracted)
Step 4: Filter + select representative cases (proportional + balanced; script default --count 30)
```

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Copy config template and add your API keys
cp config.example.py config.py
# Edit config.py with your CourtListener + DeepSeek keys

# 3. Run the full pipeline
python src/download_hybrid.py --count 500
python src/extract_with_llm.py
python src/select_cases.py --count 21   # committed selected_cases.json = 21 (script default --count is 30)

# 4. Result: data/selected_cases.json — 21 representative de-identified cases (committed; script default --count is 30)
```

## Data Sources

| Source | Method | Cases | Period |
|--------|--------|-------|--------|
| US (CourtListener API) | Automated (this code) | 490 | 2025-01-01 to 2026-01-01 |
| China (裁判文书网) | Manual extraction | 612 | 2025-01-01 to 2026-01-01 |

## JSON Schema (8 Fields)

```json
{
  "case_metadata": {
    "title": "Case title",
    "document_type": "Civil Judgment Document"
  },
  "clinical_facts": {
    "patient_demographics": "e.g., female, 56 years old",
    "primary_complaint": "Initial symptoms",
    "misdiagnosed_condition": "What was misdiagnosed",
    "final_correct_diagnosis": "Confirmed diagnosis (MeSH)"
  },
  "organ_system_mapping": {
    "primary_system": "One of 8 WHO ICD-11 systems"
  },
  "malpractice_details": {
    "diagnostic_error_type": "misdiagnosis | missed | delayed",
    "expert_appraisal_summary": "What went wrong"
  }
}
```

**Rules:** Never use "N/A" — use "Unknown". `primary_system` must be one of:
Cardiovascular, Respiratory, Digestive, Neuropsychiatric, Urinary,
Endocrine, Reproductive, Musculoskeletal.

## Project Structure

```
medical-malpractice-dataset/
├── README.md
├── config.example.py       # Template — copy to config.py
├── config.py               # Your keys (gitignored)
├── requirements.txt
├── .gitignore
├── src/
│   ├── download_hybrid.py      # Step 1: Download US cases via API
│   ├── extract_with_llm.py     # Step 2: LLM extraction (DeepSeek V3)
│   ├── extract_fields.py       # Regex-based field extraction (Step 1 alt)
│   ├── extract_us_cases.py     # API-only downloader (Step 1 alt)
│   └── select_cases.py    # Step 4: Select representative cases (default --count 30; committed set = 21)
├── data/
│   ├── selected_cases.json         # 21 representative de-identified cases (committed)
│   ├── case_database.json          # 25 OLD CARTS structured gold cases (experiment set; all with final_diagnosis)
│   ├── us_cases.json           # Raw US download (gitignored, ~18MB)
│   ├── us_cases_llm.json       # LLM-extracted US (gitignored)
│   └── cn_medical_cases.json   # CN cases (gitignored)
└── docs/
    └── extraction_logic.md     # Detailed extraction rules
```

## Case Selection Algorithm

The selection in `select_cases.py` works as follows:

1. **Filter** — keep only cases where all 8 fields have non-"Unknown" values
   AND `primary_system` is one of the 8 WHO ICD-11 systems
   AND `diagnostic_error_type` is misdiagnosis/missed/delayed

2. **Intersect** — US and CN cases are normalized to the same schema,
   then combined into one candidate pool

3. **Allocate** — seats distributed proportionally by source volume
   using the largest remainder method (ensures fair rounding)

4. **Balance** — within each source, cases selected via round-robin
   across (organ_system × error_type) cells for diversity

## API Keys Needed

- **CourtListener** (free): https://www.courtlistener.com/profile/api-token/
- **DeepSeek** (paid, ~$0.002/case): https://platform.deepseek.com/

## License

CourtListener data: CC-BY-NC-SA 4.0
