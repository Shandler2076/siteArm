from django import forms

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
