"""Services métier des membres : matricule, enregistrement, doublons."""

import datetime
import secrets
from dataclasses import dataclass

from django.db import IntegrityError, transaction
from django.db.models import Q, QuerySet
from django.utils import timezone

from apps.comptes.models import Compte
from apps.membres.grades import Grade
from apps.membres.models import Affectation, CompteurMatricule, Membre, cle_nom
from apps.organisation.models import Paroisse, Region

__all__ = [
    "CapaciteMatriculeAtteinte",
    "ResultatEnregistrement",
    "attribuer_matricule",
    "cle_nom",
    "doublons_possibles",
    "enregistrer_membre",
    "generer_mot_de_passe_provisoire",
]

NUMERO_MAX = 9999


class CapaciteMatriculeAtteinte(Exception):
    def __init__(self, annee: int, region: Region):
        super().__init__(
            f"Le nombre maximal de 9 999 matricules est atteint pour l'année {annee} "
            f"dans la région {region.code}."
        )


def attribuer_matricule(annee: int, region: Region) -> str:
    """Prend le prochain numéro pour (année, région) sous verrou. À appeler dans une transaction."""
    if not transaction.get_connection().in_atomic_block:
        raise RuntimeError("attribuer_matricule doit être appelée dans une transaction.")
    try:
        with transaction.atomic():
            CompteurMatricule.objects.get_or_create(annee=annee, region=region)
    except IntegrityError:
        pass  # créé au même instant par un autre enregistrement : on le relit sous verrou
    compteur = CompteurMatricule.objects.select_for_update().get(annee=annee, region=region)
    if compteur.dernier_numero >= NUMERO_MAX:
        raise CapaciteMatriculeAtteinte(annee, region)
    compteur.dernier_numero += 1
    compteur.save(update_fields=["dernier_numero"])
    return f"{annee:04d}-{region.code}AS-{compteur.dernier_numero:04d}"


# --- Enregistrement d'un membre -------------------------------------------------------------

ALPHABET_PROVISOIRE = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghjkmnpqrstuvwxyz23456789"


def generer_mot_de_passe_provisoire() -> str:
    """10 caractères lisibles (sans 0/O/1/l/I), avec majuscule, minuscule et chiffre."""
    while True:
        mdp = "".join(secrets.choice(ALPHABET_PROVISOIRE) for _ in range(10))
        if (
            any(c.isupper() for c in mdp)
            and any(c.islower() for c in mdp)
            and any(c.isdigit() for c in mdp)
        ):
            return mdp


def doublons_possibles(
    *, nom: str, prenoms: str, date_naissance: datetime.date | None, npi: str = ""
) -> QuerySet[Membre]:
    """Même NPI, ou même nom et prénoms (écriture normalisée) et même date de naissance."""
    critere = Q(cle_identite=f"{cle_nom(nom)} | {cle_nom(prenoms)}")
    if date_naissance:
        critere &= Q(date_naissance=date_naissance) | Q(date_naissance__isnull=True)
    if npi:
        critere |= Q(npi=npi)
    return Membre.objects.filter(critere)


@dataclass(frozen=True)
class ResultatEnregistrement:
    membre: Membre
    mot_de_passe: str


