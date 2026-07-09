"""
Hybrid downloader: Uses CourtListener API for search, then downloads
PDFs directly from court websites (download_url) to avoid API rate limits.

Strategy:
  1. Search via API (41 pages, ~41 API calls)
  2. Download full text from court PDFs (0 API calls, no rate limit)
  3. Fallback to API for cases without download_url

Usage:
    python src/download_hybrid.py --count 500
    python src/download_hybrid.py --append  # resume from checkpoint
"""

import os
import sys
import json
import time
import argparse
import requests
import io

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import (
    COURTLISTENER_API_KEYS, DATE_FROM, DATE_TO,
    REQUEST_DELAY, API_BASE, US_OUTPUT, MAX_CASES,
)
from extract_fields import parse_opinion_to_json

try:
    import fitz  # PyMuPDF for PDF text extraction
    HAS_FITZ = True
except ImportError:
    HAS_FITZ = False


class HybridDownloader:
    """Download cases: API search + direct PDF download."""

    def __init__(self):
        self.keys = list(COURTLISTENER_API_KEYS)
        self.key_idx = 0
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "MedicalResearchBot/1.0 (academic research)"
        })

    @property
    def current_key(self):
        return self.keys[self.key_idx]

    def _rotate_key(self):
        self.key_idx = (self.key_idx + 1) % len(self.keys)

    def _api_headers(self):
        return {
            "Authorization": f"Token {self.current_key}",
            "Accept": "application/json",
        }

    def search(self, query, count=500):
        """Search via API with pagination and dedup."""
        params = {"q": query, "type": "o", "page_size": 20}
        results = []
        url = f"{API_BASE}/search/"
        page = 1

        while url and len(results) < count:
            print(f"  Search page {page}...")

            if page == 1:
                resp = self._api_request(url, params=params)
            else:
                resp = self._api_request(url)

            if not resp:
                break

            data = resp.json()
            batch = data.get("results", [])
            total = data.get("count", 0)
            print(f"    Total: {total}, page: {len(batch)}, accumulated: {len(results)}")

            results.extend(batch)
            url = data.get("next")
            page += 1
            if url and len(results) < count:
                time.sleep(REQUEST_DELAY)

        # Dedup by cluster_id
        seen = set()
        unique = []
        for r in results[:count]:
            key = r.get("cluster_id") or r.get("id")
            if key and key not in seen:
                seen.add(key)
                unique.append(r)

        print(f"  Deduplicated: {len(results)} -> {len(unique)} unique cases")
        return unique

    def _api_request(self, url, params=None, max_retries=9):
        """API request with proactive key rotation to distribute load."""
        for attempt in range(max_retries):
            # Proactively rotate key each attempt to spread load across 9 keys
            if attempt > 0:
                self._rotate_key()
            resp = requests.get(url, params=params,
                                headers=self._api_headers(), timeout=60)
            if resp.status_code == 429:
                print(f"    Rate limited on key #{self.key_idx+1}, "
                      f"rotating + 30s wait (attempt {attempt+1}/{max_retries})")
                time.sleep(30)
                continue
            resp.raise_for_status()
            return resp
        return None

    def get_full_text(self, search_result):
        """
        Get full opinion text. Try methods in order:
        1. Download PDF from court website (no API rate limit)
        2. Fetch via API (uses rate limit quota)
        """
        # Method 1: Download PDF directly from court website
        opinions = search_result.get("opinions", [])
        for op in opinions:
            if not isinstance(op, dict):
                continue
            download_url = op.get("download_url", "")
            if download_url and download_url.startswith("http"):
                text = self._download_pdf_text(download_url)
                if text and len(text) >= 500:
                    return text, "pdf_download"

        # Method 2: Try snippet from search result
        for op in opinions:
            if not isinstance(op, dict):
                continue
            snippet = op.get("snippet", "")
            if snippet and len(snippet) >= 500:
                # Snippet is too short for good extraction, but better than nothing
                pass

        # Method 3: API fallback (uses rate limit)
        for op in opinions:
            if not isinstance(op, dict):
                continue
            op_id = op.get("id")
            if op_id:
                text = self._get_opinion_via_api(op_id)
                if text and len(text) >= 500:
                    return text, "api"

        # Method 4: Use syllabus + snippet as fallback
        fallback_parts = [
            search_result.get("caseName", ""),
            search_result.get("syllabus", ""),
        ]
        for op in opinions:
            if isinstance(op, dict):
                fallback_parts.append(op.get("snippet", ""))
        fallback_text = " ".join(p for p in fallback_parts if p)
        if len(fallback_text) >= 200:
            return fallback_text, "fallback"

        return None, None

    def _download_pdf_text(self, url):
        """Download PDF from court website and extract text (no API limit)."""
        try:
            resp = self.session.get(url, timeout=60)
            if resp.status_code != 200:
                return None
            content_type = resp.headers.get("content-type", "").lower()
            if "pdf" not in content_type and not url.lower().endswith(".pdf"):
                return None
            if not HAS_FITZ:
                print(f"    (PyMuPDF not installed, can't parse PDF)")
                return None
            pdf_buffer = io.BytesIO(resp.content)
            doc = fitz.open(stream=pdf_buffer, filetype="pdf")
            text = ""
            for page in doc:
                text += page.get_text()
            doc.close()
            # Clean HTML entities
            import re
            text = text.replace("&amp;", "&").replace("&lt;", "<")
            text = text.replace("&gt;", ">").replace("&quot;", '"')
            text = re.sub(r"<[^>]+>", "", text)
            return text.strip()
        except Exception as e:
            print(f"    PDF download error: {e}")
            return None

    def _get_opinion_via_api(self, opinion_id):
        """Get opinion text via API (uses rate limit quota)."""
        try:
            resp = self._api_request(f"{API_BASE}/opinions/{opinion_id}/")
            if not resp:
                return None
            data = resp.json()
            text = data.get("plain_text", "")
            import re
            if text:
                text = text.replace("&amp;", "&").replace("&lt;", "<")
                text = text.replace("&gt;", ">").replace("&quot;", '"')
                text = re.sub(r"<[^>]+>", "", text)
            return text
        except Exception:
            return None


