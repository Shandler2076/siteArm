from django import forms

from apps.mouvements.models import Sanction, TypeSanction
from apps.organisation.models import Paroisse


class NouvelleMutationForm(forms.Form):
    matricule = forms.CharField(label="Matricule du membre", max_length=20)
    paroisse_arrivee = forms.ModelChoiceField(
        label="Paroisse d'arrivée",
        queryset=Paroisse.objects.filter(active=True).order_by("nom"),
        required=False,
    )
    motif = forms.CharField(label="Motif (facultatif)", max_length=300, required=False)

    def __init__(self, *args, national: bool = False, **kwargs):
        super().__init__(*args, **kwargs)
        if national:
            self.fields["paroisse_arrivee"].required = True
        else:
            del self.fields["paroisse_arrivee"]


class AvisForm(forms.Form):
    favorable = forms.TypedChoiceField(
        label="Avis",
        choices=[("1", "Favorable"), ("0", "Défavorable")],
        coerce=lambda v: v == "1",
        widget=forms.RadioSelect,
    )
    commentaire = forms.CharField(label="Commentaire", max_length=300, required=False)


class SignalementForm(forms.Form):
    date_effet = forms.DateField(widget=forms.DateInput(attrs={"type": "date"}))
    reference = forms.CharField(max_length=120, required=False)
    nouvelle_categorie = forms.ChoiceField(label="Nouvelle catégorie")
    commentaire = forms.CharField(label="Commentaire (facultatif)", max_length=300, required=False)

    def __init__(self, *args, type_signalement: str, membre, **kwargs):
        from apps.membres.models import Categorie, Statut

        super().__init__(*args, **kwargs)
        f = self.fields
        if type_signalement == "deces":
            f["date_effet"].label = "Date du décès"
            del f["reference"], f["nouvelle_categorie"]
        elif type_signalement == "demission":
            f["date_effet"].label = "Date de la démission"
            f["reference"].label = "Référence de la lettre (facultatif)"
            del f["nouvelle_categorie"]
        elif type_signalement == "rehabilitation":
            f["reference"].label = "Référence de l'engagement écrit de bonne conduite"
            f["reference"].required = membre.statut == Statut.EXCLU
            del f["date_effet"], f["nouvelle_categorie"]
        else:
            f["nouvelle_categorie"].choices = [
                c for c in Categorie.choices if c[0] != membre.categorie
            ]
            del f["date_effet"], f["reference"]


class SanctionForm(forms.Form):
    degre = forms.TypedChoiceField(label="Degré de la faute", choices=Sanction.DEGRES, coerce=int)
    type = forms.ChoiceField(label="Type de sanction", choices=TypeSanction.choices)
    precision = forms.CharField(label="Précision (type « Autre »)", max_length=200, required=False)
    date_debut = forms.DateField(
        label="Date de début", widget=forms.DateInput(attrs={"type": "date"})
    )
    date_fin = forms.DateField(
        label="Date de fin (sanctions temporaires)",
        required=False,
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    motif = forms.CharField(label="Motif résumé", max_length=300)
    reference = forms.CharField(label="Référence de la décision", max_length=120)
