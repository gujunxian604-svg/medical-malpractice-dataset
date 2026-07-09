"""
LLM-based medical case extraction using DeepSeek V3.

This module replaces regex-based extraction with LLM-powered extraction
for precise clinical fact identification from court opinions.

Usage:
    # Extract from raw opinions (requires us_cases.json from extract_us_cases.py)
    python src/extract_with_llm.py

    # Extract with custom input/output
    python src/extract_with_llm.py --input data/us_cases.json --output data/us_cases_llm.json

    # Resume from checkpoint (skips already-extracted cases)
    python src/extract_with_llm.py --resume

Requirements:
    pip install openai
    Set DEEPSEEK_API_KEY in config.py
"""

import os
import sys
import json
import time
import argparse
from typing import Dict, Optional

from openai import OpenAI

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import (
    DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL,
    MAX_OPINION_LENGTH, LLM_TIMEOUT, LLM_MAX_RETRIES,
    US_OUTPUT, US_LLM_OUTPUT,
)

# ============================================================
# Prompt Design
# ============================================================

SYSTEM_PROMPT = """You are a medical-legal data extractor specialized in analyzing court opinions from medical malpractice cases.

Your task: Extract ONLY clinical facts about the patient from the court opinion text. Ignore all legal analysis, procedural history, and legal conclusions.

CRITICAL RULES:
1. Extract information ONLY about the patient/victim, not about the doctors, hospitals, or legal parties.
2. If information is not explicitly stated in the text, write "Unknown".
3. NEVER write "N/A" - always use "Unknown" for missing data.
4. For "primary_system", choose EXACTLY ONE from these 8 options:
   Cardiovascular, Respiratory, Digestive, Neuropsychiatric, Urinary,
   Endocrine, Reproductive, Musculoskeletal. Use "Unknown" if unclear.
5. For "final_correct_diagnosis", use proper medical terminology aligned
   with MeSH vocabulary (e.g., "Acute Myocardial Infarction" not "heart attack").
6. For "diagnostic_error_type", choose ONE: misdiagnosis, missed diagnosis,
   delayed diagnosis, or "Unknown - [explanation]" if the case is not about
   diagnostic error (e.g., informed consent, surgical error).
7. For "expert_appraisal_summary", extract what the court/experts found the
   hospital did wrong medically. Be specific about the medical negligence,
   not the legal disposition.
8. Output ONLY valid JSON, no explanations or markdown.

JSON SCHEMA (fill all fields):
{
  "case_metadata": {
    "title": "Full case title (Appellant v. Appellee) or Unknown",
    "document_type": "Civil Judgment Document or Criminal Judgment Document"
  },
  "clinical_facts": {
    "patient_demographics": "e.g., female, 56 years old. Include age and sex if mentioned. Write Unknown if not stated.",
    "primary_complaint": "The patient's initial symptoms and reason for seeking medical care. Write Unknown if not stated.",
    "misdiagnosed_condition": "What was initially misdiagnosed or missed. If case is not about diagnostic error, write 'Unknown - [brief explanation]'.",
    "final_correct_diagnosis": "The actual confirmed disease (MeSH-aligned). Write Unknown if not stated."
  },
  "organ_system_mapping": {
    "primary_system": "ONE of: Cardiovascular, Respiratory, Digestive, Neuropsychiatric, Urinary, Endocrine, Reproductive, Musculoskeletal, Unknown"
  },
  "malpractice_details": {
    "diagnostic_error_type": "misdiagnosis | missed diagnosis | delayed diagnosis | Unknown - [explanation]",
    "expert_appraisal_summary": "Specific medical negligence findings from the court or experts. Write Unknown if not stated."
  }
}"""

USER_PROMPT_TEMPLATE = """Extract clinical facts from this court opinion. Return ONLY the JSON, no other text.

Court Opinion Text:
---
{opinion_text}
---

Return the JSON now:"""


# ============================================================
# LLM Client
# ============================================================

