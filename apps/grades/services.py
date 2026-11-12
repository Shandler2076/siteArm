"""Seuls points d'entrée qui modifient le grade d'un membre (RI art. 76 à 84).

- Camarade → Soldat de 3ᵉ classe : première consécration, sans durée minimale.
- Grades 2 à 6 : par test, depuis le grade juste en dessous, après la durée minimale (art. 78) ;
  sinon seulement en promotion exceptionnelle (art. 84) avec un motif.
- Grades 7 à 12 : par nomination, depuis n'importe quel grade inférieur.
- Seul un membre Actif est promu ; une sanction ne change jamais le grade.
"""

import datetime

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from apps.grades.models import HistoriqueGrade, ModeGrade
from apps.membres.grades import DUREES_MINIMALES, PAR_NOMINATION, Grade
from apps.membres.models import Membre, Statut


class GradeRefuse(Exception):
    """Opération refusée ; le message s'affiche tel quel."""


def _il_y_a_ans(jour: datetime.date, ans: int) -> datetime.date:
    from apps.mouvements.statuts import ajouter_mois

    return ajouter_mois(jour, -12 * ans)


def eligible(membre: Membre, aujourdhui: datetime.date) -> bool:
    """Éligible au grade suivant : Camarade actif, ou durée minimale atteinte (grades 1 à 5)."""
    if membre.statut != Statut.ACTIF or membre.grade is None:
        return False
    if membre.grade == Grade.CAMARADE:
        return True
    duree = DUREES_MINIMALES.get(membre.grade)
    return bool(duree and membre.date_grade and membre.date_grade <= _il_y_a_ans(aujourdhui, duree))


def filtre_eligibles(aujourdhui: datetime.date) -> Q:
    """Même règle que `eligible`, en base."""
    q = Q(grade=Grade.CAMARADE)
    for grade, duree in DUREES_MINIMALES.items():
        q |= Q(grade=grade, date_grade__lte=_il_y_a_ans(aujourdhui, duree))
    return Q(statut=Statut.ACTIF) & q


def _enregistrer(membre, *, grade, date_effet, mode, par, reference="", motif=""):
    h = HistoriqueGrade.objects.create(
        membre=membre,
        grade=grade,
        date_effet=date_effet,
        mode=mode,
        reference=reference,
        motif=motif,
        enregistre_par=par,
    )
    membre.grade, membre.date_grade = grade, date_effet
    Membre.objects.filter(pk=membre.pk).update(grade=grade, date_grade=date_effet)
    if membre.compte_id:
        membre.compte.nom_affiche = membre.nom_complet
        membre.compte.save(update_fields=["nom_affiche"])
    return h


def erreurs_grade_initial(
    date_grade: datetime.date, annee_integration: int, date_naissance: datetime.date | None
) -> list[str]:
    """Contrôles de la date du grade donné à l'enregistrement (régularisation)."""
    erreurs = []
    if date_grade > timezone.localdate():
        erreurs.append("la date du grade ne peut pas être dans le futur.")
    if date_naissance and date_grade < date_naissance:
        erreurs.append("la date du grade précède la date de naissance.")
    if date_grade.year < annee_integration:
        erreurs.append("la date du grade précède l'année d'intégration.")
    return erreurs


def attribuer_grade_initial(
    membre: Membre, *, grade: int, date_effet: datetime.date, par, regularisation: bool
) -> HistoriqueGrade:
    """Grade à l'enregistrement (fait partie de l'enregistrement : ni journal ni notification)."""
    mode = ModeGrade.REGULARISATION if regularisation else ModeGrade.ENTREE
    return _enregistrer(membre, grade=grade, date_effet=date_effet, mode=mode, par=par)


def _obstacle(membre, grade, date_effet, aujourdhui, exceptionnelle, motif) -> tuple[str, str]:
    """(raison du refus ou "", mode retenu)."""
    if membre.statut != Statut.ACTIF:
        return f"statut {membre.get_statut_display()} : seul un membre actif est promu.", ""
    if membre.grade is None:
        return "grade non renseigné : utilisez la correction du grade.", ""
    if grade <= membre.grade:
        return "le nouveau grade doit être supérieur au grade actuel.", ""
    if date_effet > aujourdhui:
        return "la date d'effet ne peut pas être dans le futur.", ""
    if membre.date_grade and date_effet < membre.date_grade:
        return (
            f"la date d'effet précède celle du grade actuel ({membre.date_grade:%d/%m/%Y}).",
            "",
        )
    if grade >= PAR_NOMINATION:
        return "", ModeGrade.NOMINATION
    normal = grade == membre.grade + 1
    if normal and membre.grade == Grade.CAMARADE:
        return "", ModeGrade.PREMIERE_CONSECRATION
    duree = DUREES_MINIMALES.get(membre.grade)
    if normal and membre.date_grade and membre.date_grade <= _il_y_a_ans(date_effet, duree):
        return "", ModeGrade.TEST
    if exceptionnelle:
        if not (motif or "").strip():
            return "le motif est obligatoire pour une promotion exceptionnelle.", ""
        return "", ModeGrade.EXCEPTIONNELLE
    if not normal:
        return "on ne passe qu'au grade suivant, sauf promotion exceptionnelle (art. 84).", ""
    return (
        f"il faut {duree} ans dans le grade actuel (art. 78), sauf promotion exceptionnelle.",
        "",
    )


