from django.utils.functional import SimpleLazyObject

from apps.bureaux.perimetre import unites_gerees


def bureaux(request):
    user = getattr(request, "user", None)
    if user is None or not user.is_authenticated:
        return {}
    return {
        "mes_unites": SimpleLazyObject(lambda: unites_gerees(user)),
        "est_bn": SimpleLazyObject(lambda: user.has_perm("membres.gerer_membres")),
    }
