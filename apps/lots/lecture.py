"""Lecture du fichier Excel déposé : contrôle de forme, lignes non vides."""

import zipfile

from openpyxl import load_workbook
from openpyxl.utils import get_column_letter
from openpyxl.utils.exceptions import InvalidFileException

from apps.lots.colonnes import COLONNES

TAILLE_MAX = 5 * 1024 * 1024
LIGNES_MAX = 2000


class FichierInvalide(ValueError):
    pass


def _vide(valeur) -> bool:
    return valeur is None or (isinstance(valeur, str) and not valeur.strip())


def lire_classeur(fichier) -> list[tuple[int, dict[str, object]]]:
    if getattr(fichier, "size", 0) > TAILLE_MAX:
        raise FichierInvalide("Le fichier dépasse 5 Mo. Découpez-le en plusieurs lots.")
    try:
        fichier.seek(0)
        wb = load_workbook(fichier, read_only=True, data_only=True)
    except (zipfile.BadZipFile, InvalidFileException, KeyError, OSError, ValueError) as e:
        raise FichierInvalide(
            "Ce fichier n'est pas un classeur Excel (.xlsx). Utilisez le modèle officiel."
        ) from e
    if "Membres" not in wb.sheetnames:
        raise FichierInvalide(
            "La feuille « Membres » est introuvable. Utilisez le modèle officiel."
        )
    ws = wb["Membres"]
    lignes = ws.iter_rows(values_only=True)
    entetes = list(next(lignes, ()) or ())
    for i, colonne in enumerate(COLONNES):
        lue = entetes[i] if i < len(entetes) else None
        if (str(lue).strip() if lue is not None else "") != colonne.entete:
            raise FichierInvalide(
                "Les colonnes ne correspondent pas au modèle officiel : "
                f"colonne {get_column_letter(i + 1)} attendue « {colonne.entete} »."
            )
    resultat = []
    for numero, valeurs in enumerate(lignes, start=2):
        valeurs = list(valeurs)[: len(COLONNES)]
        if all(_vide(v) for v in valeurs):
            continue
        valeurs += [None] * (len(COLONNES) - len(valeurs))
        resultat.append((numero, {c.entete: v for c, v in zip(COLONNES, valeurs, strict=True)}))
        if len(resultat) > LIGNES_MAX:
            maxi = f"{LIGNES_MAX:,}".replace(",", " ")
            raise FichierInvalide(
                f"Le fichier contient trop de lignes : {maxi} lignes au plus par lot."
            )
    wb.close()
    return resultat
