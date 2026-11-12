import datetime

import pytest

from apps.grades.models import HistoriqueGrade, ModeGrade
from apps.grades.services import (
    GradeRefuse,
    corriger_grade,
    eligible,
    filtre_eligibles,
    promouvoir,
    promouvoir_en_serie,
)
from apps.journal.models import GRADE_CORRECTION, GRADE_PROMOTION, EntreeJournal
from apps.membres.models import Membre
from apps.notifications.models import Notification

D = datetime.date


def _poser(membre, grade, depuis):
    """Situation de départ (hors services, pour les tests)."""
    Membre.objects.filter(pk=membre.pk).update(grade=grade, date_grade=depuis)
    HistoriqueGrade.objects.create(
        membre=membre, grade=grade, date_effet=depuis, mode=ModeGrade.REGULARISATION
    )
    membre.refresh_from_db()
    return membre


@pytest.fixture
def soldat(monde):
    return _poser(monde["m1"], 1, D(2020, 1, 1))


def test_promotion_apres_duree(soldat, monde, compte_technique, django_capture_on_commit_callbacks):
    with django_capture_on_commit_callbacks(execute=True):
        h = promouvoir(
            soldat, grade=2, date_effet=D(2023, 1, 1), reference="Décision 12", par=compte_technique
        )
    soldat.refresh_from_db()
    assert (soldat.grade, soldat.date_grade) == (2, D(2023, 1, 1))
    assert h.mode == ModeGrade.TEST and h.reference == "Décision 12"
    assert EntreeJournal.objects.filter(action=GRADE_PROMOTION).count() == 1
    assert Notification.objects.filter(destinataire=soldat.compte).count() == 1
    assert Notification.objects.filter(destinataire=monde["sec_p1"].compte).exists()
    soldat.compte.refresh_from_db()
    assert soldat.compte.nom_affiche == "Soldat de 2ᵉ classe Test ADJOVI"


def test_promotion_trop_tot_refusee(soldat, compte_technique):
    avant = soldat.grades.count()
    with pytest.raises(GradeRefuse, match="3 ans"):
        promouvoir(soldat, grade=2, date_effet=D(2022, 12, 31), reference="D", par=compte_technique)
    soldat.refresh_from_db()
    assert soldat.grade == 1 and soldat.grades.count() == avant


def test_saut_de_grade_refuse_sauf_exceptionnelle(soldat, compte_technique):
    kw = dict(grade=3, date_effet=D(2021, 1, 1), reference="D", par=compte_technique)
    with pytest.raises(GradeRefuse):
        promouvoir(soldat, **kw)
    with pytest.raises(GradeRefuse, match="motif"):
        promouvoir(soldat, exceptionnelle=True, motif=" ", **kw)
    h = promouvoir(soldat, exceptionnelle=True, motif="Mérites particuliers", **kw)
    assert h.mode == ModeGrade.EXCEPTIONNELLE and h.motif == "Mérites particuliers"


def test_nomination_sans_duree(soldat, compte_technique):
    h = promouvoir(soldat, grade=7, date_effet=D(2020, 1, 2), reference="D", par=compte_technique)
    assert h.mode == ModeGrade.NOMINATION


def test_premiere_consecration(monde, compte_technique):
    camarade = _poser(monde["m2"], 0, D(2026, 3, 10))
    with pytest.raises(GradeRefuse):
        promouvoir(
            camarade, grade=2, date_effet=D(2026, 3, 11), reference="D", par=compte_technique
        )
    h = promouvoir(
        camarade, grade=1, date_effet=D(2026, 3, 11), reference="D", par=compte_technique
    )
    assert h.mode == ModeGrade.PREMIERE_CONSECRATION


@pytest.mark.parametrize("grade", [1, 0])
def test_grade_inferieur_ou_egal_refuse(soldat, compte_technique, grade):
    with pytest.raises(GradeRefuse):
        promouvoir(
            soldat, grade=grade, date_effet=D(2024, 1, 1), reference="D", par=compte_technique
        )


def test_date_avant_grade_actuel_refusee(soldat, compte_technique):
    with pytest.raises(GradeRefuse):
        promouvoir(soldat, grade=7, date_effet=D(2019, 12, 31), reference="D", par=compte_technique)


