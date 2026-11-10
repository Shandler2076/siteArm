from django import forms
from django.contrib.auth.forms import AuthenticationForm

from apps.comptes.models import normaliser_identifiant


class FormulaireConnexion(AuthenticationForm):
    username = forms.CharField(
        label="Identifiant (matricule)",
        max_length=40,
        widget=forms.TextInput(
            attrs={"autofocus": True, "autocapitalize": "characters", "autocomplete": "username"}
        ),
    )
    password = forms.CharField(
        label="Mot de passe",
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "current-password"}),
    )
    error_messages = {
        "invalid_login": "Identifiant ou mot de passe incorrect.",
        "inactive": "Ce compte est désactivé.",
    }

    def clean_username(self):
        return normaliser_identifiant(self.cleaned_data["username"])
