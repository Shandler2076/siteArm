from apps.journal.models import LISTE_PDF
from apps.journal.services import journaliser


def test_journaliser(compte_technique):
    e = journaliser(
        compte_technique, LISTE_PDF, unite="paroisse-3", lignes=12, filtres={"sexe": "F"}
    )
    e.refresh_from_db()
    assert e.auteur == compte_technique and e.action == "liste_pdf" and e.unite == "paroisse-3"
    assert e.details == {"lignes": 12, "filtres": {"sexe": "F"}} and e.date is not None


def test_admin_lecture_seule(client_technique, compte_technique):
    journaliser(compte_technique, LISTE_PDF)
    assert client_technique.get("/gestion/journal/entreejournal/").status_code == 200
    assert client_technique.get("/gestion/journal/entreejournal/add/").status_code == 403
