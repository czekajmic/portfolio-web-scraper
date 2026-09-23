import logging
import sys
import time
import concurrent.futures
from src.scraper import MapadotacjiScraper

# Konfiguracja logera, aby widzieć, z którego wątku pochodzi komunikat
log_format = "%(asctime)s - %(threadName)s - %(levelname)s - %(message)s"
logging.basicConfig(
    level=logging.DEBUG,
    format=log_format,
    handlers=[logging.StreamHandler(sys.stdout)]
)

# Wyciszenie bibliotek sieciowych dla czystości logów
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

class DummyStorage:
    """Prosta atrapa bazy danych, żeby nie tworzyć zbędnych plików podczas testu"""
    def save_project(self, project):
        pass

def run_cooldown_test():
    url_do_ataku = "https://simulatehttpcode.vercel.app/statuscode?q=429"
    logger = logging.getLogger("TestCoordinator")
    
    logger.info("Rozpoczęcie wielowątkowego testu cooldownu (Circuit Breaker)...")
    storage = DummyStorage()

    with MapadotacjiScraper(storage_manager=storage) as scraper:
        
        # Tworzymy funkcję lokalną dla workera
        def worker_task(worker_id):
            logger.info(f"[Worker-{worker_id}] Startuje zapytanie...")
            try:
                # Wywołanie bez process_project aby ominąć parsowanie (nasz mock HTML by tu wybuchł)
                scraper.fetch_html(url_do_ataku)
            except Exception as e:
                logger.info(f"[Worker-{worker_id}] Przerwał pracę z powodem: {e}")

        # Otwieramy pulę 5 równoległych wątków
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            # Uruchamiamy 5 wątków naraz
            for i in range(1, 6):
                executor.submit(worker_task, i)

if __name__ == "__main__":
    run_cooldown_test()