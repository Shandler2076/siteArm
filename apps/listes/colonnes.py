"""Colonnes possibles d'une liste de membres (jamais le NPI ni la photo du CIP)."""

import datetime
from collections.abc import Iterator

from django.db.models import OuterRef, Prefetch, QuerySet, Subquery

from apps.bureaux.models import Mandat
from apps.membres.models import Affectation

# clé → (titre, largeur dans le PDF en mm)
COLONNES_LISTE: dict[str, tuple[str, float]] = {
    "matricule": ("Matricule", 28),
    "nom": ("Nom", 32),
    "prenoms": ("Prénoms", 40),
    "sexe": ("Sexe", 10),
    "age": ("Âge", 10),
    "telephone": ("Téléphone", 24),
    "whatsapp": ("WhatsApp", 24),
    "paroisse": ("Paroisse", 36),
    "circuit": ("Circuit", 30),
    "categorie": ("Catégorie", 28),
    "statut": ("Statut", 22),
    "fonctions": ("Fonction(s)", 45),
}
COLONNES_PAR_DEFAUT = ["matricule", "nom", "prenoms", "sexe", "age", "telephone", "paroisse"]


def preparer(qs: QuerySet, aujourdhui: datetime.date) -> QuerySet:
    """Ajoute paroisse et circuit actuels et les mandats en cours, sans requête par membre."""
    ouverte = Affectation.objects.filter(membre=OuterRef("pk"), date_fin__isnull=True)
    return qs.annotate(
        paroisse_actuelle=Subquery(ouverte.values("paroisse__nom")[:1]),
        circuit_actuel=Subquery(ouverte.values("paroisse__circuit__nom")[:1]),
    ).prefetch_related(
        Prefetch(
            "mandats",
            queryset=Mandat.objects.en_cours(aujourdhui).select_related("fonction"),
            to_attr="mandats_en_cours",
        )
    )


def _valeur(m, cle: str, aujourdhui: datetime.date):
    if cle == "age":
        return m.age(aujourdhui)
    if cle == "paroisse":
        return m.paroisse_actuelle
    if cle == "circuit":
        return m.circuit_actuel
    if cle == "categorie":
        return m.get_categorie_display()
    if cle == "statut":
        return m.get_statut_display()
    if cle == "fonctions":
        return ", ".join(x.fonction.nom for x in m.mandats_en_cours)
    return getattr(m, cle)


def lignes(qs: QuerySet, colonnes: list[str], aujourdhui: datetime.date) -> Iterator[list]:
    for m in qs:
        yield [_valeur(m, c, aujourdhui) for c in colonnes]
