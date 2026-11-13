"""Statistiques à paramètres (décisions du mainteneur du 13/11/2026)."""

from html import unescape
from urllib.parse import parse_qs, urlparse

URL = "/bureau/national/statistiques/"


def _html(client, url):
    r = client.get(url)
    assert r.status_code == 200
    return unescape(r.content.decode())


def test_page_a_parametres_sans_tableaux_croises(client_technique, monde):
    html = _html(client_technique, URL)
    assert "Paramètres de la statistique" in html and "Générer la statistique" in html
    assert '<table class="croise">' not in html
    # Répartitions en sous-cases repliées.
    assert '<details class="repartition">' in html and "Par grade" in html
    assert "Âge de début" in html and "Âge de fin" in html


def test_parametres_croises_et_colonnes(client_technique, monde):
    from apps.membres.models import Membre

    Membre.objects.filter(pk=monde["m1"].pk).update(grade=5)
    region = monde["HOULENOU"].pk
    html = _html(client_technique, f"{URL}?envoye=1&statut=actif&grade=5&region={region}")
    debut = html.index('class="resultat"')
    bloc = html[debut : html.index("</a>", debut)]
    assert ">1<" in bloc  # un seul Capitaine (grade 5) dans la région HOULENOU
    lien = bloc[bloc.index('href="') + 6 :]
    lien = lien[: lien.index('"')]
    colonnes = parse_qs(urlparse(lien).query)["colonnes"]
    assert colonnes[:5] == ["matricule", "nom", "prenoms", "sexe", "telephone"]
    assert "grade" in colonnes
    assert "paroisse" not in colonnes and "age" not in colonnes  # paramètres non choisis


def test_age_de_debut_et_de_fin(client_technique, monde):
    html = _html(client_technique, f"{URL}?envoye=1&statut=actif&age_x=30&age_y=40")
    debut = html.index('class="resultat"')
    lien = html[html.index('href="', debut) + 6 :]
    lien = lien[: lien.index('"')]
    q = parse_qs(urlparse(lien).query)
    assert q["age"] == ["entre"] and q["age_x"] == ["30"] and q["age_y"] == ["40"]
    assert "age" in q["colonnes"]


def test_chiffre_d_une_repartition_garde_les_colonnes(client_technique, monde):
    html = _html(client_technique, f"{URL}?envoye=1&statut=actif&sexe=M")
    i = html.index("Par grade")
    lien = html[html.index('href="', i) + 6 :]
    lien = lien[: lien.index('"')]
    colonnes = parse_qs(urlparse(lien).query)["colonnes"]
    assert "grade" in colonnes and "sexe" in colonnes
