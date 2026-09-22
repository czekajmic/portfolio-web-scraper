import pytest
from pydantic import ValidationError
from src.models import ProjectDetails
from src.config import UNKNOWN_ID_FLAG, UNKNOWN_TITLE_FLAG, UNKNOWN_LINK_FLAG, INVALID_PROJECT_ERROR_MESSAGE

#test 1: czy prawidłowe dane przechodzą?

def test_project_details_valid_creation():
    fake_id = "12345"
    fake_title= "Budowa stacji kosmicznej"

    project = ProjectDetails(id_projektu=fake_id, tytul=fake_title)

    assert project.id_projektu == "12345"
    assert project.tytul == "Budowa stacji kosmicznej"
    assert project.url_projektu == "https://mapadotacji.gov.pl/projekty/12345/"

#test 2: czy zabezpieczenie dla śmieciowych linków działa?
def test_project_details_rejects_garbage():
    with pytest.raises(ValidationError, match=INVALID_PROJECT_ERROR_MESSAGE):
        ProjectDetails(
            id_projektu=UNKNOWN_ID_FLAG,
            tytul=UNKNOWN_TITLE_FLAG
        )