"""
Field extraction logic for medical malpractice cases.
Converts raw opinion text into the standardized 8-field JSON schema.

JSON Schema:
{
  "case_metadata": {
    "title": "...",
    "document_type": "Civil Judgment Document"
  },
  "clinical_facts": {
    "patient_demographics": "...",
    "primary_complaint": "...",
    "misdiagnosed_condition": "...",
    "final_correct_diagnosis": "..."
  },
  "organ_system_mapping": {
    "primary_system": "Cardiovascular|Respiratory|Digestive|Neuropsychiatric|Urinary|Endocrine|Reproductive|Musculoskeletal|Unknown"
  },
  "malpractice_details": {
    "diagnostic_error_type": "misdiagnosis|missed diagnosis|delayed diagnosis|Unknown",
    "expert_appraisal_summary": "..."
  }
}

Rules:
- Never use "N/A". Use "Unknown" for all missing/inapplicable fields.
- primary_system field name MUST NEVER be changed.
- Only one of the 8 WHO ICD-11 systems can be selected.
"""

import re


# WHO ICD-11 eight major organ systems with keyword mappings
ORGAN_SYSTEMS = {
    "Cardiovascular": [
        "heart", "cardiac", "coronary", "myocardial", "hypertension",
        "atrial", "ventricular", "vascular", "aortic", "artery",
        "thrombus", "embolism", "arrhythmia", "cardiopulmonary",
    ],
    "Respiratory": [
        "lung", "pulmonary", "respiratory", "pneumonia", "asthma",
        "copd", "bronch", "trachea", "pleural",
    ],
    "Digestive": [
        "stomach", "liver", "hepat", "intestin", "bowel", "colon",
        "pancreat", "gallbladder", "appendi", "esophag", "gastric",
        "gastro", "cholecystitis", "sepsis", "periton",
    ],
    "Neuropsychiatric": [
        "brain", "cerebral", "neuro", "spinal", "cord", "seizure",
        "epilep", "dementia", "psychiatric", "mental", "cognit",
        "stroke", "aneurysm", "subarachnoid", "hemorrhage",
    ],
    "Urinary": [
        "kidney", "renal", "bladder", "urin", "ureth", "nephr",
        "ureter", "hemodialysis", "dialysis",
    ],
    "Endocrine": [
        "diabet", "thyroid", "adrenal", "pituitary", "hormone",
        "insulin", "endocrin", "hyperglyc", "hypoglyc",
    ],
    "Reproductive": [
        "pregnan", "uterus", "uterine", "ovar", "prostate",
        "testicular", "cervical", "endometri", "placenta", "fetal",
        "obstetric", "gynec",
    ],
    "Musculoskeletal": [
        "bone", "fracture", "joint", "muscle", "skeletal",
        "orthoped", "arthrit", "spine", "femur", "tibia", "hip", "knee",
        "cervical",
    ],
}

# Known disease names for better final diagnosis extraction
DISEASE_PATTERNS = [
    r"\b(pulmonary\s+hypertension|myocardial\s+infarction|acute\s+myocardial\s+infarction|"
    r"cardiac\s+arrest|sepsis|septic\s+shock|pneumonia|stroke|cerebral\s+hemorrhage|"
    r"subarachnoid\s+hemorrhage|appendicitis|pancreatitis|cholecystitis|"
    r"diabetes\s+mellitus|chronic\s+obstructive\s+pulmonary\s+disease|COPD|"
    r"acute\s+respiratory\s+distress\s+syndrome|ARDS|renal\s+failure|kidney\s+failure|"
    r"hepatic\s+failure|liver\s+failure|cancer|tumor|carcinoma|leukemia|lymphoma|"
    r"hypovolemic\s+shock|cardiogenic\s+shock|anaphylaxis|pulmonary\s+embolism|"
    r"deep\s+vein\s+thrombosis|aortic\s+dissection|aortic\s+aneurysm|"
    r"intracranial\s+hemorrhage|meningitis|encephalitis|epilepsy|seizure\s+disorder|"
    r"urosepsis|peritonitis|bowel\s+obstruction|ischemic\s+bowel)\b",
]


def classify_organ_system(diagnosis, full_text):
    """Map a diagnosis to one of the 8 WHO ICD-11 major organ systems."""
    search_text = (diagnosis + " " + full_text[:5000]).lower()
    scores = {}
    for system, keywords in ORGAN_SYSTEMS.items():
        score = sum(1 for kw in keywords if kw in search_text)
        if score > 0:
            scores[system] = score
    if scores:
        return max(scores, key=scores.get)
    return "Unknown"


