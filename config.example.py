# ============================================================
# Example configuration — copy to config.py and fill in keys
# ============================================================

# CourtListener API (free, 5 req/min per key)
# Get tokens: https://www.courtlistener.com/profile/api-token/
COURTLISTENER_API_KEYS = [
    "YOUR_KEY_1",
    "YOUR_KEY_2",
]

# DeepSeek API (LLM extraction, ~$0.002/case)
# Get key: https://platform.deepseek.com/
DEEPSEEK_API_KEY = "YOUR_DEEPSEEK_KEY"
DEEPSEEK_BASE_URL = "https://api.deepseek.com/v1"
DEEPSEEK_MODEL = "deepseek-chat"  # DeepSeek V3

# ============================================================
# Search Configuration
# ============================================================
DATE_FROM = "2025-01-01"
DATE_TO = "2026-01-01"
SEARCH_QUERY = (
    '("medical malpractice" OR "malpractice") AND '
    '(civil OR "personal injury" OR "wrongful death") AND '
    f'dateFiled:[{DATE_FROM} TO {DATE_TO}]'
)
MAX_CASES = 500

# Request interval (seconds)
REQUEST_DELAY = 5
API_BASE = "https://www.courtlistener.com/api/rest/v4"

# ============================================================
# LLM Extraction
# ============================================================
MAX_OPINION_LENGTH = 30000
LLM_TIMEOUT = 120
LLM_MAX_RETRIES = 3

# ============================================================
# Output Paths
# ============================================================
US_RAW_OUTPUT = "data/us_cases.json"
US_LLM_OUTPUT = "data/us_cases_llm.json"
SELECTED_OUTPUT = "data/selected_cases.json"
