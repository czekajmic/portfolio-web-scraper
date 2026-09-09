from bs4 import BeautifulSoup
from urllib.parse import urljoin

def extract_project_links(html_content: str, base_url: str = "https://mapadotacji.gov.pl") -> set[str]:
    links: set[str] = set()
    soup = BeautifulSoup(html_content, "html.parser")

    for a_tag in soup.select("td.see-all a[href*='/projekty/']"):
        href = a_tag.get("href")
        if href and "page_no" not in href and "search-theme=" not in href:
            full_url = urljoin(base_url, str(href))
            links.add(full_url)
    return links

if __name__ == "__main__":
    #test IO na czas budowy parsera
    import os
    test_file = "check1.html"
    if not os.path.exists(test_file):
        print(f"!! Błąd pliku {test_file}!")
    else:
        with open(test_file, "r", encoding="utf-8") as f:
            raw_html = f.read()
        extracted_links = extract_project_links(raw_html)
        print(f"++ Znaleziono linków: {len(extracted_links)}")
        for link in extracted_links:
            print(f" - {link}")