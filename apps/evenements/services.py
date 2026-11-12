"""Seuls points d'écriture des événements (Bureau national ; cahier des charges § 17).

Les invitations partent directement du Bureau national vers la personne convoquée.
"""

import datetime

from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.evenements.models import (
    Convocation,
    EtatEvenement,
    Evenement,
    Presence,
    Session,
)

ACTIONS = {
    "creation": "evenement_cree",
    "modification": "evenement_modifie",
    "annulation": "evenement_annule",
    "convocation": "convocation",
    "retrait": "convocation_retiree",
    "presence": "presence",
}


class EvenementRefuse(Exception):
    """Opération refusée ; le message s'affiche tel quel."""


def _journal(par, action, **details):
    from apps.journal.services import journaliser

    journaliser(par, ACTIONS[action], unite="national", **details)


def _notifier(convocations, texte_pour):
    from apps.notifications.services import notifier

    paires = [(c.membre.compte, texte_pour(c)) for c in convocations]
    transaction.on_commit(lambda: [notifier([compte], t) for compte, t in paires])


def quand(ev: Evenement) -> str:
    debut = timezone.localtime(ev.debut)
    return f"le {debut:%d/%m/%Y} à {debut:%H:%M}"


def creer_evenement(
    *,
    nom: str,
    debut: datetime.datetime,
    par,
    fin: datetime.datetime | None = None,
    lieu: str = "",
    description: str = "",
    avec_autorisation: bool = False,
    sessions: list[str] | None = None,
) -> Evenement:
    nom = (nom or "").strip()
    if not nom:
        raise EvenementRefuse("La dénomination de l'événement est obligatoire.")
    if fin and fin < debut:
        raise EvenementRefuse("La fin ne peut pas précéder le début.")
    with transaction.atomic():
        ev = Evenement.objects.create(
            nom=nom,
            debut=debut,
            fin=fin,
            lieu=lieu.strip(),
            description=description.strip(),
            avec_autorisation=avec_autorisation,
            cree_par=par,
        )
        ajouter_sessions(ev, sessions or [])
        _journal(par, "creation", evenement=ev.pk, nom=ev.nom)
    return ev


def ajouter_sessions(ev: Evenement, noms: list[str]) -> None:
    existantes = set(ev.sessions.values_list("nom", flat=True))
    ordre = ev.sessions.count()
    for nom in noms:
        nom = (nom or "").strip()
        if nom and nom not in existantes:
            ordre += 1
            Session.objects.create(evenement=ev, nom=nom, ordre=ordre)
            existantes.add(nom)


def _actives(ev):
    return ev.convocations.filter(active=True).select_related("membre__compte", "session")


def modifier_evenement(ev: Evenement, *, par, sessions: list[str] | None = None, **champs):
    """Modifie l'événement ; un changement de date ou de lieu est notifié aux convoqués."""
    if ev.annule:
        raise EvenementRefuse("Cet événement est annulé.")
    avant = (ev.debut, ev.lieu)
    for cle, valeur in champs.items():
        if cle not in {"nom", "debut", "fin", "lieu", "description", "avec_autorisation"}:
            raise EvenementRefuse(f"Champ inconnu : {cle}.")
        setattr(ev, cle, valeur.strip() if isinstance(valeur, str) else valeur)
    if not ev.nom:
        raise EvenementRefuse("La dénomination de l'événement est obligatoire.")
    if ev.fin and ev.fin < ev.debut:
        raise EvenementRefuse("La fin ne peut pas précéder le début.")
    with transaction.atomic():
        ev.save()
        if sessions is not None:
            ajouter_sessions(ev, sessions)
        _journal(par, "modification", evenement=ev.pk, nom=ev.nom)
        if (ev.debut, ev.lieu) != avant:
            lieu = f", {ev.lieu}" if ev.lieu else ""
            _notifier(
                list(_actives(ev)),
                lambda c: f"Bureau national — « {ev.nom} » : nouvelle date {quand(ev)}{lieu}.",
            )
    return ev


def annuler_evenement(ev: Evenement, *, motif: str, par) -> Evenement:
    motif = (motif or "").strip()
    if not motif:
        raise EvenementRefuse("Le motif de l'annulation est obligatoire.")
    with transaction.atomic():
        ev = Evenement.objects.select_for_update().get(pk=ev.pk)
        if ev.annule:
            raise EvenementRefuse("Cet événement est déjà annulé.")
        ev.etat, ev.motif_annulation = EtatEvenement.ANNULE, motif
        ev.save()
        _journal(par, "annulation", evenement=ev.pk, nom=ev.nom, motif=motif)
        _notifier(
            list(_actives(ev)),
            lambda c: f"Bureau national — « {ev.nom} » ({quand(ev)}) est annulé : {motif}.",
        )
    return ev


