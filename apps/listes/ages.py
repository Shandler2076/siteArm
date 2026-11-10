"""Âge calculé en base, au jour près, à partir de la date de naissance.

« moins de X ans » : âge < X ; « plus de Y ans » : âge > Y ; « entre X et Y ans » : bornes incluses.
Les membres sans date de naissance ne sont retenus que par la condition « inconnu ».
"""

import datetime
from dataclasses import dataclass

from django.db.models import QuerySet

from apps.bureaux.models import _ajouter_annees

CONDITIONS = ("moins", "plus", "entre", "inconnu")


def date_limite(aujourdhui: datetime.date, annees: int) -> datetime.date:
    """Date de naissance la plus récente pour avoir au moins `annees` ans à `aujourdhui`."""
    return _ajouter_annees(aujourdhui, -annees)


def filtrer_age(
    qs: QuerySet, condition: str, x: int | None, y: int | None, aujourdhui: datetime.date
) -> QuerySet:
    if condition == "inconnu":
        return qs.filter(date_naissance__isnull=True)
    if condition == "moins":
        return qs.filter(date_naissance__gt=date_limite(aujourdhui, x))
    if condition == "plus":
        return qs.filter(date_naissance__lte=date_limite(aujourdhui, x + 1))
    if condition == "entre":
        return qs.filter(
            date_naissance__gt=date_limite(aujourdhui, y + 1),
            date_naissance__lte=date_limite(aujourdhui, x),
        )
    raise ValueError(f"Condition d'âge inconnue : {condition}")


@dataclass(frozen=True)
class Tranche:
    libelle: str
    condition: str
    x: int
    y: int | None = None


def tranches_depuis_bornes(bornes: list[int]) -> list[Tranche]:
    """[18, 40] → moins de 18 ; 18 à 40 ; plus de 40. [18, 40, 60] ajoute 41 à 60."""
    tranches = [Tranche(f"Moins de {bornes[0]} ans", "moins", bornes[0])]
    debut = bornes[0]
    for borne in bornes[1:]:
        tranches.append(Tranche(f"{debut} à {borne} ans", "entre", debut, borne))
        debut = borne + 1
    tranches.append(Tranche(f"Plus de {bornes[-1]} ans", "plus", bornes[-1]))
    return tranches
