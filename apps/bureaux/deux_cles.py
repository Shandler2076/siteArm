"""Deux clés et délégation au Bureau National de Commandement (décisions du 19/11/2026).

- Ce que fait le **Secrétaire national** (installer / remplacer / pourvoir un bureau, droits
  des fonctions, sanctions) n'est appliqué qu'après validation : `soumettre_ou_executer`.
- Valide : le **Président** ; le **Vice-président** si le poste de Président est vacant, ou si
  la demande attend depuis 7 jours ; ou la personne à qui le Président a **délégué**.
- Ce que fait le Président seul est appliqué tout de suite et **notifié au Secrétaire**.
- Une demande non traitée en 30 jours expire ; tout est inscrit au journal.
"""

import datetime

from django.db import transaction
from django.utils import timezone

from apps.bureaux.models import Delegation, DemandeValidation, Fonction, Mandat
from apps.membres.models import Statut

Etat = DemandeValidation.Etat
DELAI_VICE_PRESIDENT = datetime.timedelta(days=7)
DUREE_DEMANDE = datetime.timedelta(days=30)


class DeuxClesRefusee(ValueError):
    pass


# --- Qui est qui ----------------------------------------------------------------------------
def _titulaires(nom: str):
    from apps.comptes.models import Compte

    mandats = Mandat.objects.en_cours().filter(
        fonction__niveau="national", fonction__nom=nom, membre__statut=Statut.ACTIF
    )
    return Compte.objects.filter(is_active=True, membre__in=mandats.values("membre")).distinct()


def _noms_fonctions(compte) -> frozenset:
    from apps.bureaux.perimetre import fonctions_nationales

    return fonctions_nationales(compte)


def _a_la_fonction(compte, nom: str) -> bool:
    return nom in _noms_fonctions(compte)


def presidence_vacante() -> bool:
    return not _titulaires("Président").exists()


def delegation_active(compte, objet: str) -> Delegation | None:
    """Délégation en cours, donnée par un Président encore en fonction."""
    maintenant = timezone.now()
    for d in Delegation.objects.filter(
        delegataire=compte, objet=objet, retiree_le__isnull=True, fin__gt=maintenant
    ).select_related("delegant"):
        if d.active(maintenant) and _a_la_fonction(d.delegant, "Président"):
            return d
    return None


def doit_etre_valide(compte) -> bool:
    """Le Secrétaire national prépare ; le Président (ou le compte technique) agit directement."""
    if getattr(compte, "is_superuser", False) or _a_la_fonction(compte, "Président"):
        return False
    return _a_la_fonction(compte, "Secrétaire national")


def qualite_pour_valider(compte, demande: DemandeValidation) -> str:
    """« Président », « Vice-président (…) », « sur délégation du Président », ou « »."""
    if demande.preparee_par_id == getattr(compte, "pk", None):
        return ""
    if _a_la_fonction(compte, "Président"):
        return "Président"
    if _a_la_fonction(compte, "Vice-président"):
        if presidence_vacante():
            return "Vice-président (poste de Président vacant)"
        if timezone.now() - demande.date >= DELAI_VICE_PRESIDENT:
            return "Vice-président (Président sans réponse depuis 7 jours)"
    if _noms_fonctions(compte) and delegation_active(compte, Delegation.Objet.DEUX_CLES):
        return "sur délégation du Président"
    return ""


def peut_voir_les_demandes(compte) -> bool:
    if _noms_fonctions(compte) & {"Président", "Vice-président", "Secrétaire national"}:
        return True
    # Une délégation ne va qu'à un membre du Bureau National de Commandement.
    return bool(_noms_fonctions(compte)) and bool(
        delegation_active(compte, Delegation.Objet.DEUX_CLES)
    )


# --- Actions --------------------------------------------------------------------------------
def _membre(matricule):
    from apps.membres.models import Membre

    return Membre.objects.get(matricule=matricule) if matricule else None


def _date(valeur):
    return datetime.date.fromisoformat(valeur) if valeur else None


def _installer(d, par):
    from apps.bureaux.perimetre import unite_par_cle
    from apps.bureaux.services import installer_bureau

    titulaires = {Fonction.objects.get(pk=int(f)): _membre(m) for f, m in d["titulaires"].items()}
    return installer_bureau(
        unite=unite_par_cle(d["unite"]),
        titulaires=titulaires,
        date_debut=_date(d["date_debut"]),
        par=par,
    )


def _remplacer(d, par):
    from apps.bureaux.services import remplacer_titulaire

    return remplacer_titulaire(
        mandat=Mandat.objects.get(pk=d["mandat"]),
        date=_date(d["date"]),
        motif=d["motif"],
        remplacant=_membre(d.get("remplacant")),
        par=par,
    )


