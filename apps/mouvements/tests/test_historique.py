from datetime import date
from html import unescape

from apps.mouvements.statuts import changer_categorie, changer_statut


def test_historique_visible_partout(client, client_technique, monde):
    m1 = monde["m1"]
    changer_categorie(
        m1, "honneur", par=None, date_effet=date(2026, 11, 5), motif="Validé par le BN"
    )
    attendu = "Catégorie : Membre actif → Membre d'honneur"
    pages = []
    client.force_login(monde["sec_p1"].compte)
    pages.append(client.get(f"/bureau/paroisse-{monde['P1'].pk}/membres/{m1.matricule}/"))
    pages.append(client_technique.get(f"/membres/bn/{m1.matricule}/"))
    client.force_login(m1.compte)
    pages.append(client.get("/membres/ma-fiche/"))
    for r in pages:
        html = unescape(r.content.decode())
        assert r.status_code == 200 and "Historique" in html and attendu in html
        assert "05/11/2026" in html and "Validé par le BN" in html


def test_historique_vide(client, monde):
    client.force_login(monde["m1"].compte)
    assert "Aucun événement." in client.get("/membres/ma-fiche/").content.decode()


def test_deces_affiche_date(client_technique, monde):
    m1 = monde["m1"]
    changer_statut(m1, "decede", par=None, date_effet=date(2026, 11, 1), motif="Décès confirmé")
    html = unescape(client_technique.get(f"/membres/bn/{m1.matricule}/").content.decode())
    assert "Décédé le 01/11/2026" in html


def test_historique_pas_chez_un_autre_membre(client, monde):
    client.force_login(monde["m2"].compte)
    assert client.get(f"/membres/bn/{monde['m1'].matricule}/").status_code == 403
