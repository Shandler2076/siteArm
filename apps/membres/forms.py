from django import forms

from apps.membres.models import Categorie, Membre
from apps.organisation.models import Paroisse


class ChoixParoisse(forms.ModelChoiceField):
    def label_from_instance(self, p):
        return f"{p.nom} — {p.circuit} — {p.circuit.region.nom}"


class FormulaireEnregistrement(forms.ModelForm):
    paroisse_integration = ChoixParoisse(
        queryset=Paroisse.objects.filter(active=True).select_related("circuit__region"),
        label="Paroisse d'intégration",
    )
    categorie = forms.ChoiceField(
        label="Catégorie", choices=Categorie.choices, initial=Categorie.ACTIF,
        widget=forms.RadioSelect,
    )
    confirmer_malgre_doublon = forms.BooleanField(required=False, widget=forms.HiddenInput)

    class Meta:
        model = Membre
        fields = [
            "nom", "prenoms", "sexe", "date_naissance", "lieu_naissance",
            "situation_matrimoniale", "npi", "photo_cip", "telephone", "whatsapp", "email",
            "quartier", "ville", "profession", "urgence_nom", "urgence_telephone",
            "annee_integration", "paroisse_integration", "categorie",
        ]
        widgets = {"date_naissance": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d")}

    def donnees_membre(self) -> dict:
        exclus = {"annee_integration", "paroisse_integration", "confirmer_malgre_doublon"}
        return {k: v for k, v in self.cleaned_data.items() if k not in exclus and k in self.fields}

    def _post_clean(self):
        # Le matricule et le compte sont créés par le service : on ne valide pas l'instance ici.
        pass
