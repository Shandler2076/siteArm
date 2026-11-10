def test_admin_membre_sans_ajout_ni_suppression(admin_client_tech, membre_enregistre):
    m = membre_enregistre.membre
    assert admin_client_tech.get("/gestion/membres/membre/add/").status_code == 403
    assert admin_client_tech.get(f"/gestion/membres/membre/{m.pk}/delete/").status_code == 403
    html = admin_client_tech.get(f"/gestion/membres/membre/{m.pk}/change/").content.decode()
    assert 'name="matricule"' not in html and 'name="annee_integration"' not in html
    assert 'name="paroisse_integration"' not in html and 'name="region_integration"' not in html


def test_admin_compteur_lecture_seule(admin_client_tech, membre_enregistre):
    assert admin_client_tech.get("/gestion/membres/compteurmatricule/add/").status_code == 403
    r = admin_client_tech.get("/gestion/membres/compteurmatricule/")
    assert r.status_code == 200 and "2015" in r.content.decode()


def test_admin_recherche_par_matricule(admin_client_tech, membre_enregistre):
    r = admin_client_tech.get("/gestion/membres/membre/?q=2015-03AS")
    assert "HOUNKP" in r.content.decode().upper()
