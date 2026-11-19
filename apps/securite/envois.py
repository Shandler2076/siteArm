"""Refus précoce des envois démesurés (faille M4 de l'analyse du 19/11/2026)."""

from django.conf import settings
from django.http import HttpResponse

MESSAGE = (
    "<!doctype html><meta charset='utf-8'><title>Envoi trop volumineux</title>"
    "<p>Envoi trop volumineux : les fichiers ne doivent pas dépasser la taille indiquée sur la "
    "page. Revenez à la page précédente et envoyez un fichier plus petit.</p>"
)


class TailleDesEnvois:
    """Refuse une requête dont la taille annoncée dépasse TAILLE_MAX_ENVOI, avant de la lire."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        try:
            taille = int(request.META.get("CONTENT_LENGTH") or 0)
        except ValueError:
            taille = 0
        if taille > settings.TAILLE_MAX_ENVOI:
            return HttpResponse(MESSAGE, status=413)
        return self.get_response(request)


PERMISSIONS_POLICY = "camera=(), microphone=(), geolocation=(), payment=(), usb=()"


def politique_contenus(jeton: str) -> str:
    """CSP : seul le JavaScript du site (fichiers de /static/ et scripts marqués du jeton de la
    page) s'exécute. Les styles écrits dans les pages restent permis (risque faible)."""
    return "; ".join(
        [
            "default-src 'self'",
            f"script-src 'self' 'nonce-{jeton}'",
            "style-src 'self' 'unsafe-inline'",
            "img-src 'self' data: blob:",
            "font-src 'self'",
            "connect-src 'self'",
            "object-src 'none'",
            "base-uri 'self'",
            "form-action 'self'",
            "frame-ancestors 'none'",
        ]
    )


class EntetesDeSecurite:
    """En-têtes ajoutés à chaque réponse : le site n'utilise ni caméra, ni micro, ni position, ni
    paiement par le navigateur (le paiement mobile money passe par la plateforme)."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        import secrets

        request.csp_nonce = secrets.token_urlsafe(18)
        reponse = self.get_response(request)
        reponse.headers.setdefault("Permissions-Policy", PERMISSIONS_POLICY)
        reponse.headers.setdefault("Content-Security-Policy", politique_contenus(request.csp_nonce))
        return reponse
