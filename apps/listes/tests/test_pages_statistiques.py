import io

import pytest
from pypdf import PdfReader

from apps.journal.models import EntreeJournal


def _url(monde, niveau, cle):
    return f"/bureau/{niveau}-{monde[cle].pk}/statistiques/"


def test_acces_statistiques(client, monde):
    client.force_login(monde["sec_p1"].compte)
    assert client.get(_url(monde, "paroisse", "P1")).status_code == 200
    assert client.get(_url(monde, "paroisse", "P2")).status_code == 404
    assert client.get(_url(monde, "circuit", "Ekpe A")).status_code == 404
    for qui in ("m1", "tresorier"):
        client.force_login(monde[qui].compte)
        assert client.get(_url(monde, "paroisse", "P1")).status_code == 404


@pytest.mark.parametrize("statuts", ["", "statut=actif&statut=decede&envoye=1", "envoye=1"])
def test_chaque_lien_donne_le_meme_nombre(client_technique, monde, statuts):
    monde["m2"].statut = "decede"
    monde["m2"].save()
    urls = [
        _url(monde, "paroisse", "P1"),
        _url(monde, "circuit", "Ekpe A"),
        _url(monde, "region", "HOULENOU"),
        "/bureau/national/statistiques/",
    ]
    for url in urls:
        r = client_technique.get(url + "?" + statuts)
        assert r.status_code == 200
        html = r.content.decode()
        assert len(r.context["sections"]) >= 5
        for section in r.context["sections"]:
            for c in section.cellules:
                assert c.lien.replace("&", "&amp;") in html
                liste = client_technique.get(c.lien)
                assert liste.context["page"].paginator.count == c.nombre, (url, c.libelle)


def test_statuts_par_defaut(client_technique, monde):
    monde["m2"].statut = "decede"
    monde["m2"].save()
    r = client_technique.get("/bureau/national/statistiques/")
    total = r.context["sections"][0].cellules[0]
    assert total.nombre == 6
    r = client_technique.get("/bureau/national/statistiques/?envoye=1")
    assert r.context["sections"][0].cellules[0].nombre == 7


def test_export_pdf_statistiques(client, monde):
    client.force_login(monde["sec_p1"].compte)
    r = client.get(_url(monde, "paroisse", "P1") + "pdf/")
    assert r["Content-Type"] == "application/pdf" and "no-store" in r["Cache-Control"]
    texte = "\n".join(p.extract_text() for p in PdfReader(io.BytesIO(r.content)).pages)
    assert "ARMÉE DU SALUT DU BÉNIN" in texte and "Statistiques —" in texte
    assert "Généré le" in texte and "Total des membres" in texte and "Statut : Actif" in texte
    (e,) = EntreeJournal.objects.filter(
        action__in=["liste_pdf", "liste_excel", "statistiques_pdf", "tranches_age"]
    )
    assert e.action == "statistiques_pdf" and e.details["statuts"] == ["actif"]
    assert e.auteur == monde["sec_p1"].compte
    assert client.get(_url(monde, "paroisse", "P2") + "pdf/").status_code == 404