def _texte_convocation(ev, c) -> str:
    session = f", {c.session.nom}" if c.session else ""
    lieu = f", {ev.lieu}" if ev.lieu else ""
    suite = (
        " Votre autorisation est disponible dans « Mes événements »."
        if ev.avec_autorisation
        else ""
    )
    return (
        f"Bureau national — vous êtes convoqué(e) : « {ev.nom} » {quand(ev)}{lieu}{session}.{suite}"
    )


def convoquer(ev: Evenement, membres, *, par, session: Session | None = None) -> list[Convocation]:
    """Convoque (ou change de session) ; un membre déjà convoqué n'est pas convoqué deux fois."""
    if ev.annule:
        raise EvenementRefuse("Cet événement est annulé.")
    if session is not None and session.evenement_id != ev.pk:
        raise EvenementRefuse("Cette session n'appartient pas à l'événement.")
    resultat, a_notifier = [], []
    with transaction.atomic():
        for membre in membres:
            existante = ev.convocations.filter(membre=membre, active=True).first()
            if existante:
                if session is not None and existante.session_id != session.pk:
                    existante.session = session
                    existante.save(update_fields=["session"])
                    a_notifier.append(existante)
                resultat.append(existante)
                continue
            try:
                with transaction.atomic():
                    c = Convocation.objects.create(
                        evenement=ev, membre=membre, session=session, convoque_par=par
                    )
            except IntegrityError:
                c = ev.convocations.get(membre=membre, active=True)
            resultat.append(c)
            a_notifier.append(c)
            _journal(
                par,
                "convocation",
                evenement=ev.pk,
                nom=ev.nom,
                membre=membre.matricule,
                session=session.nom if session else "",
            )
        _notifier(a_notifier, lambda c: _texte_convocation(ev, c))
    return resultat


def retirer(convocation: Convocation, *, motif: str, par) -> Convocation:
    motif = (motif or "").strip()
    if not motif:
        raise EvenementRefuse("Le motif du retrait est obligatoire.")
    with transaction.atomic():
        c = (
            Convocation.objects.select_for_update(of=("self",))
            .select_related("evenement", "membre__compte")
            .get(pk=convocation.pk)
        )
        if not c.active:
            raise EvenementRefuse("Cette convocation est déjà retirée.")
        c.active, c.motif_retrait = False, motif
        c.save(update_fields=["active", "motif_retrait"])
        ev = c.evenement
        _journal(
            par, "retrait", evenement=ev.pk, nom=ev.nom, membre=c.membre.matricule, motif=motif
        )
        _notifier([c], lambda c: f"Bureau national — votre convocation à « {ev.nom} » est retirée.")
    return c


def pointer(convocation: Convocation, presence: str, *, par) -> Convocation:
    if presence not in (Presence.PRESENT, Presence.ABSENT, Presence.EXCUSE):
        raise EvenementRefuse("Présence inconnue.")
    with transaction.atomic():
        c = (
            Convocation.objects.select_for_update(of=("self",))
            .select_related("evenement", "membre")
            .get(pk=convocation.pk)
        )
        if not c.active:
            raise EvenementRefuse("Ce membre n'est plus convoqué : sa présence ne compte pas.")
        if c.evenement.annule:
            raise EvenementRefuse("Cet événement est annulé.")
        c.presence, c.pointe_par, c.date_pointage = presence, par, timezone.now()
        c.save(update_fields=["presence", "pointe_par", "date_pointage"])
        _journal(
            par,
            "presence",
            evenement=c.evenement_id,
            nom=c.evenement.nom,
            membre=c.membre.matricule,
            presence=presence,
        )
    return c


def convocation_par_jeton(jeton: str) -> Convocation | None:
    if not jeton or len(jeton) > 64:
        return None
    return (
        Convocation.objects.select_related("evenement", "membre", "session")
        .filter(jeton=jeton)
        .first()
    )


def autorisation_valable(c: Convocation) -> bool:
    return bool(c.active and not c.evenement.annule and c.evenement.avec_autorisation)
