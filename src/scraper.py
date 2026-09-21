import logging
from typing import Any
from src.config import DEFAULT_HEADERS, DEFAULT_TIMEOUT_DURATION, DEFAULT_CONNECT_DURATION, DEFAULT_MAX_RETRIES, DEFAULT_DELAY_DURATION
import httpx
import time

logger = logging.getLogger(__name__)

class MapadotacjiScraper:
    def __init__(self, storage_manager):
        #klasa sama nie otwiera pliku, tylko dostaje gotowy obiekt storage
        self.storage = storage_manager

        timeout = httpx.Timeout(DEFAULT_TIMEOUT_DURATION, connect=DEFAULT_CONNECT_DURATION)

        self.client = httpx.Client(headers=DEFAULT_HEADERS, timeout=timeout, http2=True)

        logger.info("Zainicjalizowano MapadotacjiScraper")

    def fetch_html(self, url: str) -> str:
        #pobiera kod HTML z danego url
        for attempt in range(1, DEFAULT_MAX_RETRIES + 1):
            try:
                logger.debug(f"Pobieranie {attempt}/{DEFAULT_MAX_RETRIES} dla {url}")
                response = self.client.get(url)
                #wyjątek jeśli zły status http
                response.raise_for_status()
                return response.text
            except (httpx.TimeoutException, httpx.HTTPStatusError, httpx.NetworkError) as e:
                logger.warning(f"Błąd sieci podczas pobierania nr {attempt} dla {url}: {e}")

                if attempt == DEFAULT_MAX_RETRIES:
                    logger.error(f"Wyczerpano limit prób dla {url}")
                    raise
            #czas oczekiwania
            time.sleep(DEFAULT_DELAY_DURATION)
        raise RuntimeError("Nieoczekiwany błąd pętli fetch_html")


#TESTOWANIE
if __name__ == "__main__":
    from src.models import ProjectDetails
    from src.parsers import parse_project_details
    from src.storage import JsonlStorage

    storage = JsonlStorage("test_dane.jsonl")
    scraper = MapadotacjiScraper(storage_manager=storage)

    logger.info("Testowanie scrapera")
    test_urls = [
        "https://mapadotacji.gov.pl/projekty/746927/"
    ]

    try:
        for url in test_urls:
            pobrany_html = scraper.fetch_html(url)
            print(pobrany_html[:1000]) #już nie będziemy wszystkiego tu wypisywać
    except Exception as e:
        print(f"Wystąpił błąd {e}")