def enregistrer_membre(
    *,
    donnees: dict,
    paroisse_integration: Paroisse,
    annee_integration: int,
    par: Compte,
    paroisse_actuelle: Paroisse | None = None,
    date_integration: datetime.date | None = None,
    notifier: bool = True,
    avec_mot_de_passe: bool = True,
    grade: int = Grade.CAMARADE,
    date_grade: datetime.date | None = None,
    regularisation: bool = False,
) -> ResultatEnregistrement:
    """Crée en une seule transaction : matricule, compte, membre et première affectation.

    En cas d'échec, rien n'est créé, y compris le fichier de la photo du CIP éventuelle.
    Grade : Camarade par défaut ; un grade donné (`regularisation`) est daté de `date_grade`,
    sinon de la date d'intégration.
    Paroisse actuelle (si différente de la paroisse d'intégration) : le membre y est affecté à
    partir du jour de son inscription sur le site ; le matricule garde la région d'intégration.
    """
    from apps.grades.services import attribuer_grade_initial

    region = paroisse_integration.region
    membre = Membre(
        **donnees,
        annee_integration=annee_integration,
        paroisse_integration=paroisse_integration,
        region_integration=region,
        enregistre_par=par,
    )
    try:
        with transaction.atomic():
            membre.matricule = attribuer_matricule(annee_integration, region)
            membre.full_clean(exclude=["compte"])
            # Lots : pas de hachage inutile, le mot de passe est créé à l'impression des fiches.
            mot_de_passe = generer_mot_de_passe_provisoire() if avec_mot_de_passe else None
            membre.compte = Compte.objects.create_user(
                membre.matricule,
                mot_de_passe,
                nom_affiche=membre.nom_complet,
                doit_changer_mot_de_passe=True,
            )
            membre.save()
            debut = date_integration or datetime.date(annee_integration, 1, 1)
            if paroisse_actuelle == paroisse_integration:
                paroisse_actuelle = None
            jour = max(timezone.localdate(), debut)
            Affectation.objects.create(
                membre=membre,
                paroisse=paroisse_integration,
                circuit_a_date=paroisse_integration.circuit,
                region_a_date=region,
                date_debut=debut,
                date_fin=jour if paroisse_actuelle else None,
                motif="Intégration",
            )
            if paroisse_actuelle:
                Affectation.objects.create(
                    membre=membre,
                    paroisse=paroisse_actuelle,
                    circuit_a_date=paroisse_actuelle.circuit,
                    region_a_date=paroisse_actuelle.circuit.region,
                    date_debut=jour,
                    motif=MOTIF_PAROISSE_ACTUELLE,
                )
            attribuer_grade_initial(
                membre,
                grade=grade,
                date_effet=date_grade or debut,
                par=par,
                regularisation=regularisation,
            )
        from apps.journal.models import ENREGISTREMENT
        from apps.journal.services import journaliser

        details = {"membre": membre.matricule}
        if paroisse_actuelle:
            details["paroisse_actuelle"] = paroisse_actuelle.nom
        journaliser(par, ENREGISTREMENT, **details)
        if notifier:  # les lots envoient une notification groupée à la place
            paroisse_avis = paroisse_actuelle or paroisse_integration
            transaction.on_commit(lambda: _notifier_nouveau_membre(membre, paroisse_avis))
            transaction.on_commit(lambda: _souhaiter_bienvenue(membre))
    except Exception:
        cip = membre.photo_cip
        if cip and getattr(cip, "_committed", False) and cip.name:
            cip.storage.delete(cip.name)  # le fichier a été écrit avant l'annulation
        raise
    return ResultatEnregistrement(membre=membre, mot_de_passe=mot_de_passe)


def _souhaiter_bienvenue(membre: Membre) -> None:
    """Notification (et e-mail s'il en a un) au nouveau membre. JAMAIS le mot de passe."""
    from apps.notifications.services import notifier

    notifier(
        [membre.compte],
        "Bienvenue sur le site de l'Armée du Salut du Bénin. Votre compte est créé : votre "
        f"identifiant est votre matricule {membre.matricule}. Votre paroisse vous remettra votre "
        "fiche avec votre mot de passe provisoire ; vous choisirez votre propre mot de passe à "
        "la première connexion.",
    )


MOTIF_PAROISSE_ACTUELLE = "Paroisse actuelle à l'inscription sur le site"


