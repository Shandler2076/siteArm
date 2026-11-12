import uuid

from django import forms
from django.core.exceptions import ValidationError

from apps.membres.grades import Grade
from apps.membres.models import Categorie, Membre
from apps.organisation.models import Paroisse


def valider_futur_membre(
    donnees: dict, paroisse, exclure=(), verifier_contraintes: bool = True
) -> dict[str, list[str]]:
    """Règles du modèle `Membre` appliquées à un membre pas encore enregistré.

    Utilisé par l'enregistrement individuel et par les lots : une seule source de vérité.
    """
    membre = Membre(**donnees)
    if paroisse is not None:
        membre.paroisse_integration = paroisse
        membre.region_integration = paroisse.region
    ignores = ["matricule", "compte", "enregistre_par", "photo_cip", *exclure]
    if paroisse is None:
        ignores += ["paroisse_integration", "region_integration"]
    try:
        membre.full_clean(exclude=ignores, validate_constraints=verifier_contraintes)
    except ValidationError as e:
        return e.message_dict
    return {}


class ChoixParoisse(forms.ModelChoiceField):
    def label_from_instance(self, p):
        return f"{p.nom} — {p.circuit} — {p.circuit.region.nom}"


class FormulaireEnregistrement(forms.ModelForm):
    paroisse_integration = ChoixParoisse(
        queryset=Paroisse.objects.filter(active=True).select_related("circuit__region"),
        label="Paroisse d'intégration",
    )
    categorie = forms.ChoiceField(
        label="Catégorie",
        choices=Categorie.choices,
        initial=Categorie.ACTIF,
        widget=forms.RadioSelect,
    )
    grade = forms.TypedChoiceField(
        label="Grade",
        choices=Grade.choices,
        coerce=int,
        required=False,
        empty_value=Grade.CAMARADE,
        initial=Grade.CAMARADE,
        help_text="Camarade pour un nouveau membre ; le grade actuel pour un membre déjà gradé.",
    )
    date_grade = forms.DateField(
        label="Grade obtenu le",
        required=False,
        widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
        help_text="Pour un membre déjà gradé. Vide : date d'intégration.",
    )
    confirmer_malgre_doublon = forms.BooleanField(required=False, widget=forms.HiddenInput)

    class Meta:
        model = Membre
        fields = [
            "nom",
            "prenoms",
            "sexe",
            "date_naissance",
            "lieu_naissance",
            "situation_matrimoniale",
            "npi",
            "photo_cip",
            "telephone",
            "whatsapp",
            "email",
            "quartier",
            "ville",
            "profession",
            "urgence_nom",
            "urgence_telephone",
            "annee_integration",
            "paroisse_integration",
            "categorie",
        ]
        widgets = {"date_naissance": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d")}

    def donnees_membre(self) -> dict:
        exclus = {
            "annee_integration",
            "paroisse_integration",
            "confirmer_malgre_doublon",
            "grade",
            "date_grade",
        }
        return {k: v for k, v in self.cleaned_data.items() if k not in exclus and k in self.fields}

    def parametres_grade(self) -> dict:
        """Paramètres de grade pour `enregistrer_membre`."""
        grade = self.cleaned_data["grade"]
        return {
            "grade": grade,
            "date_grade": self.cleaned_data.get("date_grade"),
            "regularisation": grade != Grade.CAMARADE,
        }

    def clean(self):
        from apps.grades.services import erreurs_grade_initial

        donnees = super().clean()
        date_grade, annee = donnees.get("date_grade"), donnees.get("annee_integration")
        if date_grade and annee:
            for message in erreurs_grade_initial(date_grade, annee, donnees.get("date_naissance")):
                self.add_error("date_grade", message[0].upper() + message[1:])
        return donnees

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
        """Valide le futur membre (téléphones, NPI, année, NPI unique) avant tout enregistrement."""
        champs_membre = [f for f in self._meta.fields if f not in ("photo_cip",)]
        donnees = {
            f: self.cleaned_data[f]
            for f in champs_membre
            if f in self.cleaned_data and f != "paroisse_integration"
        }
        erreurs = valider_futur_membre(
            donnees,
            self.cleaned_data.get("paroisse_integration"),
            exclure=[f for f in champs_membre if f in self._errors],
        )
        if erreurs:
            self._update_errors(ValidationError(erreurs))


class FormulaireCoordonnees(forms.ModelForm):
    class Meta:
        model = Membre
        fields = [
            "telephone",
            "whatsapp",
            "email",
            "quartier",
            "ville",
            "profession",
            "urgence_nom",
            "urgence_telephone",
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
