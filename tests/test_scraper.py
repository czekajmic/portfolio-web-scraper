import pytest
import httpx
from unittest.mock import MagicMock, patch
from src.scraper import MapadotacjiScraper
from src.config import DEFAULT_MAX_RETRIES

class TimeSimulator:
    def __init__(self):
        self.current_time = 1000.0
    def get_time(self):
        return self.current_time
    def advance(self, seconds):
        self.current_time += seconds

#Test 1: zabezpieczenie pętli retry przed niespodziewanym zerwaniem połączenia przez serwer
def test_fetch_html_retries_on_request_error():
    #atrapa obiektu storage_manager
    mock_storage = MagicMock()
    time_sim = TimeSimulator()

    with MapadotacjiScraper(storage_manager=mock_storage) as scraper:
        mock_error = httpx.RequestError("Sztuczny błąd zerwania połączenia")

        with patch.object(scraper.client, "get", side_effect=mock_error) as mock_get:
            with patch("src.scraper.time.time", side_effect=time_sim.get_time):
                with patch("src.scraper.time.sleep", side_effect=time_sim.advance):
                    with pytest.raises(RuntimeError, match="Nie udało się pobrać"):
                        scraper.fetch_html("https://test.gov.pl/projekt/1")

        assert mock_get.call_count == DEFAULT_MAX_RETRIES

#Test 2: symulacja modyfikacji struktury strony np. poprzez captcha, oczekujemy zwrócenia false ale nie crashu aplikacji
@patch("src.scraper.parse_project_details")
def test_process_project_handles_soft_ban_and_parsing_errors(mock_parse):
    mock_storage = MagicMock()

    with MapadotacjiScraper(storage_manager=mock_storage) as scraper:
        with patch.object(scraper, "fetch_html", return_value="<html><body>Weryfikacja Cloudflare</body></html>"):
            mock_parse.side_effect = ValueError("Brak wymaganych pól w HTML")
            result = scraper.process_project("https://mapadotacji.gov.pl/projekty/fake/")

            assert result is False
            mock_storage.save_project.assert_not_called()

#Test 3: sprawdzamy czy hibernacja zlicza błędy i prawidłowo zeruje się gdy serwer z powrotem odpowiada
def test_global_errors_scaling_and_recovery():
    mock_storage = MagicMock()
    time_sim = TimeSimulator()

    with MapadotacjiScraper(storage_manager=mock_storage) as scraper:
        #symulacja błędu wywołanego przez serwer
        mock_error = httpx.HTTPStatusError("503 Service Unavailable", request=MagicMock(), response=MagicMock(status_code=503))

        mock_success_response = MagicMock()
        mock_success_response.status_code = 200
        mock_success_response.text = "<html>Sukces</html>"

        #sekwencja: błąd, błąd, sukces
        with patch.object(scraper.client, "get", side_effect=[mock_error, mock_error, mock_success_response]) as mock_get:
            with patch("src.scraper.time.time", side_effect=time_sim.get_time):
                with patch("src.scraper.time.sleep", side_effect=time_sim.advance):
                    result = scraper.fetch_html("https://test.gov.pl/projekt/recovery")

                    assert "Sukces" in result
                    assert scraper._global_errors == 0
                    assert mock_get.call_count == 3