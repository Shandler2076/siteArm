"""Modèle Excel officiel d'une région : colonnes fixes, listes déroulantes, consignes."""

import io

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

from apps.lots.colonnes import COLONNES, PAR_CHAMP
from apps.membres.models import Categorie, SituationMatrimoniale
from apps.organisation.models import Paroisse, Region

NB_LIGNES = 2000
MARINE, ROUGE = "14284B", "8E0E24"

CONSIGNES = [
    "Modèle officiel d'enregistrement des membres — Armée du Salut du Bénin",
    "",
    "1. Une ligne par membre, à partir de la ligne 2 de la feuille « Membres ».",
    "2. Ne modifiez pas, ne déplacez pas et ne supprimez pas les en-têtes de la ligne 1.",
    "3. Les colonnes marquées d'un astérisque (*) sont obligatoires.",
    "4. Dates au format JJ/MM/AAAA (exemple : 01/05/1990).",
    "5. Sexe : M ou F. Situation, paroisse et catégorie : choisissez dans la liste proposée.",
    "6. Paroisse d'intégration : uniquement une paroisse de votre région.",
    "7. Catégorie laissée vide = membre actif.",
    "8. NPI : 10 chiffres, facultatif. Téléphone : chiffres, espaces et + uniquement.",
    "9. Envoyez le fichier rempli au Secrétaire national, qui le déposera sur le site.",
]


def _liste(ws, colonne: int, valeurs: list[str]) -> str:
    for i, v in enumerate(valeurs, start=1):
        ws.cell(row=i, column=colonne, value=v)
    lettre = get_column_letter(colonne)
    return f"=Listes!${lettre}$1:${lettre}${max(len(valeurs), 1)}"


def _validation(ws, champ: str, formule: str) -> None:
    lettre = get_column_letter(COLONNES.index(PAR_CHAMP[champ]) + 1)
    dv = DataValidation(type="list", formula1=formule, allow_blank=True)
    dv.error = "Choisissez une valeur dans la liste."
    dv.errorTitle = "Valeur non prévue"
    ws.add_data_validation(dv)
    dv.add(f"{lettre}2:{lettre}{NB_LIGNES + 1}")


def modele_pour_region(region: Region) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = "Membres"
    ws.append([c.entete for c in COLONNES])
    for i, c in enumerate(COLONNES, start=1):
        cell = ws.cell(row=1, column=i)
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor=ROUGE if c.obligatoire else MARINE)
        cell.alignment = Alignment(wrap_text=True, vertical="center")
        ws.column_dimensions[get_column_letter(i)].width = max(14, len(c.entete) + 4)
    ws.row_dimensions[1].height = 32
    ws.freeze_panes = "A2"
    date = get_column_letter(COLONNES.index(PAR_CHAMP["date_naissance"]) + 1)
    for ligne in range(2, NB_LIGNES + 2):
        ws[f"{date}{ligne}"].number_format = "DD/MM/YYYY"

    listes = wb.create_sheet("Listes")
    paroisses = list(
        Paroisse.objects.filter(circuit__region=region, active=True)
        .order_by("nom")
        .values_list("nom", flat=True)
    )
    _validation(ws, "paroisse_integration", _liste(listes, 1, paroisses))
    _validation(ws, "categorie", _liste(listes, 2, [lib for _, lib in Categorie.choices]))
    situations = [lib for _, lib in SituationMatrimoniale.choices]
    _validation(ws, "situation_matrimoniale", _liste(listes, 3, situations))
    _validation(ws, "sexe", '"M,F"')
    listes.sheet_state = "hidden"

    consignes = wb.create_sheet("Consignes")
    consignes.column_dimensions["A"].width = 100
    for texte in [*CONSIGNES, "", f"Région : {region.code} — {region.nom}"]:
        consignes.append([texte])
    consignes["A1"].font = Font(bold=True, size=13, color=MARINE)

    tampon = io.BytesIO()
    wb.save(tampon)
    return tampon.getvalue()