class LLMExtractor:
    """DeepSeek V3-powered medical case extractor."""

    def __init__(self, api_key=None, base_url=None, model=None):
        self.api_key = api_key or DEEPSEEK_API_KEY
        self.base_url = base_url or DEEPSEEK_BASE_URL
        self.model = model or DEEPSEEK_MODEL
        self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)
        self.total_input_tokens = 0
        self.total_output_tokens = 0

    def extract(self, opinion_text: str, case_title: str = None) -> Optional[Dict]:
        """
        Extract structured medical data from opinion text.

        Args:
            opinion_text: Raw court opinion text
            case_title: Optional case title hint from API metadata

        Returns:
            Dict matching the 8-field JSON schema, or None on failure
        """
        # Truncate if too long
        if len(opinion_text) > MAX_OPINION_LENGTH:
            opinion_text = opinion_text[:MAX_OPINION_LENGTH] + "\n[...truncated...]"
            print(f"  WARNING: Truncated to {MAX_OPINION_LENGTH} chars")

        user_prompt = USER_PROMPT_TEMPLATE.format(opinion_text=opinion_text)

        for attempt in range(LLM_MAX_RETRIES):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": user_prompt},
                    ],
                    response_format={"type": "json_object"},
                    temperature=0.1,  # low temperature for consistency
                    max_tokens=2000,
                    timeout=LLM_TIMEOUT,
                )

                # Track token usage
                usage = response.usage
                self.total_input_tokens += usage.prompt_tokens
                self.total_output_tokens += usage.completion_tokens

                # Parse JSON response
                content = response.choices[0].message.content
                result = json.loads(content)

                # Use API-provided title if LLM didn't extract it well
                if case_title and (not result.get("case_metadata", {}).get("title")
                                   or result["case_metadata"]["title"] == "Unknown"):
                    result["case_metadata"]["title"] = case_title

                # Validate schema
                validated = self._validate_schema(result)
                return validated

            except json.JSONDecodeError as e:
                print(f"  JSON parse error (attempt {attempt+1}): {e}")
                if attempt < LLM_MAX_RETRIES - 1:
                    time.sleep(3)
            except Exception as e:
                print(f"  API error (attempt {attempt+1}): {e}")
                if attempt < LLM_MAX_RETRIES - 1:
                    time.sleep(5)

        print(f"  FAILED after {LLM_MAX_RETRIES} attempts")
        return None

    def _validate_schema(self, data: Dict) -> Dict:
        """Validate and fix the JSON schema to ensure all 8 fields exist."""
        valid_systems = {
            "Cardiovascular", "Respiratory", "Digestive", "Neuropsychiatric",
            "Urinary", "Endocrine", "Reproductive", "Musculoskeletal", "Unknown",
        }

        # Ensure structure
        data.setdefault("case_metadata", {})
        data.setdefault("clinical_facts", {})
        data.setdefault("organ_system_mapping", {})
        data.setdefault("malpractice_details", {})

        data["case_metadata"].setdefault("title", "Unknown")
        data["case_metadata"].setdefault("document_type", "Civil Judgment Document")

        data["clinical_facts"].setdefault("patient_demographics", "Unknown")
        data["clinical_facts"].setdefault("primary_complaint", "Unknown")
        data["clinical_facts"].setdefault("misdiagnosed_condition", "Unknown")
        data["clinical_facts"].setdefault("final_correct_diagnosis", "Unknown")

        data["organ_system_mapping"].setdefault("primary_system", "Unknown")

        data["malpractice_details"].setdefault("diagnostic_error_type", "Unknown")
        data["malpractice_details"].setdefault("expert_appraisal_summary", "Unknown")

        # Validate primary_system
        system = data["organ_system_mapping"]["primary_system"]
        if system not in valid_systems:
            print(f"  WARNING: Invalid primary_system '{system}', setting to Unknown")
            data["organ_system_mapping"]["primary_system"] = "Unknown"

        # Replace any "N/A" with "Unknown"
        for section in data.values():
            if isinstance(section, dict):
                for key, val in section.items():
                    if isinstance(val, str) and val.strip().upper() in ("N/A", "NA", ""):
                        section[key] = "Unknown"

        return data

    def get_cost_estimate(self) -> str:
        """Estimate cost based on token usage."""
        input_cost = self.total_input_tokens / 1_000_000 * 0.5
        output_cost = self.total_output_tokens / 1_000_000 * 1.5
        total = input_cost + output_cost
        return (f"Tokens: {self.total_input_tokens:,} in + "
                f"{self.total_output_tokens:,} out | "
                f"Est. cost: CNY {total:.2f}")


