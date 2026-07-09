"""
Select the final case set from combined US + CN medical malpractice datasets.

Pipeline:
  1. Load US cases (LLM-extracted) and CN cases (manually extracted)
  2. Filter: keep only cases with complete clinical data
     - final_correct_diagnosis != Unknown
     - patient_demographics != Unknown
     - primary_complaint != Unknown
     - diagnostic_error_type in {misdiagnosis, missed, delayed}
  3. Intersect: organ system must be one of 8 WHO ICD-11 systems
  4. Allocate: distribute N seats proportionally by source (US% vs CN%)
  5. Balance: within each source, spread across organ systems + error types
  6. Output: data/selected_cases.json

Usage:
    python src/select_cases.py                 # default: 30 cases
    python src/select_cases.py --count 30      # specify count
    python src/select_cases.py --seed 42       # reproducibility
"""

import json
import os
import sys
import random
import argparse
from collections import defaultdict

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# 8 WHO ICD-11 major organ systems (the only allowed primary_system values)
VALID_SYSTEMS = [
    "Cardiovascular", "Respiratory", "Digestive", "Neuropsychiatric",
    "Urinary", "Endocrine", "Reproductive", "Musculoskeletal",
]

# Valid diagnostic error types (normalized to English)
VALID_ERROR_TYPES = {"misdiagnosis", "missed diagnosis", "delayed diagnosis"}

# CN error type → English normalization
CN_ERROR_MAP = {
    "误诊": "misdiagnosis",
    "漏诊": "missed diagnosis",
    "延误诊断": "delayed diagnosis",
    "误诊/漏诊": "misdiagnosis",
    "漏诊、延误诊断": "delayed diagnosis",
    "误诊、漏诊": "misdiagnosis",
}

# CN organ system → 8-system normalization
CN_SYSTEM_MAP = {
    "Musculoskeletal": "Musculoskeletal",
    "Neuropsychiatric": "Neuropsychiatric",
    "Nervous": "Neuropsychiatric",
    "Nervous System": "Neuropsychiatric",
    "Nervous system（Spinal cord）、Musculoskeletal system": "Neuropsychiatric",
    "Cardiovascular": "Cardiovascular",
    "Cardiovascular, Cerebrovascular": "Cardiovascular",
    "Circulatory": "Cardiovascular",
    "Digestive": "Digestive",
    "Respiratory": "Respiratory",
    "Reproductive": "Reproductive",
    "Endocrine and Breast": "Endocrine",
    "Endocrine": "Endocrine",
    "Endocrine, Metabolic & Immune": "Endocrine",
    "Immune": "Endocrine",
    "Urinary": "Urinary",
    # Everything below maps to None (excluded from the selected set)
    "Integumentary": None, "Skin and Subcutaneous Tissue": None,
    "Sensory": None, "Otolaryngological": None, "Ophthalmological": None,
    "Hemic and Lymphatic": None, "Systemic Processes and Conditions": None,
    "Unknown": None,
}

# Input file paths (relative to project root)
US_INPUT = "data/us_cases_llm.json"
CN_INPUT = "data/cn_medical_cases.json"

# Output
OUTPUT = "data/selected_cases.json"


# ---------------------------------------------------------------------------
# Loading & normalization
# ---------------------------------------------------------------------------

def load_us_cases(path):
    """Load US cases (already in English, 8-field schema)."""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_cn_cases(path):
    """Load CN cases and normalize to the same schema as US."""
    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f)

    normalized = []
    for c in raw:
        cf = c.get("clinical_facts", {})
        md = c.get("malpractice_details", {})
        om = c.get("organ_system_mapping", {})

        et_raw = md.get("diagnostic_error_type", "Unknown")
        et = CN_ERROR_MAP.get(et_raw, "Unknown")

        sys_raw = om.get("primary_system", "Unknown")
        sys_norm = CN_SYSTEM_MAP.get(sys_raw, None)

        normalized.append({
            "case_metadata": c.get("case_metadata", {}),
            "clinical_facts": cf,
            "organ_system_mapping": {"primary_system": sys_norm or "Unknown"},
            "malpractice_details": {
                "diagnostic_error_type": et,
                "expert_appraisal_summary": md.get("expert_appraisal_summary", "Unknown"),
            },
            "source": "CN",
        })
    return normalized


# ---------------------------------------------------------------------------
# Filtering (Step 2 + 3)
# ---------------------------------------------------------------------------

def is_valid(case):
    """Check if a case has complete clinical data + valid organ system."""
    cf = case.get("clinical_facts", {})
    md = case.get("malpractice_details", {})
    om = case.get("organ_system_mapping", {})

    dx = cf.get("final_correct_diagnosis", "Unknown")
    pt = cf.get("patient_demographics", "Unknown")
    pc = cf.get("primary_complaint", "Unknown")
    et = md.get("diagnostic_error_type", "Unknown")
    sys_name = om.get("primary_system", "Unknown")

    if dx == "Unknown" or dx.startswith("Unknown"):
        return False
    if pt == "Unknown" or pt.startswith("Unknown"):
        return False
    if pc == "Unknown" or pc.startswith("Unknown"):
        return False
    if et not in VALID_ERROR_TYPES:
        return False
    if sys_name not in VALID_SYSTEMS:
        return False
    return True


# ---------------------------------------------------------------------------
# Allocation (Step 4) — proportional by source volume
# ---------------------------------------------------------------------------

