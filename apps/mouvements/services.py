"""Circuits de validation : mutations (Tâche 2) et signalements (Tâche 3).

Toutes les décisions sont atomiques, verrouillent la demande et revérifient la situation.
"""

import datetime
from collections.abc import Iterable
from dataclasses import dataclass

from django.db import IntegrityError, transaction
from django.db.models import Q, QuerySet
from django.utils import timezone

from apps.bureaux.models import Niveau
from apps.bureaux.perimetre import MODELES, Unite, titulaires_gestion
from apps.journal import models as journal
from apps.journal.services import journaliser
from apps.membres.models import Affectation, Categorie, Membre, Statut
from apps.mouvements.models import (
    EN_COURS,
    TYPES_EXCLUSION,
    AvisMutation,
    EtatDemande,
    Mutation,
    Signalement,
    TypeHistorique,
    TypeSignalement,
)
from apps.mouvements.statuts import (
    STATUTS_AVEC_ACCES,
    ajouter_mois,
    changer_categorie,
    changer_statut,
    clore_mandats,
)
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


def _verrouiller_membre(pk: int):
    """Verrouille la ligne du membre : deux décisions sur lui passent l'une après l'autre."""
    return Membre.objects.select_for_update().get(pk=pk)


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
        membre = _verrouiller_membre(mutation.membre_id)
        mutation = Mutation.objects.select_for_update().get(pk=mutation.pk)
        if mutation.etat not in EN_COURS:
            raise MouvementRefuse("Cette demande a déjà été traitée.")
        mutation.membre = membre
        depart, arrivee = mutation.paroisse_depart, mutation.paroisse_arrivee
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
            clore_mandats(membre, jour, unites_quittees(depart, arrivee))
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


def unites_quittees(depart, arrivee) -> set:
    """Paroisse, circuit et région que le membre quitte (ceux qui changent)."""
    quittees = set()
    if depart != arrivee:
        quittees.add(depart)
    if depart.circuit != arrivee.circuit:
        quittees.add(depart.circuit)
    if depart.circuit.region != arrivee.circuit.region:
        quittees.add(depart.circuit.region)
    return quittees


def mandats_a_clore(mutation: Mutation) -> list:
    """Mandats en cours qui seront clos si la mutation est validée (pour prévenir le BN)."""
    quittees = unites_quittees(mutation.paroisse_depart, mutation.paroisse_arrivee)
    mandats = mutation.membre.mandats.en_cours().select_related(
        "fonction", "paroisse", "circuit", "region"
    )
    return [m for m in mandats if m.unite in quittees]


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


# --- Signalements : décès, démission, réhabilitation, catégorie --------------------------

MESSAGE_DATE_INCONNUE = "Date de démission ou d'exclusion inconnue : le BN doit la régulariser."
CONFIRMATIONS = {
    TypeSignalement.DECES: "Décès confirmé",
    TypeSignalement.DEMISSION: "Démission confirmée",
    TypeSignalement.REHABILITATION: "Réhabilitation validée",
    TypeSignalement.CATEGORIE: "Changement de catégorie validé",
}


@dataclass
class Decision:
    signalement: Signalement
    pdf: bytes | None = None


def lien_signalement(signalement: Signalement) -> str:
    return f"/bureau/bn/signalements/{signalement.pk}/"


def _unite_par_cle(cle: str) -> Unite | None:
    if cle == "national":
        return NATIONAL
    niveau, _, ident = cle.partition("-")
    if niveau in MODELES and ident.isdigit():
        objet = MODELES[niveau].objects.filter(pk=int(ident)).first()
        if objet:
            return Unite(niveau, objet)
    return None


def _unites_du_membre(membre) -> list[Unite]:
    actuelle = membre.affectation_actuelle
    return unites_de_paroisse(actuelle.paroisse) if actuelle else []