def _pourvoir(d, par):
    from apps.bureaux.perimetre import unite_par_cle
    from apps.bureaux.services import pourvoir_poste

    return pourvoir_poste(
        unite=unite_par_cle(d["unite"]),
        fonction=Fonction.objects.get(pk=d["fonction"]),
        membre=_membre(d["membre"]),
        date_debut=_date(d["date_debut"]),
        par=par,
    )


def _droits(d, par):
    from apps.bureaux.services import modifier_droit

    return modifier_droit(
        fonction=Fonction.objects.get(pk=d["fonction"]), case=d["case"], valeur=d["valeur"], par=par
    )


def _sanction(d, par):
    from apps.mouvements.sanctions import enregistrer_sanction

    champs = dict(d["champs"])
    for cle in ("date_debut", "date_fin"):
        champs[cle] = _date(champs.get(cle))
    return enregistrer_sanction(membre=_membre(d["membre"]), par=par, **champs)


def _lever(d, par):
    from apps.mouvements.models import Sanction
    from apps.mouvements.sanctions import lever_sanction

    return lever_sanction(
        sanction=Sanction.objects.get(pk=d["sanction"]), motif=d["motif"], par=par
    )


ACTIONS = {
    "installer": ("Installer un bureau", _installer),
    "remplacer": ("Remplacer ou retirer un titulaire", _remplacer),
    "pourvoir": ("Pourvoir un poste vacant", _pourvoir),
    "droits": ("Modifier les droits d'une fonction", _droits),
    "sanction": ("Inscrire une sanction", _sanction),
    "lever": ("Lever une sanction", _lever),
}


def _erreurs_metier():
    from apps.bureaux.services import InstallationRefusee
    from apps.mouvements.services import MouvementRefuse

    return (InstallationRefusee, MouvementRefuse, DeuxClesRefusee)


def _notifier_secretaires(texte: str, sauf=None):
    from apps.notifications.services import notifier

    notifier(
        [c for c in _titulaires("Secrétaire national") if c.pk != getattr(sauf, "pk", None)],
        texte,
        "/bureau/bn/validations/",
    )


def soumettre_ou_executer(compte, action: str, donnees: dict, resume: str):
    """Renvoie (None, résultat) si l'action est appliquée tout de suite, ou (demande, None) si
    elle attend la validation du Président. Les erreurs métier remontent telles quelles."""
    from apps.journal.models import DEMANDE_PREPAREE
    from apps.journal.services import journaliser
    from apps.notifications.services import notifier

    if action not in ACTIONS:
        raise DeuxClesRefusee("Action inconnue.")
    if not doit_etre_valide(compte):
        resultat = ACTIONS[action][1](donnees, compte)
        if _a_la_fonction(compte, "Président"):
            transaction.on_commit(
                lambda: _notifier_secretaires(f"Pour information, le Président a fait : {resume}.")
            )
        return None, resultat
    demande = DemandeValidation.objects.create(
        action=action, resume=resume[:400], donnees=donnees, preparee_par=compte
    )
    journaliser(compte, DEMANDE_PREPAREE, demande=demande.pk, resume=demande.resume)
    destinataires = list(_titulaires("Président"))
    if not destinataires:
        destinataires = list(_titulaires("Vice-président"))
    notifier(destinataires, f"À valider : {demande.resume}", "/bureau/bn/validations/")
    return demande, None


def expirer_demandes() -> int:
    limite = timezone.now() - DUREE_DEMANDE
    return DemandeValidation.objects.filter(etat=Etat.ATTENTE, date__lt=limite).update(
        etat=Etat.EXPIREE
    )


def valider(demande: DemandeValidation, *, par) -> DemandeValidation:
    from apps.journal.models import DEMANDE_DECIDEE
    from apps.journal.services import journaliser
    from apps.notifications.services import notifier

    expirer_demandes()
    qualite = qualite_pour_valider(par, demande)
    if not qualite:
        raise DeuxClesRefusee("Vous ne pouvez pas valider cette demande.")
    with transaction.atomic():
        demande = DemandeValidation.objects.select_for_update().get(pk=demande.pk)
        if demande.etat != Etat.ATTENTE:
            raise DeuxClesRefusee("Cette demande a déjà été traitée.")
        demande.decidee_par, demande.qualite = par, qualite
        demande.date_decision = timezone.now()
        try:
            with transaction.atomic():
                # L'action est faite au nom de son auteur (le Secrétaire), validée par `par`.
                ACTIONS[demande.action][1](demande.donnees, demande.preparee_par)
        except _erreurs_metier() as e:
            demande.etat, demande.motif = Etat.ECHEC, str(e)[:400]
        else:
            demande.etat = Etat.VALIDEE
        demande.save()
    journaliser(
        par,
        DEMANDE_DECIDEE,
        demande=demande.pk,
        resume=demande.resume,
        decision=demande.etat,
        qualite=qualite,
        auteur=demande.preparee_par.identifiant,
    )
    texte = (
        f"Validé ({qualite}) : {demande.resume}"
        if demande.etat == Etat.VALIDEE
        else f"Validé mais impossible à appliquer : {demande.resume} — {demande.motif}"
    )
    notifier([demande.preparee_par], texte, "/bureau/bn/validations/")
    if qualite != "Président":
        notifier(_titulaires("Président"), f"{texte} — par {par}.", "/bureau/bn/validations/")
    return demande


