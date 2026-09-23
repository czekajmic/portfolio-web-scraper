import logging
import sys
from src.storage import JsonlStorage, ProgressTracker
from src.scraper import MapadotacjiScraper
from src.parsers import extract_project_links
from src.config import BASE_URL
import time
import concurrent.futures

MAX_WORKERS = 5


def run_crawler(max_pages: int = 2):
    logger = logging.getLogger(__name__)
    logger.info("Crawler rozpoczął pracę")

    tracker = ProgressTracker(file_path="visited_urls.txt")

    with JsonlStorage("mapadotacji_wyniki.jsonl") as storage, MapadotacjiScraper(storage_manager=storage) as scraper:

        #wyodrębniona funkcja-worker do wywoływania na wielu wątkach
        def _process_single_url(url: str, i: int, total_urls: int) -> None:
            if tracker.is_visited(url):
                logger.debug(f"Pominięto {url}, już odwiedzony")
                return
            
            logger.debug(f"Pobieranie projektu {i}/{total_urls} ze strony {url}")
            
            czy_sukces = scraper.process_project(url)
            if czy_sukces:
                tracker.mark_visited(url)


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

                total_projects = len(project_urls)
                page_pelen_sukces = True

                # otwieramy pulę wątków
                with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
                    #słownik, pozwala zidentyfikować po obiekcie future co się zepsuło
                    future_to_url = {
                        executor.submit(_process_single_url, url, i, total_projects): url for i, url in enumerate(project_urls, start=1)
                    }

                    for future in concurrent.futures.as_completed(future_to_url):
                        current_url = future_to_url[future]
                        try:
                            future.result() #blokuje wątek póki się nie skończy, a jeśli błąd to będzie wyrzucony tutaj
                        except Exception as e:
                            logger.error(f"Worker pracujący nad {current_url} napotkał błąd: {e}", exc_info=True)
                            page_pelen_sukces = False
                if page_pelen_sukces:
                    tracker.mark_search_page_visited(page_num)
                    logger.info(f"Strona {page_num} pomyślnie oznaczona jako przetworzona")
                else:
                    logger.warning(f"Strona {page_num} zakończyła się z błędami w workerach. Nie zapisano jej jako ukończonej.")
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

    run_crawler(max_pages=7)