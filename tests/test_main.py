import pytest
from unittest.mock import patch, MagicMock, mock_open
import time

#tą funkcję testujemy
from src.main import run_link_collector, MAX_WORKERS, run_project_scraper

#Atrapy, zamiast Magic Mock
class FakeTracker:
    def __init__(self, file_path=""):
        self.zapisane_strony = []
    def is_search_page_visited(self, page_num):
        if page_num > 50:
            raise RuntimeError("Wykryto nieskończoną pętlę")
        return False #udajemy zawsze że strony jeszcze nie było
    def mark_search_page_visited(self, page_num):
        self.zapisane_strony.append(page_num)

class FakeScraperPaginating:
    def __init__(self, storage_manager=None): pass
    def __enter__(self): return self
    def __exit__(self, exc_type, exc, tb): pass

    def fetch_html(self, url):
        if "page_no=1" in url or "page_no=2" in url:
            return "ZAWARTOSC_STRONY_Z_LINKAMI"
        return "ZAWARTOSC_STRONY_PUSTA"

class FakeScraperSuccess:
    #bezbłedne oddanie zawartości
    def __init__(self, storage_manager=None): pass
    def __enter__(self): return self
    def __exit__(self, exc_type, exc, tb): pass

    def fetch_html(self, url):
        return "ZAWARTOSC_STRONY_1"
    
class FakeScraperNetworkError:
    #tym razem scraper psuje się od razu
    def __init__(self, storage_manager=None): pass
    def __enter__(self): return self
    def __exit__(self, exc_type, exc, tb): pass

    def fetch_html(self, url):
        raise Exception("Sztuczny błąd sieciowy")

def fake_extract_links_success(html_content, base_url):
    return {"https://test-link.gov.pl"}

def fake_extract_links_empty(html_content, base_url):
    return set()

def fake_extract_links_dynamic(html_content, base_url):
    if html_content == "ZAWARTOSC_STRONY_Z_LINKAMI":
        return {"https://test-link.gov.pl/projekt1", "https://test-link.gov.pl/projekt2"}
    return set()


#Testy oparte na atrapach

#Test 1: błąd scrapera = strona nie została oznaczona w trackerze
@patch("builtins.open", new_callable=mock_open)
@patch("src.main.ProgressTracker")
@patch("src.main.MapadotacjiScraper")
def test_run_link_collector_does_not_save_page_on_error(MockScraper, MockTracker, mock_file):
    MockTracker.return_value = FakeTracker()
    MockScraper.return_value = FakeScraperNetworkError()

    with patch("src.main.DEBUG_MODE", True), patch("src.main.DEBUG_MAX_PAGES", 2):
        run_link_collector()
    assert mock_file().write.call_count == 0

#Test 2: Pusta strona = koniec paginacji, ale traktowana poprawnie
@patch("builtins.open", new_callable=mock_open)
@patch("src.main.ProgressTracker")
@patch("src.main.MapadotacjiScraper")
@patch("src.main.extract_project_links", side_effect=fake_extract_links_dynamic)
def test_run_link_collector_handles_empty_pages_safely(MockExtract, MockScraper, MockTracker, mock_file):
    tracker_fake = FakeTracker()
    MockTracker.return_value = tracker_fake
    MockScraper.return_value = FakeScraperPaginating()

    with patch("src.main.DEBUG_MODE", False):
        run_link_collector()
    assert mock_file().write.call_count > 0
    assert len(tracker_fake.zapisane_strony) <= MAX_WORKERS * 2 # Np. 15 workerów, to jedna lub dwie paczki to 30 pozycji w trackerze

#Test 3: Standardowa udana strona
@patch("builtins.open", new_callable=mock_open)
@patch("src.main.ProgressTracker")
@patch("src.main.MapadotacjiScraper")
@patch("src.main.extract_project_links", side_effect=fake_extract_links_success)
def test_run_link_collector_saves_page_on_success(MockExtract, MockScraper, MockTracker, mock_file):
    tracker_fake = FakeTracker()
    MockTracker.return_value = tracker_fake
    MockScraper.return_value = FakeScraperSuccess()

    with patch("src.main.DEBUG_MODE", True), patch("src.main.DEBUG_MAX_PAGES", 2):
        run_link_collector()

    assert len(tracker_fake.zapisane_strony) == 2
    mock_file().write.assert_called_with("https://test-link.gov.pl\n")

#Test 4: weryfikacja że skrypt przetwarza wszystkie linki mimo błędów
@patch("src.main.MapadotacjiScraper")
@patch("src.main.JsonlStorage")
@patch("src.main.ProgressTracker")
@patch("builtins.open", new_callable=mock_open, read_data="http://url1\nhttp://url2\nhttp://url3\nhttp://url4\nhttp://url5\n")
def test_run_project_scraper_never_cancels(mock_file, MockTracker, MockStorage, MockScraper):
    tracker_instance = MockTracker.return_value
    tracker_instance.is_visited.return_value = False

    scraper_instance = MockScraper.return_value.__enter__.return_value

    def slow_failing_worker(*args, **kwargs):
        import time
        time.sleep(0.01)
        return False

    scraper_instance.process_project.side_effect = slow_failing_worker

    with patch("src.main.MAX_WORKERS", 2):
        run_project_scraper()

    assert scraper_instance.process_project.call_count == 5, "Skrypt przedwcześnie anulował zadania"