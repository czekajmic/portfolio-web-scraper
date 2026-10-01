import logging
import sys
from src.storage import JsonlStorage, ProgressTracker
from src.scraper import MapadotacjiScraper
from src.parsers import extract_project_links
from src.config import DEBUG_MODE, DEBUG_MAX_PAGES, BASE_URL, LIMIT_BLEDOW, LINKS_FILE, MAX_WORKERS, OUTPUT_FILE
import time
import concurrent.futures
import itertools

def run_link_collector():
    logger = logging.getLogger(__name__)
    logger.info("Rozpoczęto fazę 1: zbieranie linków")

    if DEBUG_MODE:
        logger.warning(f"Aktywowano w ustawieniach tryb debugowania, limit pobierania ustawiony na {DEBUG_MAX_PAGES}")

    #tracker do zapisywania postępu stron wyszukiwania
    tracker = ProgressTracker(file_path="visited_searches.txt")

    #nie inicjalizujemy storage, na razie interesują nas czyste linki
    with MapadotacjiScraper(storage_manager=None) as scraper:
        kolejne_bledy_z_rzedu = 0
        koniec_danych = False

        #nieskończony lilcznik stron paginacji
        page_iterator = itertools.count(start=1)

        def _fetch_page_links(page_num: int) -> tuple[int, set[str] | None]:
            #pobieramy stronę indeksu i zwracamy listę linków do projektów, ale jeśli strona jest pusta lub wystąpił błąd to zwracamy none

            #jeśli stronę już odwiedziliśmy poprzednio, zwracamy pusty zbiór
            if tracker.is_search_page_visited(page_num):
                return page_num, set()

            page_url = f"{BASE_URL}/projekty/?page_no={page_num}"
            try:
                logger.debug(f"Pobieranie {page_url}")
                html = scraper.fetch_html(page_url)
                links = extract_project_links(html, base_url=BASE_URL)

                if not links:
                    logger.warning(f"Strona {page_num} nie zwróciła listy projektów")
                    return page_num, set()
                return page_num, links
            except Exception as e:
                logger.error(f"Błąd podczas pobierania strony {page_num}: {e}")
                return page_num, None
        with open(LINKS_FILE, "a", encoding="utf-8") as f:
            with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
                while not koniec_danych:
                    batch_pages = []

                    #przygotowujemy paczkę zadań wielkości puli wątków
                    for _ in range(MAX_WORKERS):
                        p_num = next(page_iterator)
                        #DEBUG
                        if DEBUG_MODE and p_num > DEBUG_MAX_PAGES:
                            koniec_danych = True
                            break
                        #dodajemy do kolejki strony których jeszcze nie mamy
                        if not tracker.is_search_page_visited(p_num):
                            batch_pages.append(p_num)

                    #jeśli cała paczka już była w trackerze omijamy
                    if not batch_pages:
                        #jeśli doszliśmy do końca danych to przerywamy zamiast omijać
                        if koniec_danych:
                            break
                        continue

                    #zlecamy paczkę do puli wątków
                    future_to_page = {
                        executor.submit(_fetch_page_links, p_num): p_num
                        for p_num in batch_pages
                    }

                    batch_bledy = 0
                    #odbieramy wyniki
                    for future in concurrent.futures.as_completed(future_to_page):
                        page_num = future_to_page[future]
                        res = future.result()

                        #błąd wątku
                        if res is None:
                            batch_bledy += 1
                            continue

                        _, wynik_linki = res
                        if wynik_linki is None:
                            batch_bledy += 1
                        elif len(wynik_linki) == 0:
                            logger.info(f"Osiągnięto koniec danych na stronie {page_num}")
                            koniec_danych = True
                            if not tracker.is_search_page_visited(page_num):
                                tracker.mark_search_page_visited(page_num)
                        else:
                            #zapisujemy
                            for link in wynik_linki:
                                f.write(f"{link}\n")
                            #zrzut do dysku
                            f.flush()
                            tracker.mark_search_page_visited(page_num)
                            logger.info(f"Zapisano {len(wynik_linki)} linków ze strony {page_num}")
                    #sprawdzamy czy przerwać główny program
                    if batch_bledy == len(batch_pages):
                        kolejne_bledy_z_rzedu += 1
                        if kolejne_bledy_z_rzedu >= LIMIT_BLEDOW:
                            logger.error("Zbyt wiele błędów z rzędu, zaprzestajemy zbierania linków")
                            break
                    else:
                        kolejne_bledy_z_rzedu = 0
    logger.info(f"Linki zostały zebrane w pliku {LINKS_FILE}")

def run_project_scraper():
    logger = logging.getLogger(__name__)
    logger.info("Rozpoczęto ekstrakcję metadanych projektów")

    #ten tracker pilnuje konkretnych linków do projektów
    tracker = ProgressTracker(file_path="visited_urls.txt")

    with JsonlStorage(OUTPUT_FILE) as storage, MapadotacjiScraper(storage_manager=storage) as scraper:
        #definiujemy pojedynczego workera
        def _process_single_project(project_url: str) -> bool:
            if tracker.is_visited(project_url):
                logger.debug(f"Pominięto {project_url}, już znajduje się w bazie")
                return True
            logger.debug(f"Pobieranie detali dla {project_url}")
            czy_sukces = scraper.process_project(project_url)

            if czy_sukces:
                tracker.mark_visited(project_url)
            return czy_sukces

        #bierzemy pliki z fazy 1
        try:
            with open(LINKS_FILE, "r", encoding="utf-8") as f:
                project_urls = {line.strip() for line in f if line.strip()}
        except FileNotFoundError:
            logger.error(f"Nie znaleziono pliku {LINKS_FILE}")
            return

        #otwieramy pulę wątków dla fazy 2
        with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            #bierzemy pulę linków
            future_to_url = {
                executor.submit(_process_single_project, url): url
                for url in project_urls
            }

            bledy = 0

            #czekamy na zakończenie zadań
            for future in concurrent.futures.as_completed(future_to_url):
                url = future_to_url[future]
                try:
                    sukces = future.result()
                    if not sukces:
                        bledy += 1
                        logger.error(f"Nie udało się przetworzyć projektu {url}")
                except Exception as e:
                    bledy += 1
                    logger.error(f"Nieprzewidziany wyjątek w workerze projektu {url}: {e}")
    logger.info(f"Łączna liczba pominiętych/błędnych projektów: {bledy}")
    
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

    run_link_collector()
    run_project_scraper()