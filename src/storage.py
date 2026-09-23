import logging
from pathlib import Path
from types import TracebackType
from typing import Type
import os
import threading

from src.models import ProjectDetails

logger = logging.getLogger(__name__)

class JsonlStorage:
    #wykorzystujemy format jsonl, by każdy rekord był osobnym obiektem json w nowej linii

    def __init__(self, file_path: Path | str, mode: str = "a", encoding = "utf-8") -> None:
        #inicjalizacja
        self.file_path = Path(file_path)
        self.mode = mode
        self.encoding = encoding
        self._file_handle = None
        self._lock = threading.Lock()

    def __enter__(self) -> "JsonlStorage":
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        self._file_handle = open(self.file_path, mode=self.mode, encoding=self.encoding)
        logger.debug(f"Otwarto plik do zapisu: {self.file_path} w trybie {self.mode}")
        return self

    def __exit__(self, exception_type: Type[BaseException] | None, exception_value: BaseException | None, exception_traceback: TracebackType | None) -> None:
        #bezpieczne zamknięcie po wyjściu lub gdy błąd
        if self._file_handle:
            self._file_handle.close()
            logger.debug(f"Zamknięto plik zapisu: {self.file_path}")

    def save_project(self, project: ProjectDetails) -> None:
        if not self._file_handle:
            raise RuntimeError("Błąd file_handle!")
        json_string = project.model_dump_json()

        #blokada dla innych wątków
        with self._lock:
            self._file_handle.write(json_string + "\n")

#zarządza listą odwiedzonych linków i pilnuje duplikatów dzięki set()
class ProgressTracker:
    def __init__(self, file_path: str = "visited_urls.txt", file_path_for_searches: str = "visited_searches.txt"):
        self.file_path = file_path
        self.file_path_for_searches = file_path_for_searches
        self.visited = set()
        self.visited_searches = set()
        self._lock = threading.Lock()
        self._load_existing()

    def _load_existing(self):
        if os.path.exists(self.file_path):
            with open(self.file_path, "r", encoding="utf-8") as f:
                for line in f:
                    url = line.strip()
                    if url:
                        self.visited.add(url)
            logger.info(f"Wczytano {len(self.visited)} już przetworzonych linków")
        else:
            logger.info(f"Nie znaleziono pliku {self.file_path}, zbieranie linków od nowa")
        if os.path.exists(self.file_path_for_searches):
            with open(self.file_path_for_searches, "r", encoding="utf-8") as f:
                for line in f:
                    page = line.strip()
                    if page.isdigit():
                        self.visited_searches.add(int(page))
            logger.info(f"Wczytano {len(self.visited_searches)} gotowych stron wyszukiwania z {self.file_path_for_searches}")

    def is_visited(self, url: str) -> bool:
        return url in self.visited

    def mark_visited(self, url: str):
        with self._lock:
            if url not in self.visited: #ten warunek musi być mimo używania set(), inaczej będziemy dopisywać do pliku za każdym razem!
                self.visited.add(url)
                with open(self.file_path, "a", encoding="utf-8") as f:
                    f.write(f"{url}\n")

    def is_search_page_visited(self, page_num: int) -> bool:
        return page_num in self.visited_searches

    def mark_search_page_visited(self, page_num: int):
        with self._lock:
            if page_num not in self.visited_searches:
                self.visited_searches.add(page_num)
                with open(self.file_path_for_searches, "a", encoding="utf-8") as f:
                    f.write(f"{page_num}\n")

#blok testowy
if __name__ == "__main__":
    import json
    from pathlib import Path
    logging.basicConfig(level=logging.DEBUG)
    test_file = Path("data_test/test_output.jsonl")
    try:
        mock_projects = [
        # Konstrukcja przykładowych modeli (wymień kwargsy na faktyczne z ProjectDetails)
        ProjectDetails(
            id_projektu="PRJ-001",
            tytul="Budowa innowacyjnego centrum badawczego",
            total_value_str="15 000 000,00 PLN",
            beneficjent="Politechnika Warszawska"
        ),
        ProjectDetails(
            id_projektu="PRJ-002",
            tytul="Szkolenia dla programistów",
            total_value_str="120 000,50 PLN",
            beneficjent=None  # Symulacja braku danych
        )
    ]
    except Exception as e:
        print(f"Błąd: {e}")
        exit(1)

    with JsonlStorage(test_file, mode="w") as storage:
        for p in mock_projects:
            storage.save_project(p)
            print(f"Zapisano {p.tytul}")

    with open(test_file, "r", encoding="utf-8") as f:
        lines = f.readlines()
        for i, line in enumerate(lines, 1):
            data = json.loads(line)
            print(f"Linia {i}: {data}")
    print(f"Zapisano i odczytano {len(lines)} w {test_file}")

    #test ProgressTracker
    test_file_tracker = Path("data_test/test_visited.txt")
    test_searches_tracker = Path("data_test/test_visited_searches.txt")

    #usuwanie w ramach testu, uwaga!!
    if test_file_tracker.exists():
        test_file_tracker.unlink()
    if test_searches_tracker.exists():
        test_searches_tracker.unlink()

    tracker = ProgressTracker(file_path=str(test_file_tracker), file_path_for_searches=str(test_searches_tracker))

    test_urls = ["https://wp.pl", "https://wykop.pl", "https://wp.pl"]

    for url in test_urls:
        if tracker.is_visited(url):
            print(f"Pomijam {url} bo duplikat")
        else:
            print(f"Nowy url {url}, zapisywany do pliku")
            tracker.mark_visited(url)

    #próbujemy wznowić
    tracker_resume = ProgressTracker(file_path=str(test_file_tracker))

    if tracker_resume.is_visited("https://wp.pl"):
        print("https://wp.pl zostało zapamiętane z sukcesem")
    else:
        print("fail")