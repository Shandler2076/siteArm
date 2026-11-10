from apps.bureaux.perimetre import est_bn, unites_gerees

DUREE_SESSION_BUREAU = 30 * 60


class DureeSessionBureau:
    """Déconnexion après 30 minutes d'inactivité pour les comptes qui gèrent une unité."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, "user", None)
        if user is not None and user.is_authenticated and (est_bn(user) or unites_gerees(user)):
            request.session.set_expiry(DUREE_SESSION_BUREAU)
        return self.get_response(request)
