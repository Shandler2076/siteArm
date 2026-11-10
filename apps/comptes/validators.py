from django.core.exceptions import ValidationError

from apps.comptes.models import normaliser_identifiant

MESSAGE = "Le mot de passe ne doit pas être votre identifiant."


class DifferentDeLIdentifiantValidator:
    """Refuse un mot de passe identique à l'identifiant (matricule), quelle que soit la casse."""

    def validate(self, password, user=None):
        identifiant = getattr(user, "identifiant", None)
        if identifiant and normaliser_identifiant(password) == identifiant:
            raise ValidationError(MESSAGE, code="mot_de_passe_identifiant")

    def get_help_text(self):
        return MESSAGE
