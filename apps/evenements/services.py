"""Seuls points d'écriture des événements (Bureau national ; cahier des charges § 17).

Les invitations partent directement du Bureau national vers la personne convoquée.
"""

import datetime
import re

from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.evenements.models import (
    Convocation,
    EtatEvenement,
    Evenement,
    Formule,
    Presence,
    Role,
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


JETON = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
SORTIS = {"exclu", "demissionnaire", "decede"}  # plus membres : ni convocation ni carte valable


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
    avec_sections: bool | None = None,
    validite_debut: datetime.datetime | None = None,
    validite_heures: int = 24,
) -> Evenement:
    """Crée l'événement. Les sections ne sont créées que si l'option « sections » est choisie
    (par défaut : dès qu'une section est donnée)."""
    nom = (nom or "").strip()
    if not nom:
        raise EvenementRefuse("La dénomination de l'événement est obligatoire.")
    if fin and fin < debut:
        raise EvenementRefuse("La fin ne peut pas précéder le début.")
    sessions = [n for n in (sessions or []) if (n or "").strip()]
    if avec_sections is None:
        avec_sections = bool(sessions)
    with transaction.atomic():
        ev = Evenement.objects.create(
            nom=nom,
            debut=debut,
            fin=fin,
            lieu=lieu.strip(),
            description=description.strip(),
            avec_autorisation=avec_autorisation,
            avec_sections=avec_sections,
            validite_debut=validite_debut,
            validite_heures=validite_heures,
            cree_par=par,
        )
        if avec_sections:
            ajouter_sessions(ev, sessions)
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
        if cle not in {
            "nom",
            "debut",
            "fin",
            "lieu",
            "description",
            "avec_autorisation",
            "avec_sections",
            "validite_debut",
            "validite_heures",
        }:
            raise EvenementRefuse(f"Champ inconnu : {cle}.")
        setattr(ev, cle, valeur.strip() if isinstance(valeur, str) else valeur)
    if not ev.nom:
        raise EvenementRefuse("La dénomination de l'événement est obligatoire.")
    if ev.fin and ev.fin < ev.debut:
        raise EvenementRefuse("La fin ne peut pas précéder le début.")
    with transaction.atomic():
        ev.save()
        if sessions is not None and ev.avec_sections:
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
    role = f" — {c.texte_role}" if c.role != Role.TRAVAILLEUR or c.session_id else ""
    lieu = f", {ev.lieu}" if ev.lieu else ""
    suite = (
        " Votre autorisation est disponible dans « Mes événements »."
        if ev.avec_autorisation
        else ""
    )
    return f"Bureau national — vous êtes convoqué(e) : « {ev.nom} » {quand(ev)}{lieu}{role}.{suite}"


def bureau_du_membre(membre) -> str:
    """Bureau représenté par un convoqué « en tant que bureau » : ses mandats en cours."""
    from apps.bureaux.models import Mandat
    from apps.bureaux.perimetre import Unite

    libelles = []
    for m in (
        Mandat.objects.en_cours()
        .filter(membre=membre)
        .select_related("fonction", "paroisse", "circuit", "region")
        .order_by("fonction__niveau")
    ):
        libelle = Unite(m.fonction.niveau, m.unite).libelle
        if libelle not in libelles:
            libelles.append(libelle)
    return ", ".join(libelles)[:200]


def convoquer(
    ev: Evenement,
    membres,
    *,
    par,
    session: Session | None = None,
    sans_session: bool = False,
    role: str = Role.TRAVAILLEUR,
    formule: str = "",
) -> list[Convocation]:
    """Convoque (ou change de section, de rôle, de formule) ; jamais deux fois le même membre.

    Tout ou rien : un membre qui n'est plus dans le mouvement fait refuser l'ensemble.
    `sans_session=True` remet « sans section » les membres déjà convoqués.
    Rôle « bureau » : jamais de section ; le bureau représenté est déduit de ses mandats.
    """
    if ev.annule:
        raise EvenementRefuse("Cet événement est annulé.")
    if role not in Role.values:
        raise EvenementRefuse("Rôle inconnu.")
    if formule and formule not in Formule.values:
        raise EvenementRefuse("Formule inconnue.")
    if session is not None and session.evenement_id != ev.pk:
        raise EvenementRefuse("Cette section n'appartient pas à l'événement.")
    if role == Role.BUREAU:
        session, sans_session = None, True
    membres = list(membres)
    sortis = [m.nom_complet for m in membres if m.statut in SORTIS]
    if sortis:
        raise EvenementRefuse(
            "Aucune convocation enregistrée : ne sont plus membres du mouvement — "
            + ", ".join(sortis)
            + "."
        )
    resultat, a_notifier = [], []
    with transaction.atomic():
        for membre in membres:
            bureau = bureau_du_membre(membre) if role == Role.BUREAU else ""
            existante = ev.convocations.filter(membre=membre, active=True).first()
            if existante:
                nouvelle = session.pk if session is not None else None
                change_section = (
                    session is not None or sans_session
                ) and existante.session_id != nouvelle
                if change_section or (existante.role, existante.formule) != (role, formule):
                    ancienne = existante.session.nom if existante.session else ""
                    if session is not None or sans_session:
                        existante.session = session
                    existante.role, existante.formule = role, formule
                    existante.bureau_libelle = bureau
                    existante.save(update_fields=["session", "role", "formule", "bureau_libelle"])
                    a_notifier.append(existante)
                    _journal(
                        par,
                        "convocation",
                        evenement=ev.pk,
                        nom=ev.nom,
                        membre=membre.matricule,
                        session=existante.session.nom if existante.session else "",
                        ancienne_session=ancienne,
                        role=role,
                    )
                resultat.append(existante)
                continue
            try:
                with transaction.atomic():
                    c = Convocation.objects.create(
                        evenement=ev,
                        membre=membre,
                        session=session,
                        role=role,
                        formule=formule,
                        bureau_libelle=bureau,
                        convoque_par=par,
                    )
            except IntegrityError:
                # Convoqué au même instant par une autre requête : déjà notifié et journalisé.
                resultat.append(ev.convocations.get(membre=membre, active=True))
                continue
            resultat.append(c)
            a_notifier.append(c)
            _journal(
                par,
                "convocation",
                evenement=ev.pk,
                nom=ev.nom,
                membre=membre.matricule,
                session=session.nom if session else "",
                role=role,
            )
        _notifier(a_notifier, lambda c: _texte_convocation(ev, c))
    return resultat


def rechercher_membres(texte: str, limite: int = 20):
    """Recherche d'un membre à convoquer (BN seulement) : matricule ou nom / prénoms."""
    from django.db.models import Q

    from apps.membres.models import Membre

    texte = (texte or "").strip()
    if len(texte) < 2:
        return Membre.objects.none()
    par_nom = Q()
    for mot in texte.split():  # chaque mot doit se trouver dans le nom ou les prénoms
        par_nom &= Q(nom__icontains=mot) | Q(prenoms__icontains=mot)
    filtre = Q(matricule__icontains=texte) | par_nom
    return (
        Membre.objects.filter(filtre).exclude(statut__in=SORTIS).order_by("nom", "prenoms")[:limite]
    )


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
    if not jeton or not JETON.match(jeton):
        return None
    return (
        Convocation.objects.select_related("evenement", "membre", "session")
        .filter(jeton=jeton)
        .first()
    )


def autorisation_valable(c: Convocation, maintenant: datetime.datetime | None = None) -> bool:
    """Carte téléchargeable et valable (ou bientôt valable) : jusqu'à la fin de sa validité."""
    maintenant = maintenant or timezone.now()
    return bool(
        c.active
        and not c.evenement.annule
        and c.evenement.avec_autorisation
        and c.membre.statut not in SORTIS
        and maintenant < c.evenement.fin_validite
    )


def _date(d: datetime.datetime) -> str:
    return f"{timezone.localtime(d):%d/%m/%Y à %H:%M}"


def etat_scan(c: Convocation | None, maintenant: datetime.datetime) -> tuple[str, str]:
    """(état, explication) lus par le contrôleur : valable, pas_encore, expiree, non_valable."""
    if c is None:
        return "non_valable", "Code inconnu."
    ev = c.evenement
    if not c.active:
        return "non_valable", "Cette convocation a été retirée."
    if ev.annule:
        return "non_valable", "Cet événement est annulé."
    if not ev.avec_autorisation:
        return "non_valable", "Cet événement ne donne pas lieu à une autorisation."
    if c.membre.statut in SORTIS:
        return "non_valable", "Cette personne n'est plus membre du mouvement."
    if maintenant >= ev.fin_validite:
        return "expiree", f"Autorisation expirée depuis le {_date(ev.fin_validite)}."
    if maintenant < ev.debut_validite:
        return "pas_encore", f"Valable à partir du {_date(ev.debut_validite)}."
    return "valable", f"Valable jusqu'au {_date(ev.fin_validite)}."
