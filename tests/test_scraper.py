import pytest
import httpx
from unittest.mock import MagicMock, patch
from src.scraper import MapadotacjiScraper
from src.config import DEFAULT_MAX_RETRIES

#Test 1: zabezpieczenie pętli retry przed niespodziewanym zerwaniem połączenia przez serwer
def test_fetch_html_retries_on_request_error():
    #atrapa obiektu storage_manager
    mock_storage = MagicMock()

    with MapadotacjiScraper(storage_manager=mock_storage) as scraper:
        mock_error = httpx.RequestError("Sztuczny błąd zerwania połączenia")

        with patch.object(scraper.client, "get", side_effect=mock_error) as mock_get:
            with patch("src.scraper.time.sleep") as mock_sleep:
                with pytest.raises(RuntimeError, match="Nie udało się pobrać"):
                    scraper.fetch_html("https://test.gov.pl/projekt/1")

        assert mock_get.call_count == DEFAULT_MAX_RETRIES