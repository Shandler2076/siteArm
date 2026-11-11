"""Circuits de validation : mutations (Tâche 2) et signalements (Tâche 3).

Toutes les décisions sont atomiques, verrouillent la demande et revérifient la situation.
"""

import datetime
from collections.abc import Iterable

from django.db import IntegrityError, transaction
from django.db.models import Q, QuerySet
from django.utils import timezone

from apps.bureaux.models import Niveau
from apps.bureaux.perimetre import Unite, titulaires_gestion
from apps.journal import models as journal
from apps.journal.services import journaliser
from apps.membres.models import Affectation
from apps.mouvements.models import EN_COURS, AvisMutation, EtatDemande, Mutation
from apps.mouvements.statuts import STATUTS_AVEC_ACCES, clore_mandats
from apps.notifications.services import notifier

NATIONAL = Unite(Niveau.NATIONAL, None)


class MouvementRefuse(Exception):
    """Demande ou décision impossible ; le message s'affiche tel quel."""


def lien_mutation(mutation: Mutation) -> str:
    return f"/bureau/mutations/{mutation.pk}/"


def unites_de_paroisse(paroisse) -> list[Unite]:
    return [
        Unite(Niveau.PAROISSE, paroisse),
        Unite(Niveau.CIRCUIT, paroisse.circuit),
        Unite(Niveau.REGION, paroisse.circuit.region),
    ]


def notifier_unites(unites: Iterable[Unite], message: str, lien: str = "", comptes=()) -> int:
    """Une seule notification par compte, même s'il siège dans plusieurs unités."""
    destinataires = list(comptes)
    for unite in unites:
        destinataires.extend(titulaires_gestion(unite))
    return notifier(destinataires, message, lien)


def _decrire(mutation: Mutation) -> str:
    m, depart, arrivee = mutation.membre, mutation.paroisse_depart, mutation.paroisse_arrivee
    return f"{m.matricule} — {m.nom_complet} ({depart.nom} → {arrivee.nom})"


# --- Mutations ---------------------------------------------------------------------------


def _obstacle_mutation(membre, paroisse_arrivee, paroisse_depart_attendue=None) -> str | None:
    if membre.statut not in STATUTS_AVEC_ACCES:
        return "Seul un membre actif ou sanctionné peut être muté."
    if not paroisse_arrivee.active:
        return "Cette paroisse est fermée."
    actuelle = membre.affectations.filter(date_fin__isnull=True).first()
    if actuelle is None:
        return "Ce membre n'a pas d'affectation actuelle."
    if paroisse_depart_attendue is not None and actuelle.paroisse_id != paroisse_depart_attendue.pk:
        return "le membre n'est plus dans la paroisse de départ."
    if actuelle.paroisse_id == paroisse_arrivee.pk:
        return "Le membre est déjà dans cette paroisse."
    return None


def demander_mutation(*, membre, paroisse_arrivee, par, motif: str = "") -> Mutation:
    obstacle = _obstacle_mutation(membre, paroisse_arrivee)
    if obstacle:
        raise MouvementRefuse(obstacle)
    if membre.mutations.filter(etat__in=EN_COURS).exists():
        raise MouvementRefuse("Une demande de mutation est déjà en cours pour ce membre.")
    depart = membre.affectation_actuelle.paroisse
    try:
        with transaction.atomic():
            mutation = Mutation.objects.create(
                membre=membre,
                paroisse_depart=depart,
                paroisse_arrivee=paroisse_arrivee,
                motif=motif,
                demandee_par=par,
            )
    except IntegrityError as exc:  # demande simultanée
        raise MouvementRefuse("Une demande de mutation est déjà en cours pour ce membre.") from exc
    journaliser(par, journal.MUTATION_DEMANDEE, mutation=mutation.pk, membre=membre.matricule)
    notifier_unites(
        [*unites_de_paroisse(depart), NATIONAL],
        f"Demande de mutation de {membre.matricule} — {membre.nom_complet} "
        f"vers {paroisse_arrivee.nom}",
        lien_mutation(mutation),
    )
    return mutation