def extract_case_title(text):
    """Extract the case title from opinion text."""
    # Pattern: "APPELLANT v. APPELLEE" format
    m = re.search(
        r"NO\.\s+[\dA-Z\-]+\s+\n?(.*?)\s+v\.\s+(.*?)\s+"
        r"(?:DATE\s+OF\s+JUDGMENT|APPELLEE|APPELLANT)",
        text, re.DOTALL,
    )
    if m:
        appellant = re.sub(r"\s+", " ", m.group(1)).replace("APPELLANT", "").strip()
        appellee = re.sub(r"\s+", " ", m.group(2)).replace("APPELLEE", "").strip()
        if appellant and appellee:
            return f"{appellant} v. {appellee}"
    # Fallback: any "X v. Y" in the first 2000 chars
    m = re.search(
        r"([A-Z][A-Z\s,.&\-()]{5,})\s+v\.\s+([A-Z][A-Z\s,.&\-()]{5,})",
        text[:2000],
    )
    if m:
        return f"{m.group(1).strip()} v. {m.group(2).strip()}"
    return "Unknown"


def extract_document_type(text):
    """Determine if the case is civil or criminal."""
    if re.search(
        r"\b(criminal|felony|misdemeanor|murder|assault|battery\s+(?:charge|conviction))\b",
        text[:3000], re.IGNORECASE,
    ):
        return "Criminal Judgment Document"
    return "Civil Judgment Document"


def extract_patient_demographics(text):
    """Extract patient age and sex from the opinion text."""
    parts = []

    # Age patterns
    age = None
    for pat in [
        r"(\d+)[\- ]year[\- ]old\s+(?:patient|decedent|girl|boy|woman|man|female|male)",
        r"(?:patient|decedent|victim|child)\s*(?:was|is|a)\s*(?:a\s+)?(\d+)[\- ]year[\- ]old",
        r"(\d+)[\- ]year[\- ]old\s+(?:patient|decedent|victim|girl|boy|woman|man)",
        r"aged\s+(\d+)\s*(?:years|year|y/o)",
        r"age\s+(?:of\s+)?(\d+)",
    ]:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            age = m.group(1)
            break
    if not age:
        m = re.search(r"(\d+)[\- ]year[\- ]old", text[:3000])
        if m:
            age = m.group(1)
    # Spelled-out ages (e.g., "Seventeen-year-old")
    if not age:
        word_to_num = {
            "seventeen": "17", "eighteen": "18", "sixteen": "16",
            "fifteen": "15", "fourteen": "14", "thirteen": "13",
            "twelve": "12", "eleven": "11", "twenty": "20", "thirty": "30",
            "forty": "40", "fifty": "50", "sixty": "60", "seventy": "70",
            "eighty": "80", "ninety": "90",
        }
        m = re.search(
            r"\b(seventeen|eighteen|sixteen|fifteen|fourteen|thirteen|twelve|eleven|"
            r"twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety)[\s\-]+year[\s\-]+old",
            text[:5000], re.IGNORECASE,
        )
        if m:
            age = word_to_num.get(m.group(1).lower())

    # Sex patterns
    sex = None
    for pat in [
        r"(?:patient|decedent|victim|child|plaintiff)\s+[^.]*?\b(female|male)\b",
        r"\b(female|male)\s+(?:patient|decedent|victim|child|plaintiff)",
        r"(\d+)[\- ]year[\- ]old\s+(female|male)",
        r"her\s+(?:daughter|son|mother|father|sister|brother)",
        r"his\s+(?:daughter|son|mother|father|sister|brother)",
        r"\b(she|her)\s+(?:was|had|underwent|was admitted|died|suffered)",
    ]:
        m = re.search(pat, text[:5000], re.IGNORECASE)
        if m:
            raw = m.group(0).lower()
            if "daughter" in raw or "she" in raw or "her" in raw or "female" in raw:
                sex = "female"
            else:
                sex = "male"
            break

    if age and sex:
        parts.extend([sex, f"{age} years old"])
    elif age:
        parts.append(f"{age} years old")
    elif sex:
        parts.append(sex)

    if age and age.isdigit() and int(age) < 18:
        parts.append("minor")
    if re.search(r"\bpediatric\b", text[:5000], re.IGNORECASE) and "minor" not in parts:
        parts.append("pediatric patient")

    return ", ".join(parts) if parts else "Unknown"


