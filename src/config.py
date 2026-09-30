DEBUG_MODE = False
DEBUG_MAX_PAGES = 3
LIMIT_BLEDOW = 3
LINKS_FILE = "project_links.txt"
OUTPUT_FILE = "data/mapadotacji_wyniki.jsonl"
MAX_WORKERS = 12

BASE_URL = "https://mapadotacji.gov.pl"
UNKNOWN_ID_FLAG = "BRAK_ID"
UNKNOWN_TITLE_FLAG = "BRAK_TYTULU"
UNKNOWN_LINK_FLAG = "BRAK_LINKU"

#scraper.py
DEFAULT_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/102.0.0.0 Safari/537.36'
}
DEFAULT_TIMEOUT_DURATION = 15.0
DEFAULT_CONNECT_DURATION = 15.0
DEFAULT_MAX_RETRIES = 3
DEFAULT_DELAY_DURATION = 2.0

#models.py
INVALID_PROJECT_ERROR_MESSAGE = "Odrzucono model: Wykryto brak ID oraz tytułu jednocześnie."

#main.py
POLITE_BASE_DELAY = 0.5
POLITE_JITTER_MAX = 1.0