import logging
import sys
from src.storage import JsonlStorage, ProgressTracker
from src.scraper import MapadotacjiScraper
from src.parsers import extract_project_links
from src.config import BASE_URL
import time


def run_crawler(max_pages: int = 2):
    logger = logging.getLogger(__name__)
    logger.info("Crawler rozpoczął pracę")

    tracker = ProgressTracker(file_path="visited_urls.txt")

    with JsonlStorage("mapadotacji_wyniki.jsonl") as storage, MapadotacjiScraper(storage_manager=storage) as scraper:
        for page_num in range(1, max_pages+1):
            if tracker.is_search_page_visited(page_num):
                logger.debug(f"Pomijam stronę {page_num}, ta strona została już zebrana")
                continue

            page_url = f"{BASE_URL}/projekty/?page_no={page_num}"
            logger.info(f"Przeszukiwanie strony {page_url}")
            try:
                search_page_html = scraper.fetch_html(page_url)
                project_urls = extract_project_links(search_page_html, base_url=BASE_URL)
                if not project_urls:
                    logger.warning(f"Nie znaleziono żadnych linków na stronie {page_url}")
                    break
                logger.info(f"Znaleziono {len(project_urls)} projektów na stronie {page_url}")

                for i, url in enumerate(project_urls, start=1):
                    if tracker.is_visited(url):
                        logger.debug(f"Pominięto {url}, już odwiedzony")
                        continue

                    logger.debug(f"Pobieranie projektu {i}/{len(project_urls)} ze strony {page_url}")

                    czy_sukces = scraper.process_project(url)
                    if czy_sukces:
                        tracker.mark_visited(url)
                    time.sleep(1.0)
                tracker.mark_search_page_visited(page_num)
                logger.info(f"Strona {page_num} pomyślnie oznaczona jako przetworzona")
            except Exception as e:
                logger.error(f"Błąd podczas crawlingu strony {page_url}: {e}")
                continue
            time.sleep(1.0)
    logger.info("Zakończono pracę crawlera")

            

###########

if __name__ == "__main__":
    log_format = "%(asctime)s - %(levelname)s - %(name)s - %(message)s"
    logging.basicConfig(
        level=logging.DEBUG,
        format=log_format,
        handlers=[
            logging.FileHandler("main_debug.log", encoding="utf-8", mode="a"),
            logging.StreamHandler(sys.stdout)
        ]
        )
    #mamy level logów jako debug, ale wyciszamy zewnętrzne biblioteki
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("hpack").setLevel(logging.WARNING)

    run_crawler(max_pages=4)