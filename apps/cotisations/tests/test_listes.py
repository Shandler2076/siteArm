"""Listes et statistiques : filtres et colonnes des cotisations."""

import datetime
from urllib.parse import urlencode

import pytest
from django.http import QueryDict

from apps.bureaux.models import Niveau
from apps.bureaux.perimetre import Unite
from apps.cotisations.services import saisir_versement, valider
from apps.cotisations.tests.conftest import enregistre_le
from apps.listes.colonnes import lignes, preparer
from apps.listes.filtres import FiltreListeForm, membres_filtres, resume_filtres
from apps.listes.statistiques import _nettoyer, calculer_statistiques
from apps.membres.models import Membre

D = datetime.date
NATIONAL = Unite(Niveau.NATIONAL, None)


@pytest.fixture(autouse=True)
def date_fixe(monkeypatch):
    import apps.cotisations.services as s
    import apps.listes.filtres as f

    monkeypatch.setattr(s, "aujourdhui", lambda: D(2026, 3, 15))
    monkeypatch.setattr(f, "mois_des_cotisations", lambda j: D(2026, 3, 1))


@pytest.fixture
def situes(monde, depart):
    """m1 à jour ; m2 en retard d'un mois ; m3 en retard de 3 mois (Capitaine) ; autres : 3."""
    for k in ("m1", "m2", "m3", "m4", "sec_p1", "chef", "tresorier"):
        enregistre_le(monde[k], D(2025, 1, 1))
    for cle, montant in (("m1", 300), ("m2", 200)):
        v = saisir_versement(monde[cle], montant=montant, date_versement=D(2026, 3, 1), par=None)
        valider([v], par=None)
    Membre.objects.filter(pk=monde["m3"].pk).update(grade=5)
    return monde


def _noms(**data):
    form = FiltreListeForm(NATIONAL, QueryDict(urlencode(data | {"envoye": "1"}, doseq=True)))
    assert form.is_valid(), form.errors
    return sorted(m.nom for m in membres_filtres(NATIONAL, form.cleaned_data, D(2026, 3, 15)))


def test_filtre_a_jour_et_en_retard(situes):
    assert _noms(cotisation="a_jour") == ["Adjovi"]
    assert "Adjovi" not in _noms(cotisation="en_retard")
    assert len(_noms(cotisation="en_retard")) == 6
    assert "Bio" not in _noms(cotisation="en_retard", retard_min="2")


def test_filtre_combine_grade_et_retard(situes):
    assert _noms(grade=["5"], cotisation="en_retard", retard_min="2") == ["Chabi"]


def test_colonnes_cotisations(situes):
    qs = preparer(Membre.objects.filter(pk__in=[situes["m1"].pk, situes["m2"].pk]), D(2026, 3, 15))
    rangees = {
        r[0]: r[1:]
        for r in lignes(qs, ["nom", "mois_payes", "total_verse", "reste_du"], D(2026, 3, 15))
    }
    assert rangees["Adjovi"] == [3, 300, 0]
    assert rangees["Bio"] == [2, 200, 100]


def test_resume_filtres_cotisations(situes):
    form = FiltreListeForm(
        NATIONAL,
        QueryDict(urlencode({"envoye": "1", "cotisation": "en_retard", "retard_min": "2"})),
    )
    assert form.is_valid()
    assert "Cotisations : en retard d'au moins 2 mois" in resume_filtres(form)


def test_chaque_chiffre_cotisation_egal_sa_liste(situes):
    s = {x.titre: x for x in calculer_statistiques(NATIONAL, ["actif"], D(2026, 3, 15))}
    chiffres = {c.libelle: c.nombre for c in s["Cotisations"].cellules}
    assert chiffres == {"À jour": 1, "En retard": 6, "En retard de 3 mois et plus": 5}
    for c in s["Cotisations"].cellules:
        assert (
            c.nombre
            == membres_filtres(NATIONAL, _nettoyer(NATIONAL, c.filtres), D(2026, 3, 15)).count()
        )
