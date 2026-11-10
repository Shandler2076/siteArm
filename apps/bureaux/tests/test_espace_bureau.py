import datetime

from apps.membres.models import Affectation


def _client(client, membre):
    client.force_login(membre.compte)
    return client


def test_espace_bureau_liste_son_perimetre(client, monde):
    html = _client(client, monde["sec_p1"]).get("/bureau/", follow=True).content.decode()
    assert "ADJOVI" in html and "BIO" not in html


def test_une_seule_unite_redirige(client, monde):
    r = _client(client, monde["sec_p1"]).get("/bureau/")
    assert r.status_code == 302 and r.url == f"/bureau/paroisse-{monde['P1'].pk}/membres/"


def test_plusieurs_unites_choix(client, monde, donner_mandat):
    donner_mandat(monde["sec_p1"], "Coordinateur régional", monde["WEME"])
    html = _client(client, monde["sec_p1"]).get("/bureau/").content.decode()
    assert "Paroisse P1" in html and "Région WEME" in html


def test_unite_non_geree_404(client, monde):
    c = _client(client, monde["sec_p1"])
    assert c.get(f"/bureau/circuit-{monde['Ekpe A'].pk}/membres/").status_code == 404
    assert c.get("/bureau/national/membres/").status_code == 404


def test_fiche_hors_perimetre_404(client, monde):
    c = _client(client, monde["sec_p1"])
    cle = f"paroisse-{monde['P1'].pk}"
    r = c.get(f"/bureau/{cle}/membres/{monde['m1'].matricule}/")
    assert r.status_code == 200 and "Intégration" in r.content.decode()
    assert c.get(f"/bureau/{cle}/membres/{monde['m3'].matricule}/").status_code == 404


def test_fiche_sans_cip(client, monde):
    from django.core.files.base import ContentFile

    m1 = monde["m1"]
    m1.photo_cip.save("cip.jpg", ContentFile(b"x"))
    html = (
        _client(client, monde["sec_p1"])
        .get(f"/bureau/paroisse-{monde['P1'].pk}/membres/{m1.matricule}/")
        .content.decode()
    )
    assert "/cip/" not in html and "CIP" not in html


def test_membre_simple_sans_espace_bureau(client, monde):
    assert _client(client, monde["m1"]).get("/bureau/").status_code == 403


def test_anciens_membres_sans_coordonnees(client, monde):
    m1 = monde["m1"]
    m1.telephone = "0199887766"
    m1.save()
    a = m1.affectation_actuelle
    a.date_fin = datetime.date(2026, 11, 10)
    a.save()
    Affectation.objects.create(
        membre=m1,
        paroisse=monde["P4"],
        circuit_a_date=monde["Dangbo A"],
        region_a_date=monde["WEME"],
        date_debut=datetime.date(2026, 11, 10),
        motif="Mutation",
    )
    html = (
        _client(client, monde["sec_p1"])
        .get(f"/bureau/paroisse-{monde['P1'].pk}/anciens/")
        .content.decode()
    )
    assert m1.matricule in html and "P4" in html and "0199887766" not in html


def test_recherche(client, monde):
    html = (
        _client(client, monde["chef"])
        .get(f"/bureau/circuit-{monde['Ekpe A'].pk}/membres/?q=bio")
        .content.decode()
    )
    assert "BIO" in html and "ADJOVI" not in html


def test_bn_voit_toute_unite(client_technique, monde):
    html = client_technique.get(f"/bureau/circuit-{monde['Ekpe B'].pk}/membres/").content.decode()
    assert "CHABI" in html