def extract_primary_complaint(text):
    """Extract the patient's initial symptoms and reason for seeking care."""
    for pat in [
        r"(?:went to|was taken to|was brought to|arrived at)\s+[^.]*?"
        r"(?:for|because of|with|to\s+see|to\s+have)\s+([^.]{10,250})",
        r"(?:presented|was admitted|sought treatment)[^.]*?"
        r"(?:with|for|complaining of|because of)\s+([^.]{10,250})",
        r"(?:complained of|chief complaint[^:]*:)\s*([^.{]{10,250})",
        r"(?:was referred to)\s+[^.]*?(?:for|because of|with)\s+([^.]{10,250})",
    ]:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            complaint = m.group(1).strip().rstrip(";,")
            for cutoff in [
                " and died", " and later", " and subsequently",
                " and was", " and underwent", "; however",
            ]:
                idx = complaint.lower().find(cutoff.lower())
                if idx > 10:
                    complaint = complaint[:idx].strip()
            return complaint
    # Fallback: first patient description in FACTS section
    m = re.search(
        r"(?:FACTS|FACTUAL\s+BACKGROUND|BACKGROUND)\s*.*?"
        r"(?:[¶¶]\d+\.?\s*)?"
        r"((?:[A-Z][a-z]+\s+)?(?:went|was|arrived|presented|sought|admitted|referred|consultation)[^.]{20,300})",
        text, re.DOTALL | re.IGNORECASE,
    )
    if m:
        return m.group(1).strip()
    return "Unknown"


def extract_misdiagnosed_condition(text):
    """Extract the initially misdiagnosed or missed condition."""
    for pat in [
        r"(?:misdiagnos\w+|wrongly diagnos\w+|incorrectly diagnos\w+|"
        r"initially diagnos\w+ as|treated as|mistakenly diagnos\w+)[^:]*[:\s]+([^.{]{10,200})",
        r"(?:was|were)\s+(?:initially|originally|first)\s+diagnos\w+\s+(?:as|with)\s+([^.{]{10,200})",
        r"(?:fail\w+|failed)\s+to\s+diagnos\w+\s+([^.{]{10,200})",
        r"missed\s+diagnos\w+\s+(?:of\s+)?([^.{]{10,200})",
        r"delay\w*\s+in\s+diagnos\w+\s+(?:of\s+)?([^.{]{10,200})",
    ]:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            return m.group(1).strip().rstrip(";,")
    # Check for non-diagnostic case types
    for kw in [
        "informed consent", "surgical error", "medication error",
        "failure to monitor", "nursing negligence", "lack of consent",
    ]:
        if re.search(kw, text, re.IGNORECASE):
            return f"Unknown - The case does not involve a diagnostic error. " \
                   f"The dispute centers on {kw}."
    return "Unknown"


def extract_final_diagnosis(text):
    """Extract the confirmed diagnosis, aligned with MeSH vocabulary."""
    # Try known disease patterns first
    for pat in DISEASE_PATTERNS:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            disease = m.group(1).strip()
            start = max(0, m.start() - 200)
            context = text[start:m.end() + 200].lower()
            if any(kw in context for kw in [
                "diagnosed", "diagnosis", "suffered", "condition",
                "had", "was found", "confirmed", "died", "death",
            ]):
                return disease
    # Contextual patterns
    for pat in [
        r"(?:was\s+)?diagnos\w+\s+(?:with|as\s+having)\s+([A-Z][^.{]{3,100})",
        r"diagnos\w+\s+of\s+([A-Z][^.{]{3,100})",
        r"(?:suffered\s+from|was\s+found\s+to\s+have|had)\s+([A-Z][^.{]{3,100})",
        r"(?:died\s+from|died\s+of|cause\s+of\s+death\s+was)\s+([^.{]{3,100})",
    ]:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            diagnosis = re.sub(r"\s+", " ", m.group(1).strip().rstrip(";,."))
            if len(diagnosis) > 100:
                diagnosis = diagnosis[:100]
            if not re.search(
                r"(?i)(posttraumatic|stress disorder|hard time|family|after.*death|weekend)",
                diagnosis,
            ):
                return diagnosis
    return "Unknown"