def donner_avis(*, mutation, niveau: str, favorable: bool, commentaire: str, par) -> AvisMutation:
    libelle = {"circuit": "du circuit", "region": "de la région"}[niveau]
    with transaction.atomic():
        mutation = Mutation.objects.select_for_update().get(pk=mutation.pk)
        if mutation.etat != EtatDemande.AVIS:
            raise MouvementRefuse("Cette demande n'attend plus d'avis.")
        if mutation.avis.filter(niveau=niveau).exists():
            raise MouvementRefuse(f"L'avis {libelle} a déjà été donné.")
        avis = AvisMutation.objects.create(
            mutation=mutation, niveau=niveau, favorable=favorable, commentaire=commentaire, par=par
        )
        if mutation.avis.count() == 2:
            mutation.etat = EtatDemande.BN
            mutation.save(update_fields=["etat"])
    journaliser(
        par, journal.MUTATION_AVIS, mutation=mutation.pk, niveau=niveau, favorable=favorable
    )
    sens = "favorable" if favorable else "défavorable"
    notifier_unites(
        [NATIONAL, Unite(Niveau.PAROISSE, mutation.paroisse_arrivee)],
        f"Avis {sens} {libelle} sur la mutation de {_decrire(mutation)}",
        lien_mutation(mutation),
    )
    return avis


def decider_mutation(
    *,
    mutation,
    valider: bool,
    par,
    commentaire: str = "",
    jour: datetime.date | None = None,
) -> Mutation:
    jour = jour or timezone.localdate()
    with transaction.atomic():
        mutation = Mutation.objects.select_for_update().select_related("membre").get(pk=mutation.pk)
        if mutation.etat not in EN_COURS:
            raise MouvementRefuse("Cette demande a déjà été traitée.")
        membre, depart, arrivee = (
            mutation.membre,
            mutation.paroisse_depart,
            mutation.paroisse_arrivee,
        )
        if valider:
            obstacle = _obstacle_mutation(membre, arrivee, depart)
            if obstacle:
                raison = obstacle[0].lower() + obstacle[1:]
                raise MouvementRefuse(
                    f"La situation du membre a changé depuis la demande : {raison}"
                )
            ancienne = membre.affectations.select_for_update().get(date_fin__isnull=True)
            ancienne.date_fin = jour
            ancienne.save(update_fields=["date_fin"])
            Affectation.objects.create(
                membre=membre,
                paroisse=arrivee,
                circuit_a_date=arrivee.circuit,
                region_a_date=arrivee.circuit.region,
                date_debut=jour,
                motif=f"Mutation n° {mutation.pk}",
            )
            quittees = set()
            if depart != arrivee:
                quittees.add(depart)
            if depart.circuit != arrivee.circuit:
                quittees.add(depart.circuit)
            if depart.circuit.region != arrivee.circuit.region:
                quittees.add(depart.circuit.region)
            clore_mandats(membre, jour, quittees)
        mutation.etat = EtatDemande.VALIDEE if valider else EtatDemande.REFUSEE
        mutation.decidee_par = par
        mutation.date_decision = timezone.now()
        mutation.commentaire_decision = commentaire
        mutation.save()
    journaliser(
        par,
        journal.MUTATION_DECIDEE,
        mutation=mutation.pk,
        membre=membre.matricule,
        valider=valider,
        commentaire=commentaire,
    )
    decision = "validée" if valider else "refusée"
    texte = f"Mutation {decision} : {_decrire(mutation)}"
    if commentaire:
        texte += f" — {commentaire}"
    unites = {*unites_de_paroisse(depart), *unites_de_paroisse(arrivee), NATIONAL}
    notifier_unites(unites, texte, lien_mutation(mutation), comptes=[membre.compte])
    return mutation


def mutations_pour_unite(unite: Unite) -> QuerySet[Mutation]:
    qs = Mutation.objects.select_related("membre", "paroisse_depart", "paroisse_arrivee").order_by(
        "-date_demande", "-pk"
    )
    if unite.niveau == Niveau.NATIONAL:
        return qs
    chemin = {
        Niveau.PAROISSE: "",
        Niveau.CIRCUIT: "__circuit",
        Niveau.REGION: "__circuit__region",
    }[unite.niveau]
    return qs.filter(
        Q(**{f"paroisse_depart{chemin}": unite.objet})
        | Q(**{f"paroisse_arrivee{chemin}": unite.objet})
    )
