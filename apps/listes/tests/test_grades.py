"""Listes : filtre et colonnes grade, membres éligibles (module 2, étape 1)."""

from datetime import date
from urllib.parse import urlencode

from django.http import QueryDict

from apps.bureaux.models import Niveau
from apps.bureaux.perimetre import Unite
from apps.listes.colonnes import lignes, preparer
from apps.listes.filtres import FiltreListeForm, membres_filtres, resume_filtres
from apps.membres.models import Membre

J = date(2026, 11, 10)
NATIONAL = Unite(Niveau.NATIONAL, None)


def _form(unite, **data):
    return FiltreListeForm(unite, QueryDict(urlencode(data | {"envoye": "1"}, doseq=True)))


def _noms(unite, **data):
    form = _form(unite, **data)
    assert form.is_valid(), form.errors
    return sorted(m.nom for m in membres_filtres(unite, form.cleaned_data, J))


def _situer(monde):
    """Adjovi (P1, HOULENOU) Capitaine 45 ans ; Bio (P2) Capitaine 30 ans ; Chabi (P3) Senior
    Capitaine 50 ans ; Dossou (P4, WEME) Capitaine 60 ans ; Secretaire : Commandant ;
    Chef : Camarade ; Tresorier : sans grade."""
    reglages = {
        "m1": (5, date(1981, 1, 1), date(2015, 1, 1)),
        "m2": (5, date(1996, 1, 1), date(2025, 1, 1)),
        "m3": (6, date(1976, 1, 1), date(2010, 1, 1)),
        "m4": (5, date(1966, 1, 1), date(2015, 1, 1)),
        "sec_p1": (7, None, date(2020, 1, 1)),
        "chef": (0, None, date(2026, 1, 1)),
        "tresorier": (None, None, None),
    }
    for cle, (grade, naissance, depuis) in reglages.items():
        Membre.objects.filter(pk=monde[cle].pk).update(
            grade=grade, date_naissance=naissance, date_grade=depuis
        )


def test_filtre_grade_et_age_et_region(monde):
    _situer(monde)
    filtres = {"grade": ["5"], "age": "plus", "age_x": "40", "region": monde["HOULENOU"].pk}
    assert _noms(NATIONAL, **filtres) == ["Adjovi"]
    assert _noms(NATIONAL, grade=["5"], age="plus", age_x="40") == ["Adjovi", "Dossou"]


def test_filtre_plusieurs_grades(monde):
    _situer(monde)
    assert _noms(NATIONAL, grade=["6", "7"]) == ["Chabi", "Secretaire"]


def test_filtre_grade_min(monde):
    _situer(monde)
    assert _noms(NATIONAL, grade_min="5") == ["Adjovi", "Bio", "Chabi", "Dossou", "Secretaire"]
    assert _noms(NATIONAL, grade_min="6") == ["Chabi", "Secretaire"]


def test_filtre_grade_non_renseigne_et_camarade(monde):
    _situer(monde)
    assert _noms(NATIONAL, grade=["aucun"]) == ["Tresorier"]
    assert _noms(NATIONAL, grade=["0"]) == ["Chef"]


def test_filtre_eligible(monde):
    _situer(monde)
    # Capitaine depuis 2015 (5 ans requis) : oui ; depuis 2025 : non ; Senior Capitaine et
    # Commandant : par nomination, hors liste ; Camarade : oui ; sans grade : non.
    assert _noms(NATIONAL, eligible="on") == ["Adjovi", "Chef", "Dossou"]


def test_colonnes_grade(monde):
    _situer(monde)
    qs = preparer(Membre.objects.filter(pk=monde["m1"].pk), J)
    assert list(lignes(qs, ["nom", "grade", "date_grade"], J)) == [
        ["Adjovi", "Capitaine", "01/01/2015"]
    ]
    qs = preparer(Membre.objects.filter(pk=monde["tresorier"].pk), J)
    assert list(lignes(qs, ["grade"], J)) == [[None]]


def test_resume_filtres_mentionne_grade(monde):
    form = _form(NATIONAL, grade=["5", "aucun"], grade_min="7", eligible="on")
    assert form.is_valid(), form.errors
    resume = resume_filtres(form)
    assert "Grade : Capitaine, Grade non renseigné" in resume
    assert "Grade : à partir de Commandant" in resume
    assert "Éligibles au grade suivant" in resume


def test_export_excel_colonne_grade(monde, client):
    import io

    from openpyxl import load_workbook

    _situer(monde)
    client.force_login(monde["sec_p1"].compte)
    r = client.get(
        f"/bureau/paroisse-{monde['P1'].pk}/listes/excel/?"
        + urlencode({"envoye": "1", "colonnes": ["matricule", "nom", "grade"]}, doseq=True)
    )
    assert r.status_code == 200
    ws = load_workbook(io.BytesIO(r.content)).active
    valeurs = [c.value for ligne in ws.iter_rows() for c in ligne]
    assert "Grade" in valeurs and "Capitaine" in valeurs and "Commandant" in valeurs
