from datetime import date
from html import unescape

from apps.bureaux.services import libelles_fonctions


def test_libelles_fonctions_ordonnees(monde, donner_mandat):
    sec = monde["sec_p1"]
    donner_mandat(sec, "Trésorier régional", monde["HOULENOU"])
    donner_mandat(sec, "Secrétaire national adjoint")
    assert libelles_fonctions(sec.compte) == [
        "Secrétaire paroissial — Paroisse P1",
        "Trésorier régional — Région HOULENOU",
        "Secrétaire national adjoint — Bureau National de Commandement",
    ]


def test_mandat_termine_ou_futur_non_affiche(monde, donner_mandat):
    m1 = monde["m1"]
    donner_mandat(m1, "Trésorier paroissial", monde["P1"], fin=date(2025, 6, 1))
    donner_mandat(m1, "Secrétaire paroissial", monde["P2"], debut=date(2099, 1, 1))
    assert libelles_fonctions(m1.compte) == []


def test_accueil_affiche_les_fonctions(client, monde):
    client.force_login(monde["sec_p1"].compte)
    html = unescape(client.get("/").content.decode())
    assert "Secrétaire paroissial — Paroisse P1" in html
    client.force_login(monde["m1"].compte)
    assert "Membre simple" in unescape(client.get("/").content.decode())


def test_ma_fiche_affiche_les_fonctions(client, monde):
    client.force_login(monde["chef"].compte)
    html = unescape(client.get("/membres/ma-fiche/").content.decode())
    assert "Mes fonctions" in html and "Chef de Section de Circuit — Circuit Ekpe A" in html


def test_menu_bureau(client, monde):
    client.force_login(monde["sec_p1"].compte)
    cle = f"paroisse-{monde['P1'].pk}"
    html = client.get(f"/bureau/{cle}/membres/").content.decode()
    assert 'class="menu"' in html
    for chemin in ("membres", "anciens", "demandes", "listes", "statistiques"):
        assert f"/bureau/{cle}/{chemin}/" in html
    assert "/membres/ma-fiche/" in html and "/journal/" not in html


def test_menu_bn(client_technique):
    html = client_technique.get("/notifications/").content.decode()
    for lien in ("/bureau/bn/decisions/", "/membres/bn/enregistrer/", "/lots/", "/journal/"):
        assert lien in html


def test_menu_membre_simple(client, monde):
    client.force_login(monde["m1"].compte)
    html = client.get("/membres/ma-fiche/").content.decode()
    assert 'class="menu"' in html and "/bureau/" not in html and "/journal/" not in html


def test_pas_de_menu_sans_connexion(client):
    assert 'class="menu"' not in client.get("/connexion/").content.decode()


def test_bouton_retour(client, monde):
    client.force_login(monde["m1"].compte)
    assert "← Retour" in client.get("/membres/ma-fiche/").content.decode()
    assert "← Retour" not in client.get("/").content.decode()
