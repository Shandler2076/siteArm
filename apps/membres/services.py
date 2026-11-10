"""Services métier des membres : matricule, enregistrement, doublons."""

from django.db import IntegrityError, transaction

from apps.membres.models import CompteurMatricule
from apps.organisation.models import Region

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
