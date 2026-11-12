"""Lecture du journal : chaque entrée devient une phrase en français, facile à comprendre.

Le journal reste enregistré tel quel (immuable) ; seule sa présentation est traduite ici.
"""

import datetime
from dataclasses import dataclass

from apps.journal import models as j

# Actions réservées au Bureau national : sans unité enregistrée, elles relèvent du national.
ACTIONS_NATIONALES = {
    j.ENREGISTREMENT,
    j.LOT_VALIDE,
    j.PHOTO_DECISION,
    j.CORRECTION_INTEGRATION,
    j.SANCTION,
    j.SANCTION_LEVEE,
    j.FIN_SANCTION,
    j.MUTATION_DECIDEE,
    j.TRANCHES_AGE,
    j.GRADE_ATTRIBUE,
    j.GRADE_PROMOTION,
    j.GRADE_CORRECTION,
    j.REGLAGE_COTISATIONS,
}
DOUBLE_VERIFICATION = {
    "activation": "A activé sa double vérification.",
    "code_correct": "A saisi un code de double vérification correct.",
    "deconnexion_apres_echecs": "A été déconnecté après trop de codes de double vérification faux.",
}


@dataclass
class Ligne:
    date: datetime.datetime
    auteur: str
    texte: str
    unite: str
    details: dict


def _libelles(choix) -> dict:
    return {valeur: str(libelle) for valeur, libelle in choix}


def _date(iso) -> str:
    try:
        return datetime.date.fromisoformat(iso).strftime("%d/%m/%Y")
    except (TypeError, ValueError):
        return str(iso or "")


def _unites(cles: set[str]) -> dict[str, str]:
    from apps.bureaux.perimetre import MODELES, Unite

    noms = {"national": "Bureau national"}
    for cle in cles:
        niveau, _, ident = cle.partition("-")
        if niveau in MODELES and ident.isdigit():
            objet = MODELES[niveau].objects.filter(pk=int(ident)).first()
            if objet is not None:
                noms[cle] = Unite(niveau, objet).libelle
    return noms