# ============================================================
# Main Processing
# ============================================================

def process_cases(input_path: str, output_path: str, resume: bool = False):
    """
    Process all cases in the input JSON file with LLM extraction.

    Args:
        input_path: Path to us_cases.json (regex-extracted, has full_text)
        output_path: Path to save LLM-extracted cases
        resume: If True, skip cases already in output file
    """
    # Load input cases
    with open(input_path, "r", encoding="utf-8") as f:
        cases = json.load(f)

    if not isinstance(cases, list):
        cases = [cases]

    print(f"Loaded {len(cases)} cases from {input_path}")

    # Load existing results if resuming
    results = []
    processed_ids = set()
    if resume and os.path.exists(output_path):
        with open(output_path, "r", encoding="utf-8") as f:
            results = json.load(f)
            for r in results:
                if r.get("api_metadata", {}).get("cluster_id"):
                    processed_ids.add(r["api_metadata"]["cluster_id"])
        print(f"Resuming: {len(processed_ids)} cases already processed")

    # Initialize LLM extractor
    extractor = LLMExtractor()

    print(f"\nExtracting with DeepSeek V3...")
    print(f"Output: {output_path}\n")

    success = 0
    failed = 0

    for i, case in enumerate(cases, 1):
        cluster_id = case.get("api_metadata", {}).get("cluster_id", f"idx_{i}")

        # Skip if already processed
        if cluster_id in processed_ids:
            continue

        title = case.get("case_metadata", {}).get("title", "Unknown")
        print(f"[{i}/{len(cases)}] {title[:65]}")

        # Get opinion text - check if we stored full_text
        opinion_text = case.get("full_text", "")
        if not opinion_text:
            # If no full_text, reconstruct from fields (shouldn't happen with proper pipeline)
            print("  WARNING: No full_text field, skipping")
            failed += 1
            continue

        # Extract with LLM
        result = extractor.extract(opinion_text, case_title=title)

        if result:
            # Preserve API metadata
            result["api_metadata"] = case.get("api_metadata", {})
            result["source_url"] = case.get("source_url", "")
            results.append(result)
            success += 1
            print(f"  Patient: {result['clinical_facts']['patient_demographics'][:50]}")
            print(f"  Final Dx: {result['clinical_facts']['final_correct_diagnosis'][:50]}")
            print(f"  System: {result['organ_system_mapping']['primary_system']}")
        else:
            failed += 1

        # Save checkpoint every 10 cases
        if i % 10 == 0:
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
            print(f"  [Checkpoint] Saved {len(results)} cases | {extractor.get_cost_estimate()}")

        # Rate limit (DeepSeek has generous limits, but be polite)
        if i < len(cases):
            time.sleep(1)

    # Final save
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"\n{'='*55}")
    print(f"DONE: {success} extracted, {failed} failed")
    print(f"Total in file: {len(results)}")
    print(f"Cost: {extractor.get_cost_estimate()}")
    print(f"Output: {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description="LLM-based medical case extraction (DeepSeek V3)"
    )
    parser.add_argument("--input", default=US_OUTPUT,
                        help=f"Input file with opinion texts (default: {US_OUTPUT})")
    parser.add_argument("--output", default=US_LLM_OUTPUT,
                        help=f"Output file (default: {US_LLM_OUTPUT})")
    parser.add_argument("--resume", action="store_true",
                        help="Skip cases already in output file")
    args = parser.parse_args()

    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    input_path = os.path.join(project_root, args.input)
    output_path = os.path.join(project_root, args.output)

    if not os.path.exists(input_path):
        print(f"ERROR: Input file not found: {input_path}")
        print("Run `python src/extract_us_cases.py` first to download opinions.")
        sys.exit(1)

    process_cases(input_path, output_path, resume=args.resume)


if __name__ == "__main__":
    main()
