import logging
from typing import Optional
from src.storage import JsonlStorage
from src.config import DEFAULT_HEADERS, DEFAULT_TIMEOUT_DURATION, DEFAULT_CONNECT_DURATION, DEFAULT_MAX_RETRIES, DEFAULT_DELAY_DURATION, POLITE_BASE_DELAY, POLITE_JITTER_MAX, MAX_WORKERS
import httpx
import time
from src.parsers import parse_project_details
import sys
import threading
import random

logger = logging.getLogger(__name__)

class MapadotacjiScraper:
    def __init__(self, storage_manager: Optional[JsonlStorage]):
        #klasa sama nie otwiera pliku, tylko dostaje gotowy obiekt storage
        self.storage = storage_manager

        timeout = httpx.Timeout(DEFAULT_TIMEOUT_DURATION, connect=DEFAULT_CONNECT_DURATION)

        self.client = httpx.Client(headers=DEFAULT_HEADERS, timeout=timeout, http2=True)

        self._cooldown_lock = threading.Lock()
        self._cooldown_until: float = 0.0
        self._global_errors: int = 0
        self._consecutive_network_errors: int = 0

        logger.info("Zainicjalizowano MapadotacjiScraper")

    def __enter__(self):
        return self

    def _wait_if_cooldown(self):
        with self._cooldown_lock:
            now = time.time()
            if self._cooldown_until > now:
                sleep_time = self._cooldown_until - now
                logger.warning(f"Zatrzymanie wątku, trwa globalny cooldown, komenda sleep na {sleep_time:.2f} sek")
            else:
                sleep_time = 0.0
        if sleep_time > 0:
            logger.warning(f"Zatrzymanie wątku przez globalny cooldown, komenda sleep na {sleep_time:.2f} sek")
            time.sleep(sleep_time)

    def fetch_html(self, url: str) -> str:
        #pobiera kod HTML z danego url
        for attempt in range(1, DEFAULT_MAX_RETRIES + 1):
            #najpierw sprawdzamy czy nie ma cooldownu
            self._wait_if_cooldown()

            jitter = random.uniform(0.0, POLITE_JITTER_MAX)
            polite_delay = POLITE_BASE_DELAY + jitter
            time.sleep(polite_delay)

            try:
                logger.debug(f"Pobieranie {attempt}/{DEFAULT_MAX_RETRIES} dla {url}")
                response = self.client.get(url)
                #wyjątek jeśli zły status http
                response.raise_for_status()

                #zerowanie licznika globalnych awarii przy sukcesie
                if self._global_errors > 0 or self._consecutive_network_errors > 0:
                    with self._cooldown_lock:
                        self._global_errors = 0
                        self._consecutive_network_errors = 0
                return response.text
            except httpx.HTTPStatusError as e: #błędy serwera
                status = e.response.status_code
                logger.warning(f"Błąd sieci {status} podczas pobierania nr {attempt} dla {url}: {e}")

                #coś nie tak z projektami, nie włączają hibernacji i są pomijane
                if 400 <= status < 500 and status not in (429, 403):
                    logger.error(f"Błąd klienta {status} dla {url}")
                    raise RuntimeError(f"Błąd {status} dla {url}")

                if status >= 500 and status != 503:
                    logger.error(f"Błąd serwera {status} dla {url}")
                    self._handle_global_error(e)
                    raise RuntimeError(f"Awaria serwera {status} dla {url}")
                
                if status in (429, 403, 503): #typ rate limit
                    cooldowns = {1: 60, 2: 300, 3:900}
                    cooldown_time = cooldowns.get(attempt, 900)

                    logger.error(f"Otrzymano ban ({status}) dla {url}, uruchamiamy cooldown na {cooldown_time}")

                    with self._cooldown_lock:
                        now = time.time()
                        new_cooldown = now + cooldown_time
                        if new_cooldown > self._cooldown_until:
                            self._cooldown_until = new_cooldown
            except httpx.RequestError as e: #błędy lokalne
                with self._cooldown_lock:
                    self._consecutive_network_errors += 1
                    current_errors = self._consecutive_network_errors

                if current_errors >= max(MAX_WORKERS, 3):
                    logger.critical(f"Wystąpiło {current_errors} błędów sieciowych z rzędu")

                cooldown_time = 5 * attempt
                logger.warning(f"Błąd sieci podczas pobierania nr {attempt} dla {url}: {e}")

                logger.warning(f"Błąd lokalny nr {attempt} dla {url}: {e}, usypiam na {cooldown_time} s.")
                time.sleep(cooldown_time)
                continue
        #jeśli tu dotarliśmy, to wyczerpaliśmy limit prób
        logger.error(f"Wyczerpano limit prób dla {url}")
        raise RuntimeError(f"Nie udało się pobrać {url}")
    def __exit__(self, exc_type, exc, tb):
        self.client.close()
        logger.info("Zamknięto klienta HTTP")

    def process_project(self, project_url: str)  -> bool:
        logger.debug(f"Przetwarzanie projektu {project_url}")
        try:
            html_content = self.fetch_html(project_url)
            project_model = parse_project_details(html_content)

            if self.storage:
                self.storage.save_project(project_model)
                logger.info(f"Zapisano {project_model.tytul}")
            else:
                logger.debug(f"Pobrano detale {project_url}, ale storage_manager nie istnieje i nie ma możliwości zapisu")
            return True
        except Exception as e:
            logger.error(f"Błąd przy przetwarzaniu {project_url}: {e}")
            return False

    #hibernacja dla całej puli wątków
    def _handle_global_error(self, e: Exception):
        with self._cooldown_lock:
            now = time.time()
            #sprawdzamy czy inny wątek nie ogłosił już tej samej awarii
            if now >= self._cooldown_until:
                self._global_errors += 1

                #rosnący downtime programu
                if self._global_errors == 1:
                    cooldown_time = 60
                elif self._global_errors == 2:
                    cooldown_time = 300
                else:
                    cooldown_time = 900 + 60 * (self._global_errors - 2)

                self._cooldown_until = now + cooldown_time
                logger.critical(f"Globalna awaria z serii nr {self._global_errors}: {e}, hibernujemy wszystkie wątki na {cooldown_time} s. ")
            


