"""Lecture du fichier Excel déposé : contrôle de forme, lignes non vides."""

import zipfile

from openpyxl import load_workbook
from openpyxl.utils import get_column_letter
from openpyxl.utils.exceptions import InvalidFileException

from apps.lots.colonnes import COLONNES

TAILLE_MAX = 5 * 1024 * 1024
LIGNES_MAX = 2000
# Garde-fous contre un fichier piégé (« bombe zip ») : taille une fois décompressé, et nombre
# de lignes parcourues (lignes vides comprises).
DECOMPRESSE_MAX = 50 * 1024 * 1024
LIGNES_LUES_MAX = 10 * LIGNES_MAX


class FichierInvalide(ValueError):
    pass


def _vide(valeur) -> bool:
    return valeur is None or (isinstance(valeur, str) and not valeur.strip())


def _verifier_decompression(fichier) -> None:
    try:
        fichier.seek(0)
        with zipfile.ZipFile(fichier) as z:
            total = sum(info.file_size for info in z.infolist())
    except (zipfile.BadZipFile, OSError):
        return  # la lecture ci-dessous dira que ce n'est pas un classeur Excel
    finally:
        fichier.seek(0)
    if total > DECOMPRESSE_MAX:
        raise FichierInvalide(
            "Ce fichier est trop volumineux une fois ouvert. Utilisez le modèle officiel."
        )


def lire_classeur(fichier) -> list[tuple[int, dict[str, object]]]:
    if getattr(fichier, "size", 0) > TAILLE_MAX:
        raise FichierInvalide("Le fichier dépasse 5 Mo. Découpez-le en plusieurs lots.")
    _verifier_decompression(fichier)
    try:
        fichier.seek(0)
        wb = load_workbook(fichier, read_only=True, data_only=True)
    except (zipfile.BadZipFile, InvalidFileException, KeyError, OSError, ValueError) as e:
        raise FichierInvalide(
            "Ce fichier n'est pas un classeur Excel (.xlsx). Utilisez le modèle officiel."
        ) from e
    if "Membres" not in wb.sheetnames:
        wb.close()
        raise FichierInvalide(
            "La feuille « Membres » est introuvable. Utilisez le modèle officiel."
        )
    ws = wb["Membres"]
    if (ws.max_row or 0) > LIGNES_LUES_MAX:
        wb.close()
        raise FichierInvalide(
            "La feuille « Membres » est trop longue (lignes vides comprises) : supprimez les "
            "lignes inutiles sous le tableau, ou découpez le fichier en plusieurs lots."
        )
    lignes = ws.iter_rows(values_only=True, max_row=LIGNES_LUES_MAX, max_col=len(COLONNES))
    entetes = list(next(lignes, ()) or ())
    for i, colonne in enumerate(COLONNES):
        lue = entetes[i] if i < len(entetes) else None
        lue = str(lue).strip() if lue is not None else ""
        if lue != colonne.entete and not (colonne.entete_facultative and not lue):
            wb.close()
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
