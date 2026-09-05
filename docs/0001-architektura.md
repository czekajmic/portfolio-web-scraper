# ADR 0001: Architektura warstwowa scrapera i układ katalogów

## Kontekst
Projekt wymaga mechanizmu pobierania danych ze stron wyszukiwania oraz ich podstron. Skrypty typu "wszystko w jednym pliku" są trudne w utrzymaniu, testowaniu i skalowaniu.

## Decyzja
Przyjęto standardowy układ katalogów z folderem `src/`. Logika aplikacji została podzielona na niezależne moduły:
- `models.py`: Reprezentacja dziedziny (Data Transfer Objects).
- `parsers.py`: Izolowana ekstrakcja danych z HTML.
- `scraper.py`: Logika biznesowa i paginacja.
- `storage.py`: Mechanizmy wejścia/wyjścia (zapis do plików).

## Konsekwencje
+ Łatwość testowania poszczególnych komponentów (np. parserów bez uderzania do sieci).
+ Wyraźny podział ról w kodzie.
- Konieczność wstrzykiwania zależności w pliku `main.py`, co nieznacznie zwiększa początkowy stopień skomplikowania.