def blocage_rehabilitation(membre, jour: datetime.date) -> str | None:
    if membre.statut not in (Statut.DEMISSIONNAIRE, Statut.EXCLU):
        return "Seul un membre démissionnaire ou exclu peut être réhabilité."
    statuts = membre.historique.filter(type=TypeHistorique.STATUT)
    rehabilitations = statuts.filter(
        ancien=Statut.EXCLU,
        nouveau=Statut.ACTIF,
        motif=CONFIRMATIONS[TypeSignalement.REHABILITATION],
    )  # la fin d'une exclusion temporaire (sanction échue) n'est pas une réhabilitation
    if membre.statut == Statut.EXCLU and rehabilitations.exists():
        return (
            "Ce membre, déjà réhabilité après une exclusion puis exclu à nouveau, ne peut plus "
            "être réhabilité (règlement intérieur, art. 172)."
        )
    sortie = statuts.filter(nouveau=membre.statut).order_by("-date_effet", "-pk").first()
    if sortie is None:
        return MESSAGE_DATE_INCONNUE
    possible = ajouter_mois(sortie.date_effet, 6)
    if jour < possible:
        return (
            f"Réhabilitation possible à partir du {possible:%d/%m/%Y} "
            "(6 mois après la démission ou l'exclusion)."
        )
    return None


def _verifier(type_, membre, date_effet, reference, nouvelle_categorie, jour) -> None:
    if type_ in (TypeSignalement.DECES, TypeSignalement.DEMISSION):
        if membre.statut not in STATUTS_AVEC_ACCES:
            raise MouvementRefuse("Seul un membre actif ou sanctionné peut être concerné.")
        if date_effet is None:
            raise MouvementRefuse("Indiquez la date.")
        if date_effet > jour:
            raise MouvementRefuse("La date ne peut pas être dans le futur.")
        if membre.date_naissance and date_effet < membre.date_naissance:
            raise MouvementRefuse("La date ne peut pas précéder la date de naissance.")
    elif type_ == TypeSignalement.REHABILITATION:
        blocage = blocage_rehabilitation(membre, jour)
        if blocage:
            raise MouvementRefuse(blocage)
        if membre.statut == Statut.EXCLU and not reference.strip():
            raise MouvementRefuse(
                "La référence de l'engagement écrit de bonne conduite est obligatoire "
                "pour un membre exclu."
            )
    elif type_ == TypeSignalement.CATEGORIE:
        if nouvelle_categorie not in Categorie.values:
            raise MouvementRefuse("Choisissez la nouvelle catégorie.")
        if nouvelle_categorie == membre.categorie:
            raise MouvementRefuse("Le membre est déjà dans cette catégorie.")
    else:
        raise MouvementRefuse("Type de signalement inconnu.")


def signaler(
    *,
    membre,
    type: str,  # noqa: A002 — nom métier
    par,
    unite: str,
    date_effet: datetime.date | None = None,
    reference: str = "",
    nouvelle_categorie: str = "",
    commentaire: str = "",
    jour: datetime.date | None = None,
) -> Signalement:
    jour = jour or timezone.localdate()
    _verifier(type, membre, date_effet, reference, nouvelle_categorie, jour)
    deja = "Un signalement de ce type est déjà en attente."
    if membre.signalements.filter(type=type, etat=EtatDemande.BN).exists():
        raise MouvementRefuse(deja)
    try:
        with transaction.atomic():
            sig = Signalement.objects.create(
                membre=membre,
                type=type,
                date_effet=date_effet,
                reference=reference.strip(),
                nouvelle_categorie=nouvelle_categorie,
                commentaire=commentaire,
                unite=unite,
                demande_par=par,
            )
    except IntegrityError as exc:
        raise MouvementRefuse(deja) from exc
    journaliser(par, journal.SIGNALEMENT, unite=unite, type=type, membre=membre.matricule)
    notifier_unites(
        [NATIONAL],
        f"{sig.get_type_display()} signalé pour {membre.matricule} — {membre.nom_complet}",
        lien_signalement(sig),
    )
    return sig


