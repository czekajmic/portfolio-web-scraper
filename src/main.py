import logging
import sys
from src.storage import JsonlStorage, ProgressTracker
from src.scraper import MapadotacjiScraper
from src.parsers import extract_project_links
from src.config import DEBUG_MODE, DEBUG_MAX_PAGES, BASE_URL, LIMIT_BLEDOW, LINKS_FILE
import time
import concurrent.futures
import itertools

MAX_WORKERS = 5


def run_crawler():
    logger = logging.getLogger(__name__)
    logger.info("Crawler rozpoczął pracę")

    tracker = ProgressTracker(file_path="visited_urls.txt")

    with JsonlStorage("mapadotacji_wyniki.jsonl") as storage, MapadotacjiScraper(storage_manager=storage) as scraper:

        kolejne_bledy_z_rzedu = 0
        LIMIT_BLEDOW = 3

        #wyodrębniona funkcja-worker do wywoływania na wielu wątkach, musi zwracać bool jako ostateczny sukces swojej pracy
        def _process_single_url(url: str, i: int, total_urls: int) -> bool:
            if tracker.is_visited(url):
                logger.debug(f"Pominięto {url}, już odwiedzony")
                return True 
            
            logger.debug(f"Pobieranie projektu {i}/{total_urls} ze strony {url}")
            
            czy_sukces = scraper.process_project(url)
            if czy_sukces:
                tracker.mark_visited(url)

            #scraper może rzucić wyjątek i oddać false
            return czy_sukces


        for page_num in itertools.count(start=1):
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
                            #musimy pobrać wynik true/false od workera
                            #blokuje wątek póki się nie skończy, a jeśli błąd to będzie wyrzucony tutaj
                            sukces_workera = future.result()

                            #jeśli false, strona ma niezapisany projekt
                            if not sukces_workera:
                                logger.error(f"Worker nad {current_url} zakończył się z błędem")
                                page_pelen_sukces = False

                        except Exception as e:
                            logger.error(f"Worker pracujący nad {current_url} napotkał błąd: {e}", exc_info=True)
                            page_pelen_sukces = False
                if page_pelen_sukces:
                    tracker.mark_search_page_visited(page_num)
                    logger.info(f"Strona {page_num} pomyślnie oznaczona jako przetworzona")
                else:
                    logger.warning(f"Strona {page_num} zakończyła się z błędami w workerach. Nie zapisano jej jako ukończonej.")
                kolejne_bledy_z_rzedu = 0
            except Exception as e:
                logger.error(f"Błąd podczas crawlingu strony {page_url}: {e}")
                kolejne_bledy_z_rzedu += 1
                if kolejne_bledy_z_rzedu >= LIMIT_BLEDOW:
                    logger.error(f"Przerwano pętlę - wystąpił limit błędów z rzędu dla strony wyszukiwania {page_num}")
                    break
                continue
            time.sleep(1.0)
    logger.info("Zakończono pracę crawlera")

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

    #run_crawler()
    run_link_collector()