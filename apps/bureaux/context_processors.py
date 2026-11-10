from django.utils.functional import SimpleLazyObject

from apps.bureaux.perimetre import est_bn, unites_gerees


def bureaux(request):
    user = getattr(request, "user", None)
    if user is None or not user.is_authenticated:
        return {}
    return {
        "mes_unites": SimpleLazyObject(lambda: unites_gerees(user)),
        "est_bn": SimpleLazyObject(lambda: user.has_perm("membres.gerer_membres")),
        # Espace national du gardien des périmètres (mandat national ou superutilisateur).
        "espace_national": SimpleLazyObject(lambda: est_bn(user)),
    }
