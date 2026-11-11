from html import unescape


def test_page_publique(client, db):
    r = client.get("/protection-des-donnees/")
    html = unescape(r.content.decode())
    assert r.status_code == 200
    for titre in (
        "Protection de vos données",
        "Qui est responsable",
        "Quelles données",
        "Pourquoi",
        "Qui y a accès",
        "Combien de temps",
        "Où sont-elles hébergées",
        "Comment sont-elles protégées",
        "Vos droits",
        "APDP",
    ):
        assert titre in html, titre
    assert "photo du CIP" in html and "Bureau national" in html.replace(
        "Bureau National", "Bureau national"
    )


def test_liens_vers_la_page(client, monde):
    assert "/protection-des-donnees/" in client.get("/").content.decode()
    assert "/protection-des-donnees/" in client.get("/connexion/").content.decode()
    client.force_login(monde["m1"].compte)
    assert "/protection-des-donnees/" in client.get("/membres/ma-fiche/").content.decode()


def test_contact_configurable(client, db, settings):
    settings.CONTACT_DONNEES = "donnees@exemple.bj"
    assert "donnees@exemple.bj" in client.get("/protection-des-donnees/").content.decode()
