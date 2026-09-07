import httpx
from bs4 import BeautifulSoup

def verify_target_endpoint(url: str, output_file_name: str) -> None:
    #Weryfikuje dostępność strony docelowej i daje parę podstawowych metryk odpowiedzi
    headers = {
        'User-Agent': (
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/102.0.0.0 Safari/537.36'
        )
    }

    print(f"?? Wysyłam żądanie do {url}")

    try:
        with httpx.Client(headers=headers, timeout=10, follow_redirects=True) as client:
            response = client.get(url)

            # Wymuszamy wyrzucenie wyjątku jeśli status to błąd np. 403, 404, 500
            response.raise_for_status
            print(f"Kod statusu: {response.status_code}")
            print(f"Nagłowek: {response.headers.get("server", "brak")}")
    except httpx.RequestError as e:
        print(f"!! Błąd sieciowy, nie udało się połączyć z {e.request.url} - {e}")
        return
    except httpx.HTTPStatusError as e:
        print(f"!! Błąd http, serwer zwrócił status {e.response.status_code} dla {e.request.url}")
        return
    else:
        print(f"++ Status: {response.status_code}")
        print(f"++ Serwer: {response.headers.get('server', 'no headers found')}")

        # Parsowanie
        soup = BeautifulSoup(response.text, "html.parser")
        title_tag = soup.find("title")
        if title_tag:
            title = title_tag.text.strip()
        else:
            title = "Brak tytułu"

        print(f"++ Tytuł strony: {title_tag}")
        with open(output_file_name, "w", encoding="utf-8") as f:
            f.write(str(soup))

        print(f"++ Zapisano zrzut ekranu HTML do {output_file_name}")

if __name__ == "__main__":
    verify_target_endpoint("https://mapadotacji.gov.pl/projekty/?search-theme=104&page_no=2", "check1.html")
    verify_target_endpoint("https://mapadotacji.gov.pl/projekty/746903/", "check2.html")
