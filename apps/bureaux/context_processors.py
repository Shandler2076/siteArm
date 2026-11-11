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
        "nb_decisions": SimpleLazyObject(lambda: _nb_decisions(user)),
    }


def _nb_decisions(user) -> int:
    from apps.mouvements.models import EN_COURS, EtatDemande, Mutation, Signalement

    if not user.has_perm("membres.gerer_membres"):
        return 0
    return (
        Mutation.objects.filter(etat__in=EN_COURS).count()
        + Signalement.objects.filter(etat=EtatDemande.BN).count()
    )
