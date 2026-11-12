from django import forms
from django.utils import timezone

_DATE = forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d")


class _ChoixMembre(forms.ModelChoiceField):
    def label_from_instance(self, m):
        return f"{m.nom_complet} — {m.matricule}"


class VersementForm(forms.Form):
    membre = _ChoixMembre(queryset=None, label="Membre")
    montant = forms.IntegerField(label="Montant versé (F CFA)", min_value=1)
    date_versement = forms.DateField(label="Date du versement", widget=_DATE)

    def __init__(self, *args, membres=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["membre"].queryset = membres
        self.fields["date_versement"].initial = timezone.localdate()


class AnnulationForm(forms.Form):
    motif = forms.CharField(label="Motif de l'annulation", max_length=300)
