from django.shortcuts import redirect
from django.urls import reverse

from apps.securite.services import doit_verifier, double_verification_active, est_verifie

LIBRES = ("/securite/", "/deconnexion/", "/connexion/", "/mot-de-passe/changer/", "/static/")


class DoubleVerificationObligatoire:
    """Aucune page n'est servie à un compte du BN tant que son code n'est pas vérifié."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if (
            not request.path.startswith(LIBRES)
            and doit_verifier(request.user)
            and not est_verifie(request)
        ):
            page = (
                "securite:code" if double_verification_active(request.user) else "securite:activer"
            )
            return redirect(f"{reverse(page)}?suivant={request.get_full_path()}")
        return self.get_response(request)
