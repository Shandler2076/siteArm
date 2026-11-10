from django.contrib.auth.backends import ModelBackend

from apps.comptes.models import normaliser_identifiant


class IdentifiantNormaliseBackend(ModelBackend):
    """Connexion insensible aux espaces et à la casse, sur toutes les pages de connexion."""

    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is not None:
            username = normaliser_identifiant(username)
        return super().authenticate(request, username=username, password=password, **kwargs)