def lire(entrees) -> list[Ligne]:
    """Traduit des entrées du journal en lignes lisibles (quelques requêtes pour toute la page)."""
    from apps.cotisations.services import periode as periode_mois
    from apps.grades.models import ModeGrade
    from apps.membres.models import Membre, Statut
    from apps.mouvements.models import TypeSanction, TypeSignalement

    entrees = list(entrees)
    matricules = set()
    for e in entrees:
        if isinstance(e.details.get("membre"), str):
            matricules.add(e.details["membre"])
        if isinstance(e.details.get("titulaires"), dict):
            matricules.update(v for v in e.details["titulaires"].values() if isinstance(v, str))
    noms = {
        m.matricule: f"{m.nom_complet} ({m.matricule})"
        for m in Membre.objects.filter(matricule__in=matricules)
    }
    unites = _unites({e.unite for e in entrees if e.unite})
    modes = _libelles(ModeGrade.choices)
    sanctions = _libelles(TypeSanction.choices)
    signalements = _libelles(TypeSignalement.choices)
    statuts = _libelles(Statut.choices)

    def qui(matricule) -> str:
        return noms.get(matricule, str(matricule or "?"))

    def phrase(e) -> str:
        d, a = e.details, e.action
        m = qui(d.get("membre"))
        if a == j.ENREGISTREMENT:
            return f"A enregistré le membre {m}."
        if a == j.GRADE_PROMOTION:
            mode = modes.get(d.get("mode"), d.get("mode", "")).lower()
            return f"A fait passer {m} au grade de {d.get('grade')} ({mode})."
        if a == j.GRADE_CORRECTION:
            return f"A corrigé le grade de {m} : {d.get('grade')}."
        if a == j.GRADE_ATTRIBUE:
            return f"A attribué le grade {d.get('grade')} à {m}."
        if a == j.CONSULTATION_FICHE:
            return f"A consulté la fiche de {m}."
        if a == j.PHOTO_DECISION:
            if d.get("decision") == "accepter":
                return f"A accepté la photo d'identité de {m}."
            return f"A refusé la photo d'identité de {m} (motif : {d.get('motif', '')})."
        if a == j.CORRECTION_INTEGRATION:
            return f"A corrigé les données d'intégration de {m} (motif : {d.get('motif', '')})."
        if a == j.COORDONNEES:
            champs = ", ".join(d.get("changements", {})) if d.get("changements") else ""
            return f"A modifié les coordonnées de {m}" + (f" ({champs})." if champs else ".")
        if a == j.MUTATION_DEMANDEE:
            return f"A demandé la mutation de {m} (demande n° {d.get('mutation')})."
        if a == j.MUTATION_AVIS:
            sens = "favorable" if d.get("favorable") else "défavorable"
            return f"A donné un avis {sens} sur la demande de mutation n° {d.get('mutation')}."
        if a == j.MUTATION_DECIDEE:
            verbe = "validé" if d.get("valider") else "refusé"
            return f"A {verbe} la mutation de {m} (demande n° {d.get('mutation')})."
        if a == j.SIGNALEMENT:
            return f"A signalé : {signalements.get(d.get('type'), d.get('type'))} de {m}."
        if a == j.SIGNALEMENT_DECIDE:
            verbe = "confirmé" if d.get("confirmer") else "refusé"
            quoi = signalements.get(d.get("type"), d.get("type"))
            return f"A {verbe} le signalement ({quoi}) concernant {m}."
        if a == j.SANCTION and "avant" in d:
            return (
                f"Début de la sanction de {m} : statut {statuts.get(d.get('avant'), '')} → "
                f"{statuts.get(d.get('apres'), '')}."
            )
        if a == j.SANCTION:
            periode = f"du {_date(d.get('date_debut'))}"
            if d.get("date_fin"):
                periode += f" au {_date(d.get('date_fin'))}"
            ref = f", référence {d['reference']}" if d.get("reference") else ""
            quoi = sanctions.get(d.get("type"), d.get("type"))
            return (
                f"A inscrit une sanction contre {m} : {quoi} (degré {d.get('degre')}), "
                f"{periode}{ref}."
            )
        if a == j.SANCTION_LEVEE:
            return f"A levé une sanction de {m} (motif : {d.get('motif', '')})."
        if a == j.FIN_SANCTION:
            return (
                f"Fin de la sanction de {m} : statut {statuts.get(d.get('avant'), '')} → "
                f"{statuts.get(d.get('apres'), '')}."
            )
        if a == j.INSTALLATION_BUREAU:
            titulaires = "; ".join(f"{f} : {qui(t)}" for f, t in d.get("titulaires", {}).items())
            return f"A installé le bureau à compter du {_date(d.get('date_debut'))} — {titulaires}."
        if a == j.REINITIALISATION:
            return f"A réinitialisé le mot de passe de {m}."
        if a == j.LOT_VALIDE:
            return (
                f"A validé le lot Excel n° {d.get('lot')} : "
                f"{d.get('membres')} membre(s) enregistré(s)."
            )
        if a in (j.LISTE_PDF, j.LISTE_EXCEL):
            forme = "PDF" if a == j.LISTE_PDF else "Excel"
            return f"A téléchargé une liste de {d.get('lignes')} membre(s) en {forme}."
        if a == j.STATISTIQUES_PDF:
            return "A téléchargé les statistiques en PDF."
        if a == j.TRANCHES_AGE:
            return (
                "A modifié les tranches d'âge des statistiques : "
                f"{d.get('avant')} → {d.get('apres')}."
            )
        if a == j.VERSEMENT_SAISI:
            mois = [datetime.date.fromisoformat(x) for x in d.get("mois", [])]
            quand = periode_mois(mois)
            return f"A enregistré un versement de {d.get('montant')} F pour {m} ({quand})."
        if a == j.VERSEMENT_VALIDE:
            return f"A validé le versement de {d.get('montant')} F de {m} (reçu {d.get('recu')})."
        if a == j.VERSEMENT_REFUSE:
            return (
                f"A refusé le versement de {d.get('montant')} F de {m} "
                f"(motif : {d.get('motif', '')})."
            )
        if a == j.VERSEMENT_ANNULE:
            return (
                f"A annulé le versement de {d.get('montant')} F de {m} "
                f"(motif : {d.get('motif', '')})."
            )
        if a == j.PART_RECUE:
            niveau = {"circuit": "du circuit", "region": "de la région"}.get(
                d.get("niveau"), "du Bureau national"
            )
            mois = datetime.date.fromisoformat(d["mois"]) if d.get("mois") else None
            quand = periode_mois([mois] if mois else [])
            return (
                f"A marqué comme reçue la part {niveau} : {d.get('montant')} F de la paroisse "
                f"{d.get('paroisse')} (versements validés en {quand})."
            )
        if a == j.REGLAGE_COTISATIONS:
            morceaux = []
            if d.get("mois_depart"):
                depart = datetime.date.fromisoformat(d["mois_depart"])
                morceaux.append(f"a fixé le premier mois suivi à {periode_mois([depart])}")
            t = d.get("tarif") or {}
            if t:
                effet = datetime.date.fromisoformat(t.get("date_effet", "2000-01-01")[:10])
                morceaux.append(
                    f"a fixé le tarif à {t.get('montant')} F par mois à compter de "
                    f"{periode_mois([effet])} (paroisse {t.get('part_paroisse')} %, circuit "
                    f"{t.get('part_circuit')} %, région {t.get('part_region')} %, national "
                    f"{t.get('part_national')} %)"
                )
            texte = " ; ".join(morceaux) or "a modifié les réglages"
            return f"Cotisations mensuelles : {texte}."
        if a == j.EVENEMENT_CREE:
            return f"A créé l'événement « {d.get('nom')} »."
        if a == j.EVENEMENT_MODIFIE:
            return f"A modifié l'événement « {d.get('nom')} »."
        if a == j.EVENEMENT_ANNULE:
            return f"A annulé l'événement « {d.get('nom')} » (motif : {d.get('motif', '')})."
        if a == j.CONVOCATION and "ancienne_session" in d:
            avant = d.get("ancienne_session") or "sans session"
            apres = d.get("session") or "sans session"
            return f"A changé la session de {m} à « {d.get('nom')} » : {avant} → {apres}."
        if a == j.CONVOCATION:
            session = f", {d['session']}" if d.get("session") else ""
            return f"A convoqué {m} à « {d.get('nom')} »{session}."
        if a == j.CONVOCATION_RETIREE:
            return (
                f"A retiré la convocation de {m} à « {d.get('nom')} » "
                f"(motif : {d.get('motif', '')})."
            )
        if a == j.PRESENCE:
            etat = {"present": "présent", "absent": "absent", "excuse": "excusé"}.get(
                d.get("presence"), d.get("presence")
            )
            return f"A pointé {m} : {etat} à « {d.get('nom')} »."
        if a == j.CONNEXION:
            return "S'est connecté au site."
        if a == j.CONNEXION_ECHOUEE:
            return (
                f"Tentative de connexion refusée avec l'identifiant « {d.get('identifiant', '')} »."
            )
        if a == j.DOUBLE_VERIFICATION:
            ev = d.get("evenement")
            if ev == "code_faux":
                return f"A saisi un code de double vérification faux (essai n° {d.get('essai')})."
            if ev == "reinitialisation":
                return (
                    f"Double vérification réinitialisée pour le compte {d.get('compte')} "
                    "(commande technique)."
                )
            return DOUBLE_VERIFICATION.get(ev, j.LIBELLES[a])
        return j.LIBELLES.get(a, a)

    def auteur(e) -> str:
        if e.auteur_id or getattr(e, "auteur", None):
            return str(e.auteur)
        if e.action == j.CONNEXION_ECHOUEE:
            return "Inconnu"
        return "Le site (tâche automatique)"

    def unite(e) -> str:
        if e.unite:
            return unites.get(e.unite, e.unite)
        return "Bureau national" if e.action in ACTIONS_NATIONALES else "—"

    return [Ligne(e.date, auteur(e), phrase(e), unite(e), e.details) for e in entrees]