def process(search_results, downloader, existing_cases, done_ids):
    """Process search results into cases."""
    all_cases = list(existing_cases)
    success = 0
    pdf_count = 0
    api_count = 0
    fallback_count = 0
    skipped = 0

    for i, sr in enumerate(search_results, 1):
        cluster_id = sr.get("cluster_id")
        if cluster_id and cluster_id in done_ids:
            skipped += 1
            continue

        case_name = sr.get("caseName", "Unknown")
        print(f"[{i}/{len(search_results)}] {case_name[:65]}")

        try:
            full_text, method = downloader.get_full_text(sr)
            if full_text and len(full_text) >= 200:
                case_title = sr.get("caseName", "")
                url = sr.get("absolute_url", "")
                case = parse_opinion_to_json(full_text, case_title=case_title, source_url=url)
                case["api_metadata"] = {
                    "cluster_id": cluster_id,
                    "docket_number": sr.get("docketNumber", ""),
                    "court": sr.get("court", ""),
                    "date_filed": sr.get("dateFiled", ""),
                    "citation": sr.get("citation", []),
                }
                case["full_text"] = full_text
                case["download_method"] = method

                all_cases.append(case)
                success += 1
                if method == "pdf_download":
                    pdf_count += 1
                elif method == "api":
                    api_count += 1
                else:
                    fallback_count += 1

                print(f"  [{method}] Patient: {case['clinical_facts']['patient_demographics'][:40]}")
                print(f"  Final Dx: {case['clinical_facts']['final_correct_diagnosis'][:50]}")
            else:
                print(f"  Skipped (no text available)")
        except Exception as e:
            print(f"  ERROR: {e}")

        # Incremental save every 10 cases
        processed = success + skipped
        if processed % 10 == 0:
            yield all_cases, True
            print(f"  [Checkpoint] {len(all_cases)} cases saved")

        # Only delay for API calls (PDF downloads don't use API)
        if method == "api" and i < len(search_results):
            time.sleep(REQUEST_DELAY)
        elif method == "pdf_download" and i < len(search_results):
            time.sleep(2)  # Be polite to court servers, but much faster

    yield all_cases, False
    print(f"\nStats: {success} success ({pdf_count} PDF, {api_count} API, {fallback_count} fallback), {skipped} skipped")


def main():
    parser = argparse.ArgumentParser(description="Hybrid downloader (API + PDF)")
    parser.add_argument("--count", type=int, default=MAX_CASES)
    parser.add_argument("--append", action="store_true")
    parser.add_argument("--output", default=US_OUTPUT)
    args = parser.parse_args()

    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    output_path = os.path.join(project_root, args.output)

    # Build query
    query = (
        f'("medical malpractice" OR "malpractice") AND '
        f'(civil OR "personal injury" OR "wrongful death") AND '
        f'dateFiled:[{DATE_FROM} TO {DATE_TO}]'
    )

    print(f"Query: {query}")
    print(f"Output: {output_path}")
    print(f"Mode: {'APPEND' if args.append else 'OVERWRITE'}")
    print()

    # Load existing cases
    all_cases = []
    done_ids = set()
    if args.append and os.path.exists(output_path):
        with open(output_path, "r", encoding="utf-8") as f:
            existing = json.load(f)
            if isinstance(existing, list):
                all_cases = existing
                for c in all_cases:
                    cid = c.get("api_metadata", {}).get("cluster_id")
                    if cid:
                        done_ids.add(cid)
                print(f"Loaded {len(all_cases)} existing cases, {len(done_ids)} done")

    downloader = HybridDownloader()

    # Step 1: Search
    print("\nSearching CourtListener API...")
    search_results = downloader.search(query, count=args.count)
    print(f"\n{len(search_results)} unique cases to process\n")

    # Step 2: Download full texts (PDF first, API fallback)
    print("Downloading full texts (PDF direct + API fallback)...\n")

    for cases, is_checkpoint in process(search_results, downloader, all_cases, done_ids):
        all_cases = cases
        if is_checkpoint:
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(all_cases, f, indent=2, ensure_ascii=False)

    # Final save
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(all_cases, f, indent=2, ensure_ascii=False)

    print(f"\n{'='*50}")
    print(f"DONE: {len(all_cases)} total cases in file")
    print(f"Output: {output_path}")


if __name__ == "__main__":
    main()
