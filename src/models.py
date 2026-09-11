from pydantic import BaseModel, Field

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
