"""Statistiques par grade, tableaux croisés et filtres de page (module 2, étape 1)."""

import io
from datetime import date
from urllib.parse import urlencode

from django.http import QueryDict

from apps.bureaux.models import Niveau
from apps.bureaux.perimetre import Unite
from apps.listes.filtres import FiltreListeForm, membres_filtres
from apps.listes.statistiques import calculer_statistiques, calculer_tableaux
from apps.listes.tests.test_grades import _situer

J = date(2026, 11, 10)
NATIONAL = Unite(Niveau.NATIONAL, None)


def _compte_liste(unite, filtres):
    form = FiltreListeForm(unite, QueryDict(urlencode(filtres, doseq=True)))
    assert form.is_valid(), form.errors
    return membres_filtres(unite, form.cleaned_data, J).count()


def test_par_grade_compte_juste(monde):
    _situer(monde)
    s = {x.titre: x for x in calculer_statistiques(NATIONAL, ["actif"], J)}
    chiffres = {c.libelle: c.nombre for c in s["Par grade"].cellules}
    assert chiffres["Capitaine"] == 3
    assert chiffres["Senior Capitaine"] == 1
    assert chiffres["Commandant"] == 1
    assert chiffres["Camarade"] == 1
    assert chiffres["Grade non renseigné"] == 1
    assert chiffres["Supérieur Suprême Spirituel"] == 0


def test_chaque_cellule_croisee_egale_sa_liste(monde):
    _situer(monde)
    base = {"region": str(monde["HOULENOU"].pk), "age": "plus", "age_x": "40"}
    tableaux = calculer_tableaux(NATIONAL, ["actif"], J, base)
    assert [t.titre for t in tableaux] == [
        "Grade × tranche d'âge",
        "Grade × sexe",
        "Grade × région",
    ]
    vues = 0
    for t in tableaux:
        for _libelle, cellules in t.lignes:
            for c in cellules:
                assert c.nombre == _compte_liste(NATIONAL, c.filtres), (t.titre, c.filtres)
                vues += 1
    assert vues > 10
    # Région HOULENOU et plus de 40 ans : Adjovi (Capitaine 45 ans) et Chabi (Senior Capitaine).
    regions = tableaux[2]
    lignes = {lib: cellules for lib, cellules in regions.lignes}
    assert set(lignes) == {"Capitaine", "Senior Capitaine"}


def test_filtres_de_page_s_appliquent_a_toutes_les_sections(monde):
    _situer(monde)
    base = {"grade": ["5"]}
    s = {x.titre: x for x in calculer_statistiques(NATIONAL, ["actif"], J, base)}
    assert s["Total"].cellules[0].nombre == 3
    sexes = {c.libelle: c.nombre for c in s["Par sexe"].cellules}
    assert sexes == {"Hommes": 3, "Femmes": 0}
    for section in s.values():
        for c in section.cellules:
            assert c.nombre == _compte_liste(NATIONAL, c.filtres)


def test_paroisse_sans_tableau_unites_inferieures(monde):
    _situer(monde)
    tableaux = calculer_tableaux(Unite(Niveau.PAROISSE, monde["P1"]), ["actif"], J, {})
    assert [t.titre for t in tableaux] == ["Grade × tranche d'âge", "Grade × sexe"]


def test_page_et_pdf_statistiques(monde, client):
    from pypdf import PdfReader

    _situer(monde)
    client.force_login(monde["chef"].compte)  # Chef de Section de Circuit (Ekpe A)
    base = f"/bureau/circuit-{monde['Ekpe A'].pk}/statistiques/"
    r = client.get(base + "?envoye=1&statut=actif&grade_min=5")
    html = r.content.decode()
    assert r.status_code == 200 and "Par grade" in html and "Grade × sexe" in html
    assert "grade_min=5" in html  # les liens des chiffres gardent les filtres de page
    r = client.get(base + "pdf/?envoye=1&statut=actif")
    texte = "".join(p.extract_text() for p in PdfReader(io.BytesIO(r.content)).pages)
    assert "Par grade" in texte and "Grade × paroisse" in texte and "Capitaine" in texte