def refuser(demande: DemandeValidation, *, par, motif: str) -> DemandeValidation:
    from apps.journal.models import DEMANDE_DECIDEE
    from apps.journal.services import journaliser
    from apps.notifications.services import notifier

    qualite = qualite_pour_valider(par, demande)
    if not qualite:
        raise DeuxClesRefusee("Vous ne pouvez pas refuser cette demande.")
    if not motif.strip():
        raise DeuxClesRefusee("Indiquez le motif du refus.")
    with transaction.atomic():
        demande = DemandeValidation.objects.select_for_update().get(pk=demande.pk)
        if demande.etat != Etat.ATTENTE:
            raise DeuxClesRefusee("Cette demande a déjà été traitée.")
        demande.etat, demande.motif = Etat.REFUSEE, motif.strip()[:400]
        demande.decidee_par, demande.qualite = par, qualite
        demande.date_decision = timezone.now()
        demande.save()
    journaliser(
        par,
        DEMANDE_DECIDEE,
        demande=demande.pk,
        resume=demande.resume,
        decision=demande.etat,
        qualite=qualite,
        auteur=demande.preparee_par.identifiant,
    )
    notifier(
        [demande.preparee_par],
        f"Refusé ({qualite}) : {demande.resume} — {demande.motif}",
        "/bureau/bn/validations/",
    )
    return demande


def annuler(demande: DemandeValidation, *, par) -> None:
    if demande.preparee_par_id != par.pk or demande.etat != Etat.ATTENTE:
        raise DeuxClesRefusee("Vous ne pouvez pas annuler cette demande.")
    DemandeValidation.objects.filter(pk=demande.pk, etat=Etat.ATTENTE).update(etat=Etat.ANNULEE)


# --- Délégation -----------------------------------------------------------------------------
def deleguer(*, president, delegataire, objet: str, fin: datetime.datetime) -> Delegation:
    from apps.journal.models import DELEGATION
    from apps.journal.services import journaliser
    from apps.notifications.services import notifier

    if not _a_la_fonction(president, "Président"):
        raise DeuxClesRefusee("Seul le Président délègue.")
    if delegataire.pk == president.pk:
        raise DeuxClesRefusee("Choisissez une autre personne que vous-même.")
    if (
        not any(
            _a_la_fonction(delegataire, nom)
            for nom in ("Vice-président", "Secrétaire national", "Secrétaire national adjoint")
        )
        and objet == Delegation.Objet.DEUX_CLES
    ):
        raise DeuxClesRefusee(
            "Déléguez à un membre du Bureau National de Commandement (Vice-président ou "
            "Secrétaire national adjoint)."
        )
    if objet not in Delegation.Objet.values:
        raise DeuxClesRefusee("Choisissez ce que vous déléguez.")
    if fin <= timezone.now() or fin > timezone.now() + datetime.timedelta(days=31):
        raise DeuxClesRefusee("La délégation dure au plus un mois.")
    d = Delegation.objects.create(delegant=president, delegataire=delegataire, objet=objet, fin=fin)
    journaliser(
        president,
        DELEGATION,
        evenement="donnee",
        delegataire=delegataire.identifiant,
        objet=objet,
        fin=fin.isoformat(),
    )
    notifier(
        [delegataire],
        f"Le Président vous délègue : {d.get_objet_display().lower()}, jusqu'au "
        f"{timezone.localtime(fin):%d/%m/%Y à %H:%M}.",
        "/bureau/bn/validations/",
    )
    return d


def retirer_delegation(d: Delegation, *, par) -> None:
    from apps.journal.models import DELEGATION
    from apps.journal.services import journaliser

    if d.delegant_id != par.pk:
        raise DeuxClesRefusee("Seul le Président qui a délégué peut retirer la délégation.")
    Delegation.objects.filter(pk=d.pk, retiree_le__isnull=True).update(retiree_le=timezone.now())
    journaliser(par, DELEGATION, evenement="retiree", delegataire=d.delegataire.identifiant)
