import pytest
from unittest.mock import patch, MagicMock

#tą funkcję testujemy
from src.main import run_crawler

#Test 1, zabezpieczenie przed błędem zrzucanym przez scraper

@patch("src.main.MapadotacjiScraper", autospec=True)
@patch("src.main.JsonlStorage", autospec=True)
@patch("src.main.ProgressTracker", autospec=True)
def test_run_crawler_does_not_save_page_on_worker_error(MockTracker, MockStorage, MockScraper):
    #szykujemy mocki
    mock_tracker_instance = MockTracker.return_value
    mock_scraper_instance = MockScraper.return_value.__enter__.return_value

    #oznaczamy wszystkie strony wyszukiwania jako nieodwiedzone
    mock_tracker_instance.is_search_page_visited.return_value = False

    mock_tracker_instance.is_visited.return_value = False

    #Atrapa sieciowa
    def mock_fetch_html(url):
        if "page_no=1" in url:
            return "ZAWARTOSC_STRONY_1"
        return "PUSTA_STRONA"

    #atrapa parsera html, reaguje na to co odda atrapa sieciowa
    def mock_extract(html_content, base_url):
        if "ZAWARTOSC_STRONY_1" in html_content:
            return ["https://test-link.gov.pl"]
        return []

    with patch("src.main.extract_project_links", side_effect=mock_extract):
        with patch("src.main.BASE_URL", "https://test.gov.pl"):
            mock_scraper_instance.process_project.side_effect = Exception("Sztuczny błąd")

            #przypisujemy mockową funkcję
            mock_scraper_instance.fetch_html.return_value = mock_fetch_html

            run_crawler()

    #Strona 1 nie powinna zostać zapisana jako zakończona, powinien nastąpić wyjątek z powodu wystąpienia błędu
    mock_tracker_instance.mark_search_page_visited.assert_not_called()

# Test 2: Zabezpieczenie przed silent failure
@patch("src.main.MapadotacjiScraper", autospec=True)
@patch("src.main.JsonlStorage", autospec=True)
@patch("src.main.ProgressTracker", autospec=True)
def test_run_crawler_does_not_save_page_on_scraper_silent_failure(
    MockTracker: MagicMock,
    MockStorage: MagicMock,
    MockScraper: MagicMock
):
    mock_tracker_instance = MockTracker.return_value
    mock_scraper_instance = MockScraper.return_value.__enter__.return_value

    mock_tracker_instance.is_search_page_visited.return_value = False
    mock_tracker_instance.is_visited.return_value = False

    def mock_fetch_html(html_content, base_url):
        if "page_no=1" in html_content:
            return ["https://test-link.gov.pl"]
        return []

    def mock_extract(html_content, base_url):
        if "ZAWARTOSC_STRONY_1" in html_content:
            return ["https://test-link.gov.pl"]
        return []

    with patch("src.main.extract_project_links", side_effect=mock_extract):
        with patch("src.main.BASE_URL", "https://test.gov.pl"):
            #tutaj w przeciwieństwie do testu 1 zawodzimy bez rzucania błędem
            mock_scraper_instance.process_project.return_value = False
            mock_scraper_instance.fetch_html.return_value = mock_fetch_html

            run_crawler()

    #zapis powinien się zablokować ze względu na wynik false ze scrapera
    mock_tracker_instance.mark_search_page_visited.assert_not_called()