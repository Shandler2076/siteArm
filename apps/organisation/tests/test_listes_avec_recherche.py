"""Listes longues avec une recherche (demande du 20/11/2026) : on ne fouille jamais toute la
liste des paroisses ; on tape quelques lettres."""

from pathlib import Path

import pytest
from django.conf import settings

from apps.organisation.widgets import ListeAvecRecherche


def _avec_recherche(champ):
    assert isinstance(champ.widget, ListeAvecRecherche)
    assert "data-recherche" in champ.widget.render("x", None)


@pytest.mark.django_db
def test_enregistrement_paroisses_avec_recherche():
    from apps.membres.forms import FormulaireEnregistrement

    f = FormulaireEnregistrement()
    _avec_recherche(f.fields["paroisse_integration"])
    _avec_recherche(f.fields["paroisse_actuelle"])


@pytest.mark.django_db
def test_correction_mutation_lots_versement_avec_recherche():
    from apps.cotisations.forms import VersementForm
    from apps.lots.forms import FormulaireDepot
    from apps.membres.models import Membre
    from apps.membres.views_bn import FormulaireCorrection
    from apps.mouvements.forms import NouvelleMutationForm

    _avec_recherche(FormulaireCorrection().fields["paroisse"])
    _avec_recherche(NouvelleMutationForm(national=True).fields["paroisse_arrivee"])
    _avec_recherche(FormulaireDepot().fields["region"])
    _avec_recherche(VersementForm(membres=Membre.objects.none()).fields["membre"])


def test_listes_unites_avec_recherche():
    from apps.listes.filtres import _SelectRattache

    assert issubclass(_SelectRattache, ListeAvecRecherche)


def test_le_script_ajoute_la_recherche_partout():
    """Filet de sécurité : toute liste déroulante longue reçoit aussi la recherche."""
    js = (Path(settings.BASE_DIR) / "static/js/site.js").read_text(encoding="utf-8")
    assert "function listeAvecRecherche(" in js
    assert "select[data-recherche]" in js
    assert "SEUIL_RECHERCHE" in js