#TESTOWANIE
if __name__ == "__main__":
    from src.models import ProjectDetails
    from src.parsers import parse_project_details
    from src.storage import JsonlStorage

    log_format = "%(asctime)s - %(levelname)s - %(name)s - %(message)s"
    logging.basicConfig(
        level=logging.DEBUG,
        format=log_format,
        handlers=[
            logging.FileHandler("scraper_debug.log", encoding="utf-8", mode="a"),
            logging.StreamHandler(sys.stdout)
        ]
        )
    #mamy level logów jako debug, ale wyciszamy zewnętrzne biblioteki
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("hpack").setLevel(logging.WARNING)

    logger.info("Testowanie scrapera")
    test_urls = [
        "https://mapadotacji.gov.pl/projekty/746927/",
        "https://mapadotacji.gov.pl/projekty/0/",
        "https://mapadotacji.gov.pl/projekty/1691544/",
        "https://simulatehttpcode.vercel.app/statuscode?q=429"
    ]

    try:
        with JsonlStorage("test_dane.jsonl") as storage, MapadotacjiScraper(storage_manager=storage) as scraper:
            for url in test_urls:
                #pobrany_html = scraper.fetch_html(url)
                #print(pobrany_html[:1000]) #już nie będziemy wszystkiego tu wypisywać
                czy_sukces = scraper.process_project(url)
                if czy_sukces:
                    logger.info(f"Projekt {url} pomyślnie dopisany do pliku JSONL")
    except Exception as e:
        print(f"Wystąpił błąd {e}")
