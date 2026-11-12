import datetime
import io
from html import unescape

import pytest
from django.test import Client

from apps.grades.models import HistoriqueGrade, ModeGrade
from apps.membres.models import Membre

D = datetime.date


def _poser(membre, grade, depuis):
    Membre.objects.filter(pk=membre.pk).update(grade=grade, date_grade=depuis)
    HistoriqueGrade.objects.create(
        membre=membre, grade=grade, date_effet=depuis, mode=ModeGrade.REGULARISATION
    )
    membre.refresh_from_db()
    return membre


def _client(membre):
    c = Client()
    c.force_login(membre.compte)
    return c


def _html(r):
    return unescape(r.content.decode())


def test_ma_fiche_affiche_grade_et_historique(monde):
    m = _poser(monde["m1"], 5, D(2018, 3, 15))
    html = _html(_client(m).get("/membres/ma-fiche/"))
    assert "Capitaine Test ADJOVI" in html
    assert "Grades" in html and "15/03/2018" in html and "Régularisation" in html


def test_fiche_bureau_affiche_grade(monde):
    m = _poser(monde["m1"], 6, D(2018, 3, 15))
    r = _client(monde["sec_p1"]).get(f"/bureau/paroisse-{monde['P1'].pk}/membres/{m.matricule}/")
    assert r.status_code == 200 and "Senior Capitaine" in _html(r)


def test_pdf_contient_grade(monde):
    from pypdf import PdfReader

    from apps.membres.pdf import fiche_identification_pdf

    m = _poser(monde["m1"], 5, D(2018, 3, 15))
    texte = "".join(
        p.extract_text() for p in PdfReader(io.BytesIO(fiche_identification_pdf(m))).pages
    )
    assert "Grade" in texte and "Capitaine" in texte


def test_promouvoir_bn_ok(monde, client_technique):
    m = _poser(monde["m1"], 1, D(2019, 1, 1))
    url = f"/grades/bn/{m.matricule}/promouvoir/"
    assert client_technique.get(url).status_code == 200
    r = client_technique.post(
        url, {"grade": "2", "date_effet": "2024-01-01", "reference": "Décision 7"}, follow=True
    )
    assert "Grade enregistré" in _html(r)
    m.refresh_from_db()
    assert m.grade == 2


def test_promouvoir_refuse_affiche_message(monde, client_technique):
    m = _poser(monde["m1"], 1, D(2023, 1, 1))
    r = client_technique.post(
        f"/grades/bn/{m.matricule}/promouvoir/",
        {"grade": "2", "date_effet": "2024-01-01", "reference": "Décision 7"},
    )
    assert r.status_code == 200 and "3 ans" in _html(r)


def test_corriger_bn(monde, client_technique):
    m = _poser(monde["m1"], 5, D(2019, 1, 1))
    r = client_technique.post(
        f"/grades/bn/{m.matricule}/corriger/",
        {"grade": "4", "date_effet": "2019-01-01", "motif": "Erreur de saisie"},
    )
    assert r.status_code == 302
    m.refresh_from_db()
    assert m.grade == 4


@pytest.mark.parametrize("qui", ["chef", "m1"])
def test_pages_grades_interdites_hors_bn(monde, qui):
    c = _client(monde[qui])
    m = monde["m2"]
    for url in (
        f"/grades/bn/{m.matricule}/promouvoir/",
        f"/grades/bn/{m.matricule}/corriger/",
        "/grades/bn/serie/",
    ):
        assert c.get(url).status_code == 403


def test_serie(monde, client_technique):
    a = _poser(monde["m1"], 1, D(2019, 1, 1))
    b = _poser(monde["m2"], 1, D(2019, 6, 1))
    trop_tot = _poser(monde["m3"], 1, D(2025, 1, 1))
    _poser(monde["m4"], 0, D(2025, 1, 1))
    html = _html(client_technique.get("/grades/bn/serie/?grade=2"))
    assert a.nom_complet in html and trop_tot.nom_complet in html
    assert "Camarade Test DOSSOU" not in html
    assert "Camarade Test DOSSOU" in _html(client_technique.get("/grades/bn/serie/?grade=1"))
    donnees = {"grade": "2", "date_effet": "2024-01-01", "reference": "Test du 01/12/2023"}
    r = client_technique.post(
        "/grades/bn/serie/?grade=2", {**donnees, "membres": [a.pk, trop_tot.pk]}
    )
    assert r.status_code == 200 and trop_tot.nom_complet in _html(r)
    assert Membre.objects.get(pk=a.pk).grade == 1
    r = client_technique.post("/grades/bn/serie/?grade=2", {**donnees, "membres": [a.pk, b.pk]})
    assert r.status_code == 302
    assert set(Membre.objects.filter(pk__in=[a.pk, b.pk]).values_list("grade", flat=True)) == {2}


def test_serie_region_invalide_pas_d_erreur(monde, client_technique):
    assert client_technique.get("/grades/bn/serie/?grade=2&region=abc").status_code == 200


def test_serie_grade_impose_par_la_page(monde, client_technique):
    """Revue finale M-3 : le grade promu est celui de la liste affichée, pas un autre."""
    a = _poser(monde["m1"], 1, D(2019, 1, 1))
    client_technique.post(
        "/grades/bn/serie/?grade=2",
        {"grade": "9", "date_effet": "2024-01-01", "reference": "R", "membres": [a.pk]},
    )
    assert Membre.objects.get(pk=a.pk).grade == 2