def test_date_future_refusee(soldat, compte_technique):
    demain = datetime.date.today() + datetime.timedelta(days=1)
    with pytest.raises(GradeRefuse, match="futur"):
        promouvoir(soldat, grade=2, date_effet=demain, reference="D", par=compte_technique)


def test_reference_obligatoire(soldat, compte_technique):
    with pytest.raises(GradeRefuse, match="référence"):
        promouvoir(soldat, grade=2, date_effet=D(2024, 1, 1), reference="  ", par=compte_technique)


@pytest.mark.parametrize("statut", ["sanctionne", "exclu", "decede"])
def test_membre_non_actif_refuse(soldat, compte_technique, statut):
    Membre.objects.filter(pk=soldat.pk).update(statut=statut)
    soldat.refresh_from_db()
    with pytest.raises(GradeRefuse):
        promouvoir(soldat, grade=2, date_effet=D(2024, 1, 1), reference="D", par=compte_technique)


def test_sans_grade_refuse_vers_correction(monde, compte_technique):
    m = monde["m3"]
    Membre.objects.filter(pk=m.pk).update(grade=None, date_grade=None)
    m.refresh_from_db()
    with pytest.raises(GradeRefuse, match="correction"):
        promouvoir(m, grade=2, date_effet=D(2024, 1, 1), reference="D", par=compte_technique)


def test_serie_tout_ou_rien(monde, compte_technique):
    a = _poser(monde["m1"], 1, D(2019, 1, 1))
    b = _poser(monde["m2"], 1, D(2019, 6, 1))
    c = _poser(monde["m3"], 1, D(2023, 1, 1))  # trop récent
    with pytest.raises(GradeRefuse) as e:
        promouvoir_en_serie(
            [a, b, c], grade=2, date_effet=D(2024, 1, 1), reference="D", par=compte_technique
        )
    assert c.nom_complet in str(e.value)
    assert a.nom_complet not in str(e.value)
    assert set(
        Membre.objects.filter(pk__in=[a.pk, b.pk, c.pk]).values_list("grade", flat=True)
    ) == {1}
    faits = promouvoir_en_serie(
        [a, b], grade=2, date_effet=D(2024, 1, 1), reference="D", par=compte_technique
    )
    assert len(faits) == 2


def test_correction(soldat, compte_technique):
    with pytest.raises(GradeRefuse, match="motif"):
        corriger_grade(soldat, grade=0, date_effet=D(2020, 1, 1), motif="", par=compte_technique)
    h = corriger_grade(
        soldat, grade=0, date_effet=D(2020, 1, 1), motif="Erreur de saisie", par=compte_technique
    )
    soldat.refresh_from_db()
    assert soldat.grade == 0 and h.mode == ModeGrade.CORRECTION
    assert EntreeJournal.objects.filter(action=GRADE_CORRECTION).count() == 1


def test_eligible_camarade(monde):
    camarade = _poser(monde["m2"], 0, datetime.date.today())
    assert eligible(camarade, datetime.date.today())


def test_eligibles_en_base_egal_python(monde):
    j = D(2026, 11, 12)
    situations = [
        (monde["m1"], 1, D(2023, 11, 12), "actif"),  # pile 3 ans
        (monde["m2"], 1, D(2023, 11, 13), "actif"),  # un jour de trop peu
        (monde["m3"], 5, D(2020, 1, 1), "actif"),
        (monde["m4"], 6, D(2000, 1, 1), "actif"),  # Senior Capitaine : nomination ensuite
        (monde["sec_p1"], 0, D(2026, 11, 1), "actif"),
        (monde["chef"], 2, D(2010, 1, 1), "sanctionne"),
    ]
    tous = []
    for m, g, d, s in situations:
        Membre.objects.filter(pk=m.pk).update(grade=g, date_grade=d, statut=s)
        m.refresh_from_db()
        tous.append(m)
    attendus = {m.pk for m in tous if eligible(m, j)}
    assert attendus == {monde["m1"].pk, monde["m3"].pk, monde["sec_p1"].pk}
    en_base = set(
        Membre.objects.filter(pk__in=[m.pk for m in tous])
        .filter(filtre_eligibles(j))
        .values_list("pk", flat=True)
    )
    assert en_base == attendus
