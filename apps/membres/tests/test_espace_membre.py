def test_ma_fiche_affiche_parcours(client_membre, membre_enregistre):
    html = client_membre.get("/membres/ma-fiche/").content.decode()
    assert "2015-03AS-0001" in html and "Intégration" in html and "Ekpe A" in html
    assert "Membre actif" in html


def test_accueil_propose_ma_fiche(client_membre):
    assert "/membres/ma-fiche/" in client_membre.get("/").content.decode()


def test_modifier_coordonnees_ignore_les_champs_proteges(client_membre, membre_enregistre):
    r = client_membre.post("/membres/ma-fiche/coordonnees/", {
        "telephone": "0161000000", "ville": "Porto-Novo",
        "nom": "PIRATE", "matricule": "2099-99AS-9999", "annee_integration": "2000",
        "categorie": "honneur", "statut": "decede",
    })
    assert r.status_code == 302
    m = membre_enregistre.membre
    m.refresh_from_db()
    assert m.telephone == "0161000000" and m.ville == "Porto-Novo"
    assert m.nom == "Hounkpè" and m.matricule == "2015-03AS-0001" and m.annee_integration == 2015
    assert m.categorie == "actif" and m.statut == "actif"


def test_telephone_invalide_refuse(client_membre, membre_enregistre):
    r = client_membre.post("/membres/ma-fiche/coordonnees/", {"telephone": "abc"})
    assert r.status_code == 200 and "invalide" in r.content.decode()


def test_membre_n_accede_pas_aux_pages_bn(client_membre, membre_enregistre):
    assert client_membre.get("/membres/bn/2015-03AS-0001/").status_code == 403
    assert client_membre.get("/membres/bn/2015-03AS-0001/fiche.pdf").status_code == 403


def test_compte_sans_membre_404(admin_client_tech):
    assert admin_client_tech.get("/membres/ma-fiche/").status_code == 404


def test_ma_fiche_pdf(client_membre):
    r = client_membre.get("/membres/ma-fiche/fiche.pdf")
    assert r.status_code == 200 and r.content.startswith(b"%PDF")
