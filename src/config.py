DEBUG_MODE = True
DEBUG_MAX_PAGES = 10
LIMIT_BLEDOW = 3
LINKS_FILE = "project_links.txt"

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