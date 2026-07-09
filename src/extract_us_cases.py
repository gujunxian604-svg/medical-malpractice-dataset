"""
Extract US medical malpractice cases from CourtListener API.

Search strategy (aligned with reference pipeline):
  Query: ("medical malpractice" OR "malpractice") AND
         (civil OR "personal injury" OR "wrongful death") AND
         dateFiled:[DATE_FROM TO DATE_TO]
  Dedup: by cluster_id (one case may have multiple opinion entries)

Usage:
    python extract_us_cases.py                        # Default search
    python extract_us_cases.py --append               # Add to existing data
    python extract_us_cases.py --count 100            # Fetch up to 100 cases
    python extract_us_cases.py --query "custom query" # Custom search query

Requirements:
    pip install requests
    Set API keys in config.py
"""

import os
import sys
import json
import time
import argparse
import requests

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import (
    COURTLISTENER_API_KEYS, SEARCH_QUERY, DATE_FROM, DATE_TO,
    MAX_CASES, REQUEST_DELAY, API_BASE, US_OUTPUT,
)
from extract_fields import parse_opinion_to_json


class CourtListenerAPI:
    """CourtListener REST API v4 client with automatic key rotation."""

    def __init__(self, keys):
        self.keys = keys
        self.key_index = 0

    @property
    def current_key(self):
        return self.keys[self.key_index]

    def _rotate_key(self):
        self.key_index = (self.key_index + 1) % len(self.keys)
        print(f"  Switched to API key #{self.key_index + 1}")

    def _headers(self):
        return {
            "Authorization": f"Token {self.current_key}",
            "Accept": "application/json",
        }

    def search(self, query, count=100, page_size=20):
        """
        Search for opinions using Lucene query syntax.

        The date range should be embedded in the query string using:
            dateFiled:[YYYY-MM-DD TO YYYY-MM-DD]

        Results are deduplicated by cluster_id.
        Note: CourtListener search API caps page_size at 20.
        """
        params = {"q": query, "type": "o", "page_size": min(page_size, 20)}
        results = []
        url = f"{API_BASE}/search/"
        page = 1

        while url and len(results) < count:
            print(f"  Searching page {page}...")

            if page == 1:
                resp = self._request(url, params=params)
            else:
                resp = self._request(url)  # next URL already has query params

            if not resp:
                break

            data = resp.json()
            batch = data.get("results", [])
            total = data.get("count", 0)
            print(f"  Total matches: {total}, page got {len(batch)}, "
                  f"accumulated {len(results)}")

            results.extend(batch)

            url = data.get("next")
            page += 1

            if url and len(results) < count:
                time.sleep(REQUEST_DELAY)

        # Deduplicate by cluster_id (one case may have multiple opinion entries)
        seen = set()
        unique = []
        for r in results[:count]:
            key = r.get("cluster_id") or r.get("id")
            if key and key not in seen:
                seen.add(key)
                unique.append(r)

        print(f"  Deduplicated: {len(results)} → {len(unique)} unique cases")
        return unique

    def get_opinion_text(self, opinion_id):
        """Get the full plain text of an opinion by ID."""
        print(f"  Fetching opinion {opinion_id}...")
        resp = self._request(f"{API_BASE}/opinions/{opinion_id}/")
        if not resp:
            return None, None

        data = resp.json()
        text = data.get("plain_text", "")
        cluster_id = data.get("cluster_id")

        # Clean HTML entities and tags
        if text:
            import re
            text = text.replace("&amp;", "&").replace("&lt;", "<")
            text = text.replace("&gt;", ">").replace("&quot;", '"')
            text = text.replace("&#x27;", "'").replace("&#39;", "'")
            text = re.sub(r"<[^>]+>", "", text)

        return text, cluster_id

    def _request(self, url, params=None, max_retries=5):
        """Make a request with retry and key rotation on rate limit."""
        for attempt in range(max_retries):
            resp = requests.get(url, params=params,
                                headers=self._headers(), timeout=60)
            if resp.status_code == 429:
                print(f"  Rate limited (attempt {attempt + 1}/{max_retries})")
                self._rotate_key()
                # Wait 120s on rate limit to fully reset the window
                wait_time = 120 if attempt < max_retries - 1 else 60
                print(f"  Waiting {wait_time}s for rate limit reset...")
                time.sleep(wait_time)
                continue
            resp.raise_for_status()
            return resp
        resp.raise_for_status()
        return resp


def build_search_query(date_from, date_to):
    """
    Build the Lucene search query (aligned with reference pipeline).

    Query: ("medical malpractice" OR "malpractice") AND
           (civil OR "personal injury" OR "wrongful death") AND
           dateFiled:[date_from TO date_to]
    """
    return (
        f'("medical malpractice" OR "malpractice") AND '
        f'(civil OR "personal injury" OR "wrongful death") AND '
        f'dateFiled:[{date_from} TO {date_to}]'
    )


