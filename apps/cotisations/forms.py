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


class DepartForm(forms.Form):
    mois_depart = forms.DateField(
        label="Premier mois suivi (mise en service)",
        widget=_DATE,
        help_text="Le jour est ignoré : seul le mois compte.",
    )


class TarifForm(forms.Form):
    date_effet = forms.DateField(label="À compter du mois", widget=_DATE)
    montant = forms.IntegerField(label="Montant mensuel (F CFA)", min_value=1)
    part_paroisse = forms.IntegerField(label="Part de la paroisse (%)", min_value=0, max_value=100)
    part_circuit = forms.IntegerField(label="Part du circuit (%)", min_value=0, max_value=100)
    part_region = forms.IntegerField(label="Part de la région (%)", min_value=0, max_value=100)
    part_national = forms.IntegerField(label="Part du national (%)", min_value=0, max_value=100)
