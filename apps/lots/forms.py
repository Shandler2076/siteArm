from django import forms

from apps.lots.colonnes import COLONNES
from apps.organisation.models import Region


class FormulaireDepot(forms.Form):
    region = forms.ModelChoiceField(
        queryset=Region.objects.filter(active=True).order_by("code"), label="Région"
    )
    fichier = forms.FileField(label="Fichier Excel rempli (.xlsx)")


class FormulaireRedepot(forms.Form):
    fichier = forms.FileField(label="Fichier corrigé (.xlsx)")


class FormulaireLigne(forms.Form):
    """Une case par colonne du modèle, préremplie avec les valeurs lues."""

    def __init__(self, *args, brutes=None, **kwargs):
        super().__init__(*args, **kwargs)
        for i, colonne in enumerate(COLONNES):
            valeur = (brutes or {}).get(colonne.entete)
            self.fields[f"c{i}"] = forms.CharField(
                label=colonne.entete,
                required=False,
                initial="" if valeur is None else _affichage(valeur),
            )

    def brutes(self) -> dict:
        return {c.entete: self.cleaned_data.get(f"c{i}", "") for i, c in enumerate(COLONNES)}


def _affichage(valeur) -> str:
    texte = str(valeur)
    # Date lue comme date Excel (ISO) : on la réaffiche au format JJ/MM/AAAA.
    if len(texte) >= 10 and texte[4] == "-" and texte[7] == "-":
        return f"{texte[8:10]}/{texte[5:7]}/{texte[0:4]}"
    return texte
