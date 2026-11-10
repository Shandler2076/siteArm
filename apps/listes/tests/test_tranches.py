import pytest

from apps.journal.models import EntreeJournal
from apps.listes.models import ReglageStatistiques

URL = "/bureau/bn/tranches-age/"


def test_reserve_au_bn(client, client_technique, monde):
    client.force_login(monde["sec_p1"].compte)
    assert client.get(URL).status_code == 403
    assert client.post(URL, {"bornes": "10"}).status_code == 403
    assert client_technique.get(URL).status_code == 200


def test_modifier(client_technique, compte_technique, monde):
    r = client_technique.post(URL, {"bornes": " 18, 40 ,60"})
    assert r.status_code == 302
    assert ReglageStatistiques.courant().bornes == "18,40,60"
    html = client_technique.get("/bureau/national/statistiques/").content.decode()
    assert "41 à 60 ans" in html and "Plus de 60 ans" in html
    (e,) = EntreeJournal.objects.all()
    assert e.action == "tranches_age" and e.auteur == compte_technique
    assert e.details == {"avant": "18,40", "apres": "18,40,60"}


@pytest.mark.parametrize("saisie", ["", "40,18", "18,18", "abc", "0", "121", "1,2,3,4,5,6,7"])
def test_refus(client_technique, saisie):
    r = client_technique.post(URL, {"bornes": saisie})
    assert r.status_code == 200 and "erreur" in r.content.decode()
    assert ReglageStatistiques.courant().bornes == "18,40"
    assert not EntreeJournal.objects.exists()


def test_lien_accueil(client_technique):
    html = client_technique.get("/").content.decode()
    assert URL in html and "/bureau/national/listes/" in html
    assert "/bureau/national/statistiques/" in html


def test_liens_nationaux_seulement_si_espace_national(client, monde):
    from django.contrib.auth.models import Permission

    compte = monde["m1"].compte
    compte.user_permissions.add(Permission.objects.get(codename="gerer_membres"))
    client.force_login(compte)
    html = client.get("/").content.decode()
    assert URL in html  # pages BN de transition : oui
    assert "/bureau/national/listes/" not in html  # espace national (gardien) : non
    assert client.get("/bureau/national/listes/").status_code == 404