def decider_signalement(
    *,
    signalement,
    confirmer: bool,
    par,
    motif_refus: str = "",
    jour: datetime.date | None = None,
) -> Decision:
    from apps.membres.pdf import fiche_identification_pdf
    from apps.membres.services import generer_mot_de_passe_provisoire

    jour = jour or timezone.localdate()
    pdf = None
    with transaction.atomic():
        membre = _verrouiller_membre(signalement.membre_id)
        sig = Signalement.objects.select_for_update().get(pk=signalement.pk)
        if sig.etat != EtatDemande.BN:
            raise MouvementRefuse("Cette demande a déjà été traitée.")
        sig.membre = membre
        if confirmer:
            _verifier(sig.type, membre, sig.date_effet, sig.reference, sig.nouvelle_categorie, jour)
            motif = CONFIRMATIONS[sig.type]
            if sig.type in (TypeSignalement.DECES, TypeSignalement.DEMISSION):
                nouveau = (
                    Statut.DECEDE if sig.type == TypeSignalement.DECES else Statut.DEMISSIONNAIRE
                )
                changer_statut(
                    membre,
                    nouveau,
                    par=par,
                    date_effet=sig.date_effet,
                    motif=motif,
                    reference=sig.reference,
                )
                _annuler_mutations(membre, f"Annulée : {motif.lower()}")
            elif sig.type == TypeSignalement.REHABILITATION:
                changer_statut(
                    membre,
                    Statut.ACTIF,
                    par=par,
                    date_effet=jour,
                    motif=motif,
                    reference=sig.reference,
                )
                mot_de_passe = generer_mot_de_passe_provisoire()
                compte = membre.compte
                compte.set_password(mot_de_passe)
                compte.doit_changer_mot_de_passe = True
                compte.save(update_fields=["password", "doit_changer_mot_de_passe"])
                pdf = fiche_identification_pdf(membre, mot_de_passe)
                # Les exclusions encore « en cours » sont levées : sinon la tâche quotidienne
                # des sanctions exclurait de nouveau le membre réhabilité.
                membre.sanctions.filter(
                    type__in=list(TYPES_EXCLUSION), levee_le__isnull=True
                ).update(
                    levee_le=jour, levee_par=par, motif_levee="Réhabilitation validée par le BN"
                )
            else:
                changer_categorie(
                    membre, sig.nouvelle_categorie, par=par, date_effet=jour, motif=motif
                )
        sig.etat = EtatDemande.VALIDEE if confirmer else EtatDemande.REFUSEE
        sig.decide_par = par
        sig.date_decision = timezone.now()
        sig.motif_refus = "" if confirmer else motif_refus
        sig.save()
    journaliser(
        par,
        journal.SIGNALEMENT_DECIDE,
        unite=sig.unite,
        type=sig.type,
        membre=membre.matricule,
        confirmer=confirmer,
        motif_refus=sig.motif_refus,
    )
    qui = f"{membre.matricule} — {membre.nom_complet}"
    if confirmer:
        texte = f"{CONFIRMATIONS[sig.type]} : {qui}"
        if sig.type == TypeSignalement.CATEGORIE:
            texte += f" — {sig.get_nouvelle_categorie_display()}"
    else:
        texte = f"Signalement refusé ({sig.get_type_display().lower()}) : {qui}"
        if motif_refus:
            texte += f" — {motif_refus}"
    unites = set(_unites_du_membre(membre))
    signalante = _unite_par_cle(sig.unite)
    if signalante:
        unites.add(signalante)
    notifier_unites(unites, texte, comptes=[membre.compte] if membre.compte_id else [])
    return Decision(signalement=sig, pdf=pdf)


def _annuler_mutations(membre, commentaire: str) -> None:
    for mutation in Mutation.objects.select_for_update().filter(membre=membre, etat__in=EN_COURS):
        mutation.etat = EtatDemande.ANNULEE
        mutation.commentaire_decision = commentaire
        mutation.date_decision = timezone.now()
        mutation.save(update_fields=["etat", "commentaire_decision", "date_decision"])
        transaction.on_commit(
            lambda m=mutation: notifier_unites(
                [Unite(Niveau.PAROISSE, m.paroisse_arrivee), NATIONAL],
                f"Mutation annulée : {_decrire(m)} — {commentaire}",
                lien_mutation(m),
            )
        )
