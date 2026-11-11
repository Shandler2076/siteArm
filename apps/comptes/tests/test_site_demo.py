def test_bandeau_site_d_essai(client, settings):
    settings.SITE_DEMO = True
    html = client.get("/connexion/").content.decode()
    assert "Site d'essai" in html and "données fictives" in html


def test_pas_de_bandeau_en_production(client, settings):
    settings.SITE_DEMO = False
    assert "Site d'essai" not in client.get("/connexion/").content.decode()
