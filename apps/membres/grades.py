"""Les grades de l'Armée du Salut (RI art. 77 à 87) ; « Camarade » à l'entrée (décision du BNC).

La valeur d'un grade est son rang : 0 Camarade, puis 1 (Soldat de 3ᵉ classe) à 12.
"""

import re

from django.db import models


class Grade(models.IntegerChoices):
    CAMARADE = 0, "Camarade"
    SOLDAT_3 = 1, "Soldat de 3ᵉ classe"
    SOLDAT_2 = 2, "Soldat de 2ᵉ classe"
    SOLDAT_1 = 3, "Soldat de 1ʳᵉ classe"
    SOUS_CAPITAINE = 4, "Sous-Capitaine"
    CAPITAINE = 5, "Capitaine"
    SENIOR_CAPITAINE = 6, "Senior Capitaine"
    COMMANDANT = 7, "Commandant"
    SOUS_SUPERIEUR = 8, "Sous-Supérieur"
    SUPERIEUR_DELEGUE = 9, "Supérieur Délégué"
    SUPERIEUR_GENERAL_DELEGUE = 10, "Supérieur Général Délégué"
    SUPERIEUR_GENERAL = 11, "Supérieur Général"
    SUPREME = 12, "Supérieur Suprême Spirituel"


# Durée minimale (en années) dans un grade avant le grade suivant (art. 78).
DUREES_MINIMALES = {1: 3, 2: 3, 3: 3, 4: 4, 5: 5}
# Premier grade attribué exclusivement par nomination (art. 78 et 79).
PAR_NOMINATION = Grade.COMMANDANT


def _forme(texte: str) -> str:
    from apps.membres.models import cle_nom

    t = (texte or "").replace("ᵉ", "e").replace("ʳ", "r")
    t = cle_nom(t)
    t = re.sub(r"\b(\d)\s*(?:EME|IEME|ERE|IERE|RE|E)\b", r"\1E", t)
    return t


def _formes() -> dict[str, int]:
    formes = {}
    for g in Grade:
        forme = _forme(g.label)
        formes[forme] = g.value
        if forme.startswith("SOLDAT DE "):
            formes[forme.removeprefix("SOLDAT DE ")] = g.value
    return formes


def grade_depuis_texte(texte: str | None) -> Grade | None:
    """Reconnaît un grade écrit librement (« capitaine », « 3e classe », « Sous capitaine »…)."""
    if not texte or not texte.strip():
        return None
    valeur = _formes().get(_forme(texte))
    return Grade(valeur) if valeur is not None else None
