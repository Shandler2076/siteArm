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
from apps.membres.grades import Grade
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


@dataclass
class Tableau:
    """Tableau croisé : une ligne par grade, une colonne par tranche d'âge, sexe ou unité."""

    titre: str
    colonnes: list[str]
    lignes: list[tuple[str, list[Cellule]]]


# Valeurs d'URL du filtre « grade », dans l'ordre : Camarade, les 12 grades, non renseigné.
GRADES_STAT = [(str(v), str(lib)) for v, lib in Grade.choices] + [("aucun", "Grade non renseigné")]
# Filtres de page acceptés sur la page Statistiques (mêmes clés que la liste).
CLES_BASE = (
    "sexe",
    "categorie",
    "grade",
    "grade_min",
    "eligible",
    "region",
    "circuit",
    "paroisse",
    "sans_affectation",
    "annee",
    "fonction",
    "age",
    "age_x",
    "age_y",
)


def base_depuis_requete(donnees) -> dict:
    """Filtres de page (clés d'URL) d'une requête GET, sans statut ni colonnes."""
    base = {}
    for cle in CLES_BASE:
        valeurs = [v for v in donnees.getlist(cle) if v != ""]
        if valeurs:
            base[cle] = valeurs if cle == "grade" else valeurs[0]
    return base


def _grades(base: dict | None) -> list[tuple[str, str]]:
    """Grades à détailler : ceux du filtre de page « grade » s'il y en a un, sinon tous."""
    choisis = (base or {}).get("grade")
    return [(v, lib) for v, lib in GRADES_STAT if not choisis or v in choisis]


def _fabrique(unite: Unite, statuts: list[str], aujourdhui: datetime.date, base: dict | None):
    def cellule(libelle: str, **filtres) -> Cellule:
        complets = {"envoye": "1", "statut": list(statuts)}
        complets.update(base or {})
        complets.update(filtres)
        donnees = _nettoyer(unite, complets)
        return Cellule(libelle, membres_filtres(unite, donnees, aujourdhui).count(), complets)

    return cellule


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


def _tranches_age(cellule_age) -> list:
    """[(libellé, filtres)] des tranches d'âge, « âge non renseigné » compris."""
    resultat = []
    for t in tranches_depuis_bornes(ReglageStatistiques.courant().liste_bornes):
        filtres = {"age": t.condition, "age_x": str(t.x)}
        if t.y is not None:
            filtres["age_y"] = str(t.y)
        resultat.append((t.libelle, filtres))
    resultat.append(("Âge non renseigné", {"age": "inconnu"}))
    return resultat


def calculer_statistiques(
    unite: Unite, statuts: list[str], aujourdhui: datetime.date, base: dict | None = None
) -> list[Section]:
    """`base` : filtres de page (clés d'URL de la liste) appliqués à tous les chiffres."""
    cellule = _fabrique(unite, statuts, aujourdhui, base)

    sections = [
        Section("Total", [cellule("Total des membres")]),
        Section(
            "Par sexe",
            [cellule("Hommes", sexe=Sexe.MASCULIN), cellule("Femmes", sexe=Sexe.FEMININ)],
        ),
    ]
    ages = [cellule(libelle, **filtres) for libelle, filtres in _tranches_age(cellule)]
    sections.append(Section("Par tranche d'âge", ages))
    sections.append(
        Section("Par catégorie", [cellule(str(lib), categorie=v) for v, lib in Categorie.choices])
    )
    sections.append(Section("Par grade", [cellule(lib, grade=[v]) for v, lib in _grades(base)]))
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


def calculer_tableaux(
    unite: Unite, statuts: list[str], aujourdhui: datetime.date, base: dict | None = None
) -> list[Tableau]:
    """Grade × tranche d'âge, grade × sexe, grade × unité inférieure ; lignes non vides seules.

    Chaque cellule porte ses filtres : son nombre est celui de la liste qu'elle ouvre.
    """
    cellule = _fabrique(unite, statuts, aujourdhui, base)
    grades = []
    for valeur, libelle in _grades(base):
        total = cellule("Total", grade=[valeur])
        if total.nombre:
            grades.append((valeur, libelle, total))
    colonnes_par_tableau = [
        ("Grade × tranche d'âge", _tranches_age(cellule)),
        ("Grade × sexe", [("Hommes", {"sexe": Sexe.MASCULIN}), ("Femmes", {"sexe": Sexe.FEMININ})]),
    ]
    inferieures = _inferieures(unite)
    if inferieures:
        titre, champ, objets = inferieures
        nom = {"region": "région", "circuit": "circuit", "paroisse": "paroisse"}[champ]
        colonnes_par_tableau.append(
            (f"Grade × {nom}", [(libelle, {champ: str(o.pk)}) for libelle, o in objets])
        )
    tableaux = []
    for titre, colonnes in colonnes_par_tableau:
        lignes = []
        for valeur, libelle, total in grades:
            cellules = [cellule(lib, grade=[valeur], **filtres) for lib, filtres in colonnes]
            lignes.append((libelle, [*cellules, total]))
        # Unités inférieures fermées et vides : colonne retirée.
        garder = [
            i
            for i, (lib, _f) in enumerate(colonnes)
            if "(fermée)" not in lib or any(cs[i].nombre for _l, cs in lignes)
        ]
        lignes = [(lib, [cs[i] for i in garder] + [cs[-1]]) for lib, cs in lignes]
        tableaux.append(Tableau(titre, [colonnes[i][0] for i in garder] + ["Total"], lignes))
    return tableaux


def _nettoyer(unite: Unite, filtres: dict) -> dict:
    """Passe les filtres par le formulaire des listes : mêmes règles que la liste ouverte."""
    form = FiltreListeForm(unite, QueryDict(urlencode(filtres, doseq=True)))
    if not form.is_valid():  # ne doit jamais arriver : filtres construits ici
        raise ValueError(f"Filtres de statistiques invalides : {form.errors.as_text()}")
    return form.cleaned_data