def allocate_seats(us_count, cn_count, total_seats):
    """
    Distribute seats proportionally between US and CN.

    Uses the largest remainder method for fair rounding.
    """
    if us_count + cn_count == 0:
        return 0, 0

    us_exact = total_seats * us_count / (us_count + cn_count)
    cn_exact = total_seats * cn_count / (us_count + cn_count)

    us_floor = int(us_exact)
    cn_floor = int(cn_exact)
    remainder = total_seats - us_floor - cn_floor

    # Give the extra seat(s) to whichever has the larger fractional part
    fracs = [("US", us_exact - us_floor), ("CN", cn_exact - cn_floor)]
    fracs.sort(key=lambda x: -x[1])

    us_seats = us_floor
    cn_seats = cn_floor
    for src, _ in fracs[:remainder]:
        if src == "US":
            us_seats += 1
        else:
            cn_seats += 1

    return us_seats, cn_seats


# ---------------------------------------------------------------------------
# Balanced selection (Step 5)
# ---------------------------------------------------------------------------

def select_balanced(candidates, n, seed=42):
    """
    Select n cases from candidates with balanced distribution.

    Balances across:
      - organ systems (8 categories)
      - error types (3 categories)
    """
    random.seed(seed)

    # Group by (system, error_type)
    groups = defaultdict(list)
    for c in candidates:
        s = c["organ_system_mapping"]["primary_system"]
        e = c["malpractice_details"]["diagnostic_error_type"]
        groups[(s, e)].append(c)

    # Shuffle within each group for reproducible randomness
    for key in groups:
        random.shuffle(groups[key])

    selected = []

    # Phase 1: round-robin pick across (system × error_type) cells
    all_keys = list(groups.keys())
    random.shuffle(all_keys)

    idx = 0
    while len(selected) < n:
        progressed = False
        for key in all_keys:
            if len(selected) >= n:
                break
            pool = groups[key]
            if pool:
                selected.append(pool.pop())
                progressed = True
        if not progressed:
            break  # all pools exhausted

    return selected[:n]


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Select the final case set from combined US + CN datasets"
    )
    parser.add_argument("--count", type=int, default=30,
                        help="Number of cases to select (default: 30)")
    parser.add_argument("--seed", type=int, default=42,
                        help="Random seed for reproducibility (default: 42)")
    parser.add_argument("--us-input", default=US_INPUT)
    parser.add_argument("--cn-input", default=CN_INPUT)
    parser.add_argument("--output", default=OUTPUT)
    args = parser.parse_args()

    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    us_path = os.path.join(project_root, args.us_input)
    cn_path = os.path.join(project_root, args.cn_input)
    out_path = os.path.join(project_root, args.output)

    # ---- Step 1: Load ----
    print("=" * 60)
    print("Case Selection — Combined US + CN")
    print("=" * 60)

    us_raw = load_us_cases(us_path)
    print(f"US cases loaded: {len(us_raw)}")

    # Tag US cases with source
    for c in us_raw:
        c.setdefault("source", "US")

    cn_raw = load_cn_cases(cn_path)
    print(f"CN cases loaded: {len(cn_raw)}")

    # ---- Step 2 + 3: Filter + Intersect ----
    us_valid = [c for c in us_raw if is_valid(c)]
    cn_valid = [c for c in cn_raw if is_valid(c)]
    print(f"\nAfter filtering (complete data + valid system):")
    print(f"  US valid: {len(us_valid)}/{len(us_raw)}")
    print(f"  CN valid: {len(cn_valid)}/{len(cn_raw)}")
    print(f"  Total valid: {len(us_valid) + len(cn_valid)}")

    # ---- Step 4: Allocate seats proportionally ----
    us_seats, cn_seats = allocate_seats(len(us_valid), len(cn_valid), args.count)
    print(f"\nProportional allocation (largest remainder method):")
    print(f"  US share: {len(us_valid)}/{len(us_valid)+len(cn_valid)}"
          f" = {len(us_valid)*100/(len(us_valid)+len(cn_valid)):.1f}%"
          f" → {us_seats} seats")
    print(f"  CN share: {len(cn_valid)}/{len(us_valid)+len(cn_valid)}"
          f" = {len(cn_valid)*100/(len(us_valid)+len(cn_valid)):.1f}%"
          f" → {cn_seats} seats")
    print(f"  Total: {us_seats + cn_seats} seats")

    # ---- Step 5: Balanced selection ----
    us_selected = select_balanced(us_valid, us_seats, seed=args.seed)
    cn_selected = select_balanced(cn_valid, cn_seats, seed=args.seed + 1)
    all_selected = us_selected + cn_selected
    random.Random(args.seed).shuffle(all_selected)

    print(f"\nSelected: {len(us_selected)} US + {len(cn_selected)} CN"
          f" = {len(all_selected)} cases")

    # ---- Summary ----
    sys_dist = defaultdict(int)
    et_dist = defaultdict(int)
    src_dist = defaultdict(int)
    for c in all_selected:
        sys_dist[c["organ_system_mapping"]["primary_system"]] += 1
        et_dist[c["malpractice_details"]["diagnostic_error_type"]] += 1
        src_dist[c["source"]] += 1

    print(f"\n{'—' * 40}")
    print("Source distribution:")
    for s in ["US", "CN"]:
        print(f"  {s:<5} {src_dist.get(s, 0):>3}")

    print(f"\nOrgan system distribution:")
    for s in VALID_SYSTEMS:
        print(f"  {s:<20} {sys_dist.get(s, 0):>3}")

    print(f"\nError type distribution:")
    for e in ["misdiagnosis", "missed diagnosis", "delayed diagnosis"]:
        print(f"  {e:<20} {et_dist.get(e, 0):>3}")

    # ---- Step 6: Save ----
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(all_selected, f, indent=2, ensure_ascii=False)
    print(f"\nSaved to: {out_path}")


if __name__ == "__main__":
    main()
