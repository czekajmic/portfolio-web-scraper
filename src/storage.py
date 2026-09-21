import logging
from pathlib import Path
from types import TracebackType
from typing import Type

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
        self._file_handle.write(json_string + "\n")

#blok testowy
if __name__ == "__main__":
    import json
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