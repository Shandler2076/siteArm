from datetime import date

import pytest
from django.urls import reverse

from apps.journal.models import EntreeJournal, JournalImmuable
from apps.journal.services import journaliser


def _actions():
    return list(EntreeJournal.objects.order_by("pk").values_list("action", flat=True))


def test_journal_immuable(compte_technique):
    e = journaliser(compte_technique, "test", unite="national", x=1)
    e.action = "falsifie"
    with pytest.raises(JournalImmuable):
        e.save()
    with pytest.raises(JournalImmuable):
        e.delete()
    with pytest.raises(JournalImmuable):
        EntreeJournal.objects.all().delete()
    with pytest.raises(JournalImmuable):
        EntreeJournal.objects.update(action="x")
    assert EntreeJournal.objects.get().action == "test"


def test_page_reservee_au_bn(client, client_technique, monde):
    client.force_login(monde["sec_p1"].compte)
    assert client.get("/journal/").status_code == 403
    assert client_technique.get("/journal/").status_code == 200
    assert "/journal/" in client_technique.get("/").content.decode()


def test_filtres(client_technique, compte_technique, monde):
    journaliser(compte_technique, "liste_pdf", unite="paroisse-1", lignes=3)
    journaliser(monde["sec_p1"].compte, "liste_excel", unite="paroisse-2", lignes=4)
    r = client_technique.get("/journal/", {"action": "liste_excel"})
    assert [e.action for e in r.context["page"]] == ["liste_excel"]
    r = client_technique.get("/journal/", {"auteur": monde["sec_p1"].matricule})
    assert [e.action for e in r.context["page"]] == ["liste_excel"]
    r = client_technique.get("/journal/", {"q": "paroisse-1"})
    assert [e.action for e in r.context["page"]] == ["liste_pdf"]
    aujourdhui = date.today().isoformat()
    r = client_technique.get("/journal/", {"du": aujourdhui, "au": aujourdhui})
    assert r.context["page"].paginator.count >= 2
    r = client_technique.get("/journal/", {"du": "2000-01-01", "au": "2000-01-02"})
    assert r.context["page"].paginator.count == 0
    assert client_technique.get("/journal/", {"du": "abc"}).status_code == 200


def test_connexion_journalisee(client, compte_technique):
    client.post("/connexion/", {"username": "tech", "password": "faux"})
    client.post("/connexion/", {"username": "tech", "password": "MotDePasse!2026"})
    echec, ok = EntreeJournal.objects.order_by("pk")
    assert echec.action == "connexion_echouee" and echec.details["identifiant"] == "TECH"
    assert ok.action == "connexion" and ok.auteur == compte_technique


def test_consultation_fiche_journalisee(client, client_technique, monde):
    m1 = monde["m1"]
    client.force_login(monde["sec_p1"].compte)
    client.get(f"/bureau/paroisse-{monde['P1'].pk}/membres/{m1.matricule}/")
    client_technique.get(f"/membres/bn/{m1.matricule}/")
    e1, e2 = EntreeJournal.objects.filter(action="consultation_fiche").order_by("pk")
    assert e1.details["membre"] == m1.matricule and e1.auteur == monde["sec_p1"].compte
    assert e2.unite == "national"


def test_coordonnees_ancienne_nouvelle_valeur(client, monde):
    m1 = monde["m1"]
    client.force_login(m1.compte)
    donnees = {
        "telephone": "0161000000",
        "whatsapp": "",
        "email": "",
        "quartier": "Akpakpa",
        "ville": "",
        "profession": "",
        "urgence_nom": "",
        "urgence_telephone": "",
    }
    assert client.post("/membres/ma-fiche/coordonnees/", donnees).status_code == 302
    e = EntreeJournal.objects.get(action="coordonnees")
    assert e.details["membre"] == m1.matricule
    assert e.details["changements"]["telephone"] == ["0197000000", "0161000000"]
    assert e.details["changements"]["quartier"] == ["", "Akpakpa"]
    assert "ville" not in e.details["changements"]


def test_reinitialisation_journalisee(client_technique, monde):
    m1 = monde["m1"]
    url = reverse("bureaux:reinitialiser", args=["national", m1.matricule])
    client_technique.post(url)
    assert EntreeJournal.objects.filter(action="reinitialisation").get().details["membre"] == (
        m1.matricule
    )


def test_installation_et_enregistrement_journalises(monde, compte_technique):
    from apps.bureaux.models import Fonction
    from apps.bureaux.perimetre import Unite
    from apps.bureaux.services import installer_bureau

    installer_bureau(
        unite=Unite("paroisse", monde["P2"]),
        titulaires={Fonction.objects.get(nom="Secrétaire paroissial"): monde["m2"]},
        date_debut=date(2026, 1, 1),
        par=compte_technique,
    )
    assert "installation_bureau" in _actions()
    assert "enregistrement" in _actions()  # les membres du monde ont été enregistrés
