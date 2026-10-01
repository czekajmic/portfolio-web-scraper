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
            self._file_handle.flush()

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