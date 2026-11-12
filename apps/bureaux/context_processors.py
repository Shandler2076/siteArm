from django.utils.functional import SimpleLazyObject

from apps.bureaux.perimetre import est_bn, unites_cotisations, unites_gerees


def bureaux(request):
    user = getattr(request, "user", None)
    if user is None or not user.is_authenticated:
        return {}
    return {
        "mes_unites": SimpleLazyObject(lambda: unites_gerees(user)),
        "mes_unites_cotisations": SimpleLazyObject(lambda: unites_cotisations(user)),
        "est_bn": SimpleLazyObject(lambda: user.has_perm("membres.gerer_membres")),
        # Espace national du gardien des périmètres (mandat national ou superutilisateur).
        "espace_national": SimpleLazyObject(lambda: est_bn(user)),
        "nb_decisions": SimpleLazyObject(lambda: _nb_decisions(user)),
        "mes_fonctions": SimpleLazyObject(lambda: _fonctions(user)),
    }


def _nb_decisions(user) -> int:
    from apps.mouvements.models import EN_COURS, EtatDemande, Mutation, Signalement

    if not user.has_perm("membres.gerer_membres"):
        return 0
    return (
        Mutation.objects.filter(etat__in=EN_COURS).count()
        + Signalement.objects.filter(etat=EtatDemande.BN).count()
    )


def _fonctions(user) -> list[str]:
    from apps.bureaux.services import libelles_fonctions

    return libelles_fonctions(user)
