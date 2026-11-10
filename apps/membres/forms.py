import uuid

from django import forms
from django.core.exceptions import ValidationError
from django.forms.models import construct_instance

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

    def clean_photo_cip(self):
        f = self.cleaned_data.get("photo_cip")
        if not f:
            return f
        from apps.membres.images import PhotoInvalide, type_piece_cip

        try:
            extension = type_piece_cip(f)
        except PhotoInvalide as e:
            raise ValidationError(str(e)) from e
        f.name = f"cip-{uuid.uuid4().hex}.{extension}"
        return f

    def _post_clean(self):
        """Valide le futur membre (téléphones, NPI, année, NPI unique) avant tout enregistrement.

        Le matricule et le compte sont créés ensuite par le service : on les exclut ici.
        """
        membre = construct_instance(self, Membre(), fields=[
            f for f in self._meta.fields if f not in ("photo_cip",)
        ])
        paroisse = self.cleaned_data.get("paroisse_integration")
        if paroisse:
            membre.region_integration = paroisse.region
        try:
            membre.full_clean(exclude=[
                "matricule", "compte", "enregistre_par", "photo_cip",
                *[n for n in self._meta.fields if n in self._errors],
            ] + ([] if paroisse else ["paroisse_integration", "region_integration"]))
        except ValidationError as e:
            self._update_errors(e)


class FormulaireCoordonnees(forms.ModelForm):
    class Meta:
        model = Membre
        fields = [
            "telephone", "whatsapp", "email", "quartier", "ville", "profession",
            "urgence_nom", "urgence_telephone",
        ]


class FormulairePhoto(forms.Form):
    fichier = forms.FileField(
        label="Photo en tenue",
        help_text="JPEG ou PNG, 5 Mo au plus, au moins 300 × 300 pixels.",
        widget=forms.ClearableFileInput(attrs={"accept": "image/jpeg,image/png"}),
    )

    def clean_fichier(self):
        from apps.membres.images import PhotoInvalide, verifier_et_preparer_photo

        try:
            return verifier_et_preparer_photo(self.cleaned_data["fichier"])
        except PhotoInvalide as e:
            raise forms.ValidationError(str(e)) from e
