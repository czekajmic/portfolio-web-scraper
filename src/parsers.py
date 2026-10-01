from bs4 import BeautifulSoup
from urllib.parse import urljoin
from src.models import ProjectDetails
import re
from src.config import BASE_URL, UNKNOWN_ID_FLAG, UNKNOWN_TITLE_FLAG

def extract_project_links(html_content: str, base_url: str = BASE_URL) -> set[str]:
    links: set[str] = set()
    soup = BeautifulSoup(html_content, "html.parser")

    for a_tag in soup.select("td.see-all a[href*='/projekty/']"):
        href = a_tag.get("href")
        if href and "page_no" not in href and "search-theme=" not in href:
            full_url = urljoin(base_url, str(href))
            links.add(full_url)
    return links

def parse_project_details(html_content: str) -> ProjectDetails:
    #Analizuje kod HTML i wyciąga dane do modelu ProjectDetails
    soup = BeautifulSoup(html_content, "html.parser")
    
    #najpierw ID, szukamy klasy w body zaczynającej się od "postid-"
    id_projektu = UNKNOWN_ID_FLAG
    body_tag = soup.find("body")
    if body_tag and body_tag.get("class"):
        for klasa in body_tag.get("class") or []:
            if klasa.startswith("postid-"):
                id_projektu = klasa.replace("postid-", "")
                break

    # teraz tytuł projektu
    title_element = soup.find("h2", class_="big-title")
    tytul = title_element.text.strip() if title_element else UNKNOWN_TITLE_FLAG

    # kategorie
    kategorie = []
    kategorie_div = soup.find("div", class_="categories")
    if kategorie_div:
        #każda kategoria to osobny span
        for span in kategorie_div.find_all("span"):
            kategoria_text = span.text.strip()
            if kategoria_text:
                kategorie.append(kategoria_text)

    # pusty szablon dla pozostałych sekcji
    extracted_data = {
        "beneficjent": None,
        "total_value_str": None,
        "eu_funding_str": None,
        "program": None,
        "dzialanie": None,
        "fundusz": None,
        "perspective": None,
        "wojewodztwa": [],
        "powiaty": []
    }

    #mapujemy etykiety ze storny na klucze w słowniku danych
    fields_map = {
        "nazwa beneficjenta": "beneficjent",
        "wartość projektu": "total_value_str",
        "dofinansowanie z ue": "eu_funding_str",
        "program": "program",
        "działanie": "dzialanie",
        "fundusz": "fundusz",
        "perspektywa": "perspective",
        "województwo": "wojewodztwa",
        "powiat": "powiaty"
    }

    #szukamy wszystkich etykiet na stronie, ...-up to etykieta, ...-down to wartość
    etykiety = soup.find_all("div", class_=re.compile("single-project-info-item-text-up"))
    for etykieta in etykiety:
        key_text = etykieta.text.strip().lower()

        #jeśli etykieta nas nie interesuje, pomijamy
        if key_text not in fields_map:
            continue

        field_name = fields_map[key_text]

        #iterujemy po kolejnych elementach poniżej tej etykiety
        values = []
        for sibling in etykieta.find_next_siblings("div"):
            klasy = sibling.get("class") or []
            klasa_string = " ".join(klasy)

            #jeśli natrafimy na kolejną etykietę "up" to przerywamy
            if "single-project-info-item-text-up" in klasa_string:
                break

            #jeśli to wartość "down", to dodajemy do tymczasowej listy
            if "single-project-info-item-text-down" in klasa_string:
                val_text = sibling.text.strip()
                if val_text:
                    values.append(val_text)
        if not values:
            continue

        #przypisujemy zebrane wartości do odpowiedniego pola w słowniku
        if field_name in ["wojewodztwa", "powiaty"]:
            extracted_data[field_name].extend(values)
        else:
            #a pola tekstowe to bierzemy tylko pierwszą wartość
            extracted_data[field_name] = values[0] 

    #opis projektu
    opis = None
    desc_container = soup.find("div", class_="single-project-desc-container")
    if desc_container:
        #zbieramy wszystkie paragrafy oprócz tych pustych
        wyciagniety_tekst = desc_container.get_text(separator="\n", strip=True)
        if wyciagniety_tekst:
            opis = wyciagniety_tekst

    # zwracamy model, przypisując wyciągnięte zmienne
    return ProjectDetails(
        id_projektu=id_projektu,
        tytul=tytul,
        kategorie=kategorie,
        beneficjent=extracted_data["beneficjent"],
        program=extracted_data["program"],
        dzialanie=extracted_data["dzialanie"],
        fundusz=extracted_data["fundusz"],
        perspective=extracted_data["perspective"],
        total_value_str=extracted_data["total_value_str"],
        eu_funding_str=extracted_data["eu_funding_str"],
        wojewodztwa=extracted_data["wojewodztwa"],
        powiaty=extracted_data["powiaty"],
        opis=opis
    )