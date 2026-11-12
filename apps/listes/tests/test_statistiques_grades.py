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
    base = {"grade_min": "1", "categorie": "actif"}
    tableaux = calculer_tableaux(NATIONAL, ["actif"], J, base)
    assert [t.titre for t in tableaux] == [
        "Grade × tranche d'âge",
        "Grade × sexe",
        "Grade × région",
    ]
    vues = 0
    for t in tableaux:
        for _libelle, cellules in t.lignes:
            *colonnes, total = cellules
            assert sum(c.nombre for c in colonnes) == total.nombre, t.titre
            for c in cellules:
                assert c.nombre == _compte_liste(NATIONAL, c.filtres), (t.titre, c.filtres)
                vues += 1
    assert vues > 10
    # Camarade (Chef) et sans grade (Tresorier) exclus par « à partir de Soldat de 3ᵉ classe ».
    lignes = {lib for lib, _c in tableaux[2].lignes}
    assert lignes == {"Capitaine", "Senior Capitaine", "Commandant"}


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


def test_dimension_fixee_par_la_page_n_est_pas_redetaillee(monde):
    """Revue finale I-1 : un filtre de page n'est jamais remplacé par celui d'une colonne."""
    _situer(monde)
    base = {"region": str(monde["HOULENOU"].pk), "age": "plus", "age_x": "40"}
    s = {x.titre: x for x in calculer_statistiques(NATIONAL, ["actif"], J, base)}
    assert "Par tranche d'âge" not in s and "Par région" not in s
    total = s["Total"].cellules[0].nombre
    assert sum(c.nombre for c in s["Par sexe"].cellules) == total
    tableaux = calculer_tableaux(NATIONAL, ["actif"], J, base)
    assert [t.titre for t in tableaux] == ["Grade × sexe"]
    for _lib, cellules in tableaux[0].lignes:
        *colonnes, total_ligne = cellules
        assert sum(c.nombre for c in colonnes) == total_ligne.nombre
    s = {x.titre: x for x in calculer_statistiques(NATIONAL, ["actif"], J, {"sexe": "F"})}
    assert "Par sexe" not in s