def search_result_to_case(api, search_result):
    """Convert a search result to the medical JSON schema."""
    opinions = search_result.get("opinions", [])
    if not opinions:
        print("  No opinion available, skipping")
        return None

    opinion_id = opinions[0].get("id")
    if not opinion_id:
        print("  No opinion ID, skipping")
        return None

    full_text, _ = api.get_opinion_text(opinion_id)
    if not full_text or len(full_text) < 500:
        print("  No sufficient full text, skipping")
        return None

    case_title = search_result.get("caseName", "")
    url = search_result.get("absolute_url", "")
    case = parse_opinion_to_json(full_text, case_title=case_title, source_url=url)

    # Add API metadata for traceability
    case["api_metadata"] = {
        "cluster_id": search_result.get("cluster_id"),
        "docket_number": search_result.get("docketNumber", ""),
        "court": search_result.get("court", ""),
        "date_filed": search_result.get("dateFiled", ""),
        "citation": search_result.get("citation", []),
    }

    # Save full opinion text for LLM re-extraction
    case["full_text"] = full_text

    # Use syllabus as appraisal summary if extraction failed
    syllabus = search_result.get("syllabus", "")
    if syllabus and len(syllabus) > 50:
        existing = case["malpractice_details"]["expert_appraisal_summary"]
        if existing == "Unknown" or len(existing) < 50:
            case["malpractice_details"]["expert_appraisal_summary"] = syllabus

    return case


def main():
    parser = argparse.ArgumentParser(
        description="Extract US medical malpractice cases from CourtListener API"
    )
    parser.add_argument("--count", type=int, default=MAX_CASES,
                        help=f"Max cases to fetch (default: {MAX_CASES})")
    parser.add_argument("--append", action="store_true",
                        help="Add to existing data instead of overwriting")
    parser.add_argument("--output", default=US_OUTPUT,
                        help=f"Output file (default: {US_OUTPUT})")
    parser.add_argument("--query", default=None,
                        help="Custom Lucene query (overrides default)")
    args = parser.parse_args()

    # Build search query
    query = args.query if args.query else build_search_query(DATE_FROM, DATE_TO)

    # Resolve output path relative to project root
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    output_path = os.path.join(project_root, args.output)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    print(f"Search query: {query}")
    print(f"Target count: {args.count}")
    print(f"Output: {output_path}")
    print(f"Mode: {'APPEND' if args.append else 'OVERWRITE'}")
    print()

    # Load existing cases if append mode
    all_cases = []
    done_cluster_ids = set()
    if args.append and os.path.exists(output_path):
        with open(output_path, "r", encoding="utf-8") as f:
            existing = json.load(f)
            if isinstance(existing, list):
                all_cases = existing
                for c in all_cases:
                    cid = c.get("api_metadata", {}).get("cluster_id")
                    if cid:
                        done_cluster_ids.add(cid)
                print(f"Loaded {len(all_cases)} existing cases, "
                      f"{len(done_cluster_ids)} already done")

    # Initialize API client
    api = CourtListenerAPI(COURTLISTENER_API_KEYS)

    # Search
    print(f"\nSearching CourtListener...")
    search_results = api.search(query, count=args.count)
    print(f"\nGot {len(search_results)} unique cases. Fetching full texts...\n")

    # Extract each case
    success = 0
    skipped_existing = 0
    for i, sr in enumerate(search_results, 1):
        # Skip if already downloaded
        cluster_id = sr.get("cluster_id")
        if cluster_id and cluster_id in done_cluster_ids:
            skipped_existing += 1
            continue

        case_name = sr.get("caseName", "Unknown")
        print(f"[{i}/{len(search_results)}] {case_name[:70]}")

        try:
            case = search_result_to_case(api, sr)
            if case:
                all_cases.append(case)
                success += 1
                print(f"  Patient: {case['clinical_facts']['patient_demographics']}")
                print(f"  Final Dx: {case['clinical_facts']['final_correct_diagnosis']}")
                print(f"  System: {case['organ_system_mapping']['primary_system']}")
            else:
                print("  Skipped (no opinion text)")
        except Exception as e:
            print(f"  ERROR: {e}")

        if i < len(search_results):
            time.sleep(REQUEST_DELAY)

        # Incremental save every 10 cases (crash protection)
        if (success + skipped_existing) % 10 == 0:
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(all_cases, f, indent=2, ensure_ascii=False)
            print(f"  [Checkpoint] Saved {len(all_cases)} cases to file")

    print(f"\nSkipped {skipped_existing} already-downloaded cases")

    # Final save
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(all_cases, f, indent=2, ensure_ascii=False)

    print(f"{'=' * 50}")
    print(f"DONE: {success}/{len(search_results)} cases extracted")
    print(f"Total cases in file: {len(all_cases)}")
    print(f"Output: {output_path}")


if __name__ == "__main__":
    main()
