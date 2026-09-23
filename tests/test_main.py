import pytest
from unittest.mock import patch, MagicMock

#tą funkcję testujemy
from src.main import run_crawler

@patch("src.main.MapadotacjiScraper", autospec=True)
@patch("src.main.JsonlStorage", autospec=True)
@patch("src.main.Progresstracker", autospec=True)
def test_run_crawler_does_not_save_page_on_worker_error(MockTracker, MockStorage, MockScraper):
    #szykujemy mocki
    mock_tracker_instance = MockTracker.return_value
    mock_scraper_instance = MockScraper.return_value.__enter__.return_value

    #oznaczamy wszystkie strony wyszukiwania jako nieodwiedzone
    mock_tracker_instance.is_search_page_visited.return_value = False

    mock_tracker_instance.is_visited.return_value = False

    with patch("src.main.extract_project_links", return_value=["https://test-link.gov.pl"]):
        with patch("src.main.BASE_URL", "https://test.gov.pl"):
            mock_scraper_instance.process_project.side_effect = Exception("Sztuczny błąd")

            run_crawler(max_pages=2)

    mock_tracker_instance.mark_search_page_visited.assert_not_called()