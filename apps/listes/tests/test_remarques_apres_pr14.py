"""Remarques du 13/11/2026 après la PR #14 : matricule cliquable, matricule à l'accueil."""

from django.test import Client


def test_matricule_ouvre_la_fiche_dans_l_espace_du_bureau(monde):
    c = Client()
    c.force_login(monde["sec_p1"].compte)
    cle = f"paroisse-{monde['P1'].pk}"
    html = c.get(f"/bureau/{cle}/listes/?envoye=1&statut=actif").content.decode()
    m1 = monde["m1"]
    assert f'href="/bureau/{cle}/membres/{m1.matricule}/"' in html
    assert c.get(f"/bureau/{cle}/membres/{m1.matricule}/").status_code == 200


def test_matricule_a_l_accueil(monde):
    c = Client()
    c.force_login(monde["m1"].compte)
    html = c.get("/").content.decode()
    assert monde["m1"].matricule in html and "accueil-matricule" in html
