from pydantic import BaseModel, Field, computed_field

class ProjectDetails(BaseModel):
    id_projektu: str = Field(..., description="ID projektu, np. 752129")
    tytul: str = Field(..., description="Tytuł projektu")

    #tutaj na ten moment jeszcze nie jesteśmy pewni na 100% struktury
    kategorie: list[str] = Field(default_factory=list, description="Kategorie, np. Transport")
    beneficjent: str | None = None
    program: str | None = None
    dzialanie: str | None = None
    fundusz: str | None = None
    perspective: str | None = None

    #finanse trzymamy jako tekst bo chroni to przed utratą danych w przypadku anomalii w formatowaniu
    total_value_str: str | None = None
    eu_funding_str: str | None = None


    wojewodztwa: list[str] = Field(default_factory=list, description="Województwa projektu lub ogólnopolskie")

    #powiat na 100% bywa pusty, tutaj więc nie będzie blokady walidacji
    powiaty: list[str] = Field(default_factory=list, description="Powiaty projektu")

    opis: str | None = None

    #pole obliczeniowe z linkiem do projektu
    @computed_field(description="Automatycznie generowany link do projektu")
    def url_projektu(self) -> str:
        if self.id_projektu == "BRAK_ID":   #TODO magic string, do poprawy, pewnie osobny constant będzie lepszy
            return "BRAK_LINKU"
        return f"https://mapadotacji.gov.pl/projekty/{self.id_projektu}/"