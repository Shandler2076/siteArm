"""Statistiques d'une unité : chaque chiffre est le nombre de lignes de la liste qu'il ouvre.

Chaque `Cellule` porte les filtres (clés d'URL du formulaire des listes) qui la définissent,
et son nombre est calculé par `membres_filtres` avec exactement ces filtres.
"""

import datetime
from dataclasses import dataclass, field
from urllib.parse import urlencode

from django.http import QueryDict

from apps.bureaux.models import Niveau
from apps.bureaux.perimetre import Unite
from apps.listes.ages import tranches_depuis_bornes
from apps.listes.filtres import FiltreListeForm, membres_filtres
from apps.listes.models import ReglageStatistiques
from apps.membres.models import Categorie, Sexe, Statut
from apps.organisation.models import Circuit, Paroisse, Region


@dataclass
class Cellule:
    libelle: str
    nombre: int
    filtres: dict = field(default_factory=dict)


@dataclass
class Section:
    titre: str
    cellules: list[Cellule]


def _nom(objet) -> str:
    return objet.nom if objet.active else f"{objet.nom} (fermée)"


def _inferieures(unite: Unite):
    """(titre, champ de filtre, [(libellé, objet)]) des unités inférieures, ou None."""
    if unite.niveau == Niveau.NATIONAL:
        regions = Region.objects.order_by("code")
        return "Par région", "region", [(f"{r.code} — {_nom(r)}", r) for r in regions]
    if unite.niveau == Niveau.REGION:
        circuits = Circuit.objects.filter(region=unite.objet).order_by("nom")
        return "Par circuit", "circuit", [(_nom(c), c) for c in circuits]
    if unite.niveau == Niveau.CIRCUIT:
        paroisses = Paroisse.objects.filter(circuit=unite.objet).order_by("nom")
        return "Par paroisse", "paroisse", [(_nom(p), p) for p in paroisses]
    return None


def calculer_statistiques(
    unite: Unite, statuts: list[str], aujourdhui: datetime.date
) -> list[Section]:
    def cellule(libelle: str, **filtres) -> Cellule:
        complets = {"envoye": "1", "statut": list(statuts)}
        complets.update(filtres)
        donnees = _nettoyer(unite, complets)
        return Cellule(libelle, membres_filtres(unite, donnees, aujourdhui).count(), complets)

    sections = [
        Section("Total", [cellule("Total des membres")]),
        Section(
            "Par sexe",
            [cellule("Hommes", sexe=Sexe.MASCULIN), cellule("Femmes", sexe=Sexe.FEMININ)],
        ),
    ]
    tranches = tranches_depuis_bornes(ReglageStatistiques.courant().liste_bornes)
    ages = []
    for t in tranches:
        filtres = {"age": t.condition, "age_x": str(t.x)}
        if t.y is not None:
            filtres["age_y"] = str(t.y)
        ages.append(cellule(t.libelle, **filtres))
    ages.append(cellule("Âge non renseigné", age="inconnu"))
    sections.append(Section("Par tranche d'âge", ages))
    sections.append(
        Section("Par catégorie", [cellule(str(lib), categorie=v) for v, lib in Categorie.choices])
    )
    sections.append(
        Section("Par statut", [cellule(str(lib), statut=[v]) for v, lib in Statut.choices])
    )
    inferieures = _inferieures(unite)
    if inferieures:
        titre, champ, objets = inferieures
        cellules = []
        for libelle, objet in objets:
            c = cellule(libelle, **{champ: str(objet.pk)})
            if objet.active or c.nombre:
                cellules.append(c)
        if unite.niveau == Niveau.NATIONAL:
            c = cellule("Sans affectation", sans_affectation="1")
            if c.nombre:
                cellules.append(c)
        sections.append(Section(titre, cellules))
    return sections


def _nettoyer(unite: Unite, filtres: dict) -> dict:
    """Passe les filtres par le formulaire des listes : mêmes règles que la liste ouverte."""
    form = FiltreListeForm(unite, QueryDict(urlencode(filtres, doseq=True)))
    if not form.is_valid():  # ne doit jamais arriver : filtres construits ici
        raise ValueError(f"Filtres de statistiques invalides : {form.errors.as_text()}")
    return form.cleaned_data