def extract_diagnostic_error_type(text):
    """Classify the type of diagnostic error."""
    if re.search(r"misdiagnos\w+|wrongly diagnos\w+|incorrectly diagnos\w+", text, re.IGNORECASE):
        return "misdiagnosis"
    if re.search(r"missed diagnos\w+|failure to diagnos\w+|fail\w+ to diagnos\w+", text, re.IGNORECASE):
        return "missed diagnosis"
    if re.search(r"delay\w*\s+in\s+diagnos\w+|delayed diagnos\w+", text, re.IGNORECASE):
        return "delayed diagnosis"
    for kw in [
        "informed consent", "surgical error", "medication error",
        "failure to monitor", "nursing negligence", "lack of consent",
        "breach of standard of care",
    ]:
        if re.search(kw, text, re.IGNORECASE):
            return f"Unknown - The case involves {kw}, not a diagnostic error."
    return "Unknown"


def extract_expert_appraisal_summary(text):
    """Extract findings about what the hospital did wrong."""
    patterns = [
        r"((?:breach\w*\s+(?:of\s+)?(?:the\s+)?standard\s+of\s+care)[^.]*\.)",
        r"((?:found\s+that|court\s+found|trial\s+court\s+found|concluded|determined)"
        r"[^.]*?(?:breach|negligence|fault|error|violation|failed|proximate\s+cause)[^.]*\.)",
        r"((?:expert\s+testif\w+|expert\s+witness)[^.]*?"
        r"(?:breach|negligence|standard|failed|violation|proximate\s+cause)[^.]*\.)",
    ]
    found_parts = []
    seen_normalized = set()
    for pat in patterns:
        for m in re.findall(pat, text, re.IGNORECASE | re.DOTALL):
            cleaned = re.sub(r"\s+", " ", m).strip()
            cleaned = re.sub(r"¶\d+", "", cleaned).strip()
            if len(cleaned) < 30:
                continue
            normalized = re.sub(r"[^a-z0-9\s]", "", cleaned.lower())
            normalized = re.sub(r"\s+", " ", normalized)
            is_dup = False
            for existing in seen_normalized:
                if normalized in existing or existing in normalized:
                    is_dup = True
                    break
                words1 = set(normalized.split())
                words2 = set(existing.split())
                if words1 and words2:
                    overlap = len(words1 & words2) / max(len(words1), len(words2))
                    if overlap > 0.7:
                        is_dup = True
                        break
            if not is_dup:
                found_parts.append(cleaned)
                seen_normalized.add(normalized)
    if found_parts:
        summary = " ".join(found_parts[:3])
        return summary[:2000] if len(summary) > 2000 else summary
    # Fallback
    for pat in [
        r"((?:we\s+)?(?:find|conclude|hold|affirm|reverse)[^.]*?"
        r"(?:no\s+error|error|negligence|breach|standard)[^.]*\.)",
        r"((?:we\s+)?(?:affirm|reverse)[^.]*\.)",
    ]:
        matches = re.findall(pat, text, re.IGNORECASE)
        if matches:
            return " ".join(matches[:3])
    return "Unknown"


def parse_opinion_to_json(full_text, case_title=None, source_url=None):
    """
    Parse a full opinion text into the standardized medical JSON schema.

    Args:
        full_text: Raw text of the court opinion
        case_title: Optional case title (from API metadata, more reliable)
        source_url: Optional source URL

    Returns:
        Dict matching the 8-field JSON schema
    """
    title = case_title if case_title else extract_case_title(full_text)

    patient_demo = extract_patient_demographics(full_text)
    primary_complaint = extract_primary_complaint(full_text)
    misdiagnosed = extract_misdiagnosed_condition(full_text)
    final_diagnosis = extract_final_diagnosis(full_text)
    primary_system = classify_organ_system(final_diagnosis, full_text)
    error_type = extract_diagnostic_error_type(full_text)
    appraisal_summary = extract_expert_appraisal_summary(full_text)

    result = {
        "case_metadata": {
            "title": title,
            "document_type": extract_document_type(full_text),
        },
        "clinical_facts": {
            "patient_demographics": re.sub(r"\s+", " ", patient_demo).strip(),
            "primary_complaint": re.sub(r"\s+", " ", primary_complaint).strip(),
            "misdiagnosed_condition": re.sub(r"\s+", " ", misdiagnosed).strip(),
            "final_correct_diagnosis": re.sub(r"\s+", " ", final_diagnosis).strip(),
        },
        "organ_system_mapping": {
            "primary_system": primary_system,
        },
        "malpractice_details": {
            "diagnostic_error_type": re.sub(r"\s+", " ", error_type).strip(),
            "expert_appraisal_summary": re.sub(r"\s+", " ", appraisal_summary).strip(),
        },
    }

    if source_url:
        result["source_url"] = source_url

    return result