def _notifier_nouveau_membre(membre: Membre, paroisse: Paroisse | None = None) -> None:
    """Avis aux bureaux de la paroisse actuelle du membre (et de son circuit, de sa région)."""
    from apps.bureaux.perimetre import Unite
    from apps.notifications.services import notifier_unite

    paroisse = paroisse or membre.paroisse_integration
    message = f"Nouveau membre dans votre périmètre : {membre.matricule} — {membre.nom_complet}"
    for unite in (
        Unite("paroisse", paroisse),
        Unite("circuit", paroisse.circuit),
        Unite("region", paroisse.circuit.region),
    ):
        notifier_unite(unite, message)


class CorrectionRefusee(Exception):
    """Correction exceptionnelle impossible ; le message s'affiche tel quel."""


def corriger_integration(*, membre: Membre, annee: int, paroisse: Paroisse, motif: str, par):
    """Correction exceptionnelle par le BN (§3.5) de l'année, de la paroisse et de la région
    d'intégration. Nouveau matricule si l'année ou la région change (l'ancien reste dans
    l'historique). L'affectation d'intégration est corrigée si le membre n'a jamais été muté.
    """
    from apps.journal.models import CORRECTION_INTEGRATION
    from apps.journal.services import journaliser
    from apps.mouvements.models import HistoriqueMembre, TypeHistorique
    from apps.notifications.services import notifier

    motif = (motif or "").strip()
    if not motif:
        raise CorrectionRefusee("Le motif est obligatoire.")
    annee_max = timezone.localdate().year
    if not 1900 <= annee <= annee_max:
        raise CorrectionRefusee(f"L'année d'intégration doit être entre 1900 et {annee_max}.")
    region = paroisse.region
    if annee == membre.annee_integration and paroisse.pk == membre.paroisse_integration_id:
        raise CorrectionRefusee("Aucune modification à enregistrer.")
    avant = {
        "annee": membre.annee_integration,
        "paroisse": membre.paroisse_integration.nom,
        "region": membre.region_integration.code,
        "matricule": membre.matricule,
    }
    with transaction.atomic():
        membre = Membre.objects.select_for_update().get(pk=membre.pk)
        nouveau_matricule = None
        if annee != membre.annee_integration or region.pk != membre.region_integration_id:
            nouveau_matricule = attribuer_matricule(annee, region)
        ancienne_annee = membre.annee_integration
        membre.annee_integration = annee
        membre.paroisse_integration = paroisse
        membre.region_integration = region
        if nouveau_matricule:
            membre.matricule = nouveau_matricule
            if membre.compte_id:
                membre.compte.identifiant = nouveau_matricule
                membre.compte.save(update_fields=["identifiant"])
            HistoriqueMembre.objects.create(
                membre=membre,
                type=TypeHistorique.MATRICULE,
                ancien=avant["matricule"],
                nouveau=nouveau_matricule,
                date_effet=timezone.localdate(),
                motif=f"Correction exceptionnelle : {motif}"[:200],
                par=par,
            )
        membre.save(
            update_fields=[
                "annee_integration",
                "paroisse_integration",
                "region_integration",
                "matricule",
            ]
        )
        affectations = list(membre.affectations.all())
        if len(affectations) == 1 and affectations[0].motif == "Intégration":
            a = affectations[0]
            a.paroisse, a.circuit_a_date, a.region_a_date = paroisse, paroisse.circuit, region
            if a.date_debut == datetime.date(ancienne_annee, 1, 1):
                a.date_debut = datetime.date(annee, 1, 1)
            a.save()
    journaliser(
        par,
        CORRECTION_INTEGRATION,
        membre=membre.matricule,
        motif=motif,
        avant=avant,
        apres={
            "annee": annee,
            "paroisse": paroisse.nom,
            "region": region.code,
            "matricule": membre.matricule,
        },
    )
    if nouveau_matricule:
        notifier(
            [membre.compte],
            f"Votre matricule a été corrigé : {avant['matricule']} → {nouveau_matricule}. "
            "Utilisez le nouveau matricule pour vous connecter.",
        )
    return membre