def _notifier(membre, h):
    from apps.bureaux.perimetre import Unite
    from apps.notifications.services import notifier, notifier_unite

    libelle = h.get_grade_display()
    ref = f" (décision {h.reference})" if h.reference else ""
    notifier([membre.compte], f"Votre grade : {libelle} à compter du {h.date_effet:%d/%m/%Y}{ref}.")
    a = membre.affectation_actuelle
    if a:
        notifier_unite(
            Unite("paroisse", a.paroisse), f"{membre.nom_complet} : nouveau grade {libelle}."
        )


def _promouvoir(membre, grade, date_effet, reference, par, exceptionnelle, motif, aujourdhui):
    from apps.journal.models import GRADE_PROMOTION
    from apps.journal.services import journaliser

    raison, mode = _obstacle(membre, grade, date_effet, aujourdhui, exceptionnelle, motif)
    if raison:
        raise GradeRefuse(raison)
    h = _enregistrer(
        membre,
        grade=grade,
        date_effet=date_effet,
        mode=mode,
        par=par,
        reference=reference,
        motif=(motif or "").strip() if mode == ModeGrade.EXCEPTIONNELLE else "",
    )
    journaliser(
        par, GRADE_PROMOTION, membre=membre.matricule, grade=h.get_grade_display(), mode=mode
    )
    transaction.on_commit(lambda: _notifier(membre, h))
    return h


def _reference(reference: str) -> str:
    reference = (reference or "").strip()
    if not reference:
        raise GradeRefuse("La référence de la décision du BNC est obligatoire.")
    return reference


def promouvoir(
    membre: Membre,
    *,
    grade: int,
    date_effet: datetime.date,
    reference: str,
    par,
    exceptionnelle: bool = False,
    motif: str = "",
) -> HistoriqueGrade:
    reference = _reference(reference)
    with transaction.atomic():
        m = (
            Membre.objects.select_for_update(of=("self",))
            .select_related("compte")
            .get(pk=membre.pk)
        )
        return _promouvoir(
            m, grade, date_effet, reference, par, exceptionnelle, motif, timezone.localdate()
        )


def promouvoir_en_serie(
    membres: list, *, grade: int, date_effet: datetime.date, reference: str, par
) -> list[HistoriqueGrade]:
    """Tout ou rien : si un membre ne remplit pas les conditions, personne n'est promu."""
    reference = _reference(reference)
    aujourdhui = timezone.localdate()
    with transaction.atomic():
        verrouilles = list(
            Membre.objects.select_for_update(of=("self",))
            .select_related("compte")
            .filter(pk__in=[m.pk for m in membres])
            .order_by("pk")
        )
        refus = []
        for m in verrouilles:
            raison, _ = _obstacle(m, grade, date_effet, aujourdhui, False, "")
            if raison:
                refus.append(f"{m.nom_complet} : {raison}")
        if refus:
            raise GradeRefuse("Aucune promotion enregistrée. " + " ; ".join(refus))
        return [
            _promouvoir(m, grade, date_effet, reference, par, False, "", aujourdhui)
            for m in verrouilles
        ]


def corriger_grade(
    membre: Membre, *, grade: int, date_effet: datetime.date, motif: str, par
) -> HistoriqueGrade:
    """Correction par le BNC (erreur de saisie) : n'importe quel grade, motif obligatoire."""
    from apps.journal.models import GRADE_CORRECTION
    from apps.journal.services import journaliser

    motif = (motif or "").strip()
    if not motif:
        raise GradeRefuse("Le motif de la correction est obligatoire.")
    if date_effet > timezone.localdate():
        raise GradeRefuse("La date d'effet ne peut pas être dans le futur.")
    with transaction.atomic():
        m = (
            Membre.objects.select_for_update(of=("self",))
            .select_related("compte")
            .get(pk=membre.pk)
        )
        h = _enregistrer(
            m, grade=grade, date_effet=date_effet, mode=ModeGrade.CORRECTION, par=par, motif=motif
        )
        journaliser(par, GRADE_CORRECTION, membre=m.matricule, grade=h.get_grade_display())
        transaction.on_commit(lambda: _notifier(m, h))
    return h
