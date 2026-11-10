"""Services métier des membres : matricule, enregistrement, doublons."""

import datetime
import secrets
from dataclasses import dataclass

from django.db import IntegrityError, transaction
from django.db.models import Q, QuerySet

from apps.comptes.models import Compte
from apps.membres.models import Affectation, CompteurMatricule, Membre, cle_nom
from apps.organisation.models import Paroisse, Region

__all__ = [
    "CapaciteMatriculeAtteinte", "ResultatEnregistrement", "attribuer_matricule", "cle_nom",
    "doublons_possibles", "enregistrer_membre", "generer_mot_de_passe_provisoire",
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
    date_integration: datetime.date | None = None,
) -> ResultatEnregistrement:
    """Crée en une seule transaction : matricule, compte, membre et première affectation.

    En cas d'échec, rien n'est créé, y compris le fichier de la photo du CIP éventuelle.
    """
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
            mot_de_passe = generer_mot_de_passe_provisoire()
            membre.compte = Compte.objects.create_user(
                membre.matricule, mot_de_passe, nom_affiche=membre.nom_complet,
                doit_changer_mot_de_passe=True,
            )
            membre.save()
            Affectation.objects.create(
                membre=membre,
                paroisse=paroisse_integration,
                circuit_a_date=paroisse_integration.circuit,
                region_a_date=region,
                date_debut=date_integration or datetime.date(annee_integration, 1, 1),
                motif="Intégration",
            )
    except Exception:
        cip = membre.photo_cip
        if cip and getattr(cip, "_committed", False) and cip.name:
            cip.storage.delete(cip.name)  # le fichier a été écrit avant l'annulation
        raise
    return ResultatEnregistrement(membre=membre, mot_de_passe=mot_de_passe)
