import datetime


def test_accueil_selon_les_mandats(client, monde, donner_mandat):
    client.force_login(monde["sec_p1"].compte)
    html = client.get("/").content.decode()
    assert "Espace bureau — Paroisse P1" in html and "Installer un bureau" not in html
    assert "Ma fiche" in html
    donner_mandat(monde["sec_p1"], "Président", None, debut=datetime.date(2025, 1, 1))
    html = client.get("/").content.decode()
    for lien in ["Installer un bureau", "Fonctions et droits", "Mandats à échéance",
                 "Enregistrer un membre", "Photos à valider", "Espace bureau — Paroisse P1"]:
        assert lien in html, lien


def test_accueil_membre_simple(client, monde):
    client.force_login(monde["m1"].compte)
    html = client.get("/").content.decode()
    assert "Ma fiche" in html and "Espace bureau" not in html and "Installer" not in html
