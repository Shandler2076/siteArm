"""Site d'essai : membres fictifs avec des grades variés ; recréation des données fictives."""

import io

import pytest
from django.core.management import CommandError, call_command
from django.db import connection

from apps.grades.models import HistoriqueGrade, ModeGrade
from apps.membres.grades import DUREES_MINIMALES, PAR_NOMINATION
from apps.membres.models import Membre
from apps.mouvements.statuts import ajouter_mois


def test_demo_grades_varies(territoire, settings):
    settings.SITE_DEMO = True
    call_command("peupler_demo", membres=300, stdout=io.StringIO())
    grades = set(Membre.objects.values_list("grade", flat=True))
    assert len(grades) >= 8 and {0, 5, 6} <= grades and None not in grades
    for m in Membre.objects.prefetch_related("grades", "affectations"):
        historique = list(m.grades.all())
        assert historique and historique[-1].grade == m.grade
        assert historique[-1].date_effet == m.date_grade
        debut = min(a.date_debut for a in m.affectations.all())
        for avant, apres in zip(historique, historique[1:], strict=False):
            assert apres.date_effet >= avant.date_effet
            if apres.mode == ModeGrade.TEST:
                duree = DUREES_MINIMALES[avant.grade]
                assert avant.date_effet <= ajouter_mois(apres.date_effet, -12 * duree)
            if apres.grade >= PAR_NOMINATION:
                assert apres.mode in (ModeGrade.NOMINATION, ModeGrade.REGULARISATION)
        assert historique[0].date_effet >= debut
    assert HistoriqueGrade.objects.filter(mode=ModeGrade.TEST).exists()


def test_reinitialiser_demo_refuse_hors_demo(territoire, settings):
    settings.SITE_DEMO = False
    with pytest.raises(CommandError, match="site d'essai"):
        call_command("reinitialiser_demo", oui=True, stdout=io.StringIO())


def test_reinitialiser_demo_refuse_sans_confirmation(territoire, settings):
    settings.SITE_DEMO = True
    with pytest.raises(CommandError, match="--oui"):
        call_command("reinitialiser_demo", stdout=io.StringIO())


@pytest.mark.skipif(connection.vendor != "postgresql", reason="TRUNCATE : PostgreSQL seulement")
@pytest.mark.django_db(transaction=True, serialized_rollback=True)
def test_reinitialiser_demo_postgresql(settings):
    from apps.bureaux.models import Fonction
    from apps.organisation.models import Region

    settings.SITE_DEMO = True
    fonctions = Fonction.objects.count()
    call_command("charger_territoire", stdout=io.StringIO())
    call_command("peupler_demo", membres=10, stdout=io.StringIO())
    Membre.objects.filter(pk=Membre.objects.first().pk).update(nom="ZZAVANT")
    base = connection.settings_dict["NAME"]
    call_command("reinitialiser_demo", oui=True, base=base, membres=10, stdout=io.StringIO())
    assert Region.objects.exists() and Membre.objects.exists()
    assert not Membre.objects.filter(nom="ZZAVANT").exists()
    assert Fonction.objects.count() == fonctions > 0


def test_reinitialiser_demo_exige_le_nom_de_la_base(territoire, settings):
    """Revue finale M-11 : une seconde sécurité, le nom exact de la base."""
    settings.SITE_DEMO = True
    with pytest.raises(CommandError, match="--base"):
        call_command("reinitialiser_demo", oui=True, stdout=io.StringIO())
    with pytest.raises(CommandError, match="--base"):
        call_command("reinitialiser_demo", oui=True, base="autre", stdout=io.StringIO())
