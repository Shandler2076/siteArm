from django.conf import settings

SESSION_OK = "double_verification_ok"
SESSION_SECRET = "double_verification_secret"
SESSION_ECHECS = "double_verification_echecs"
ECHECS_MAX = 5


def doit_verifier(user) -> bool:
    """Obligatoire pour les comptes ayant un mandat national (et le compte technique)."""
    from apps.bureaux.perimetre import est_bn

    if not getattr(settings, "DOUBLE_VERIFICATION_BN", True):
        return False
    return bool(getattr(user, "is_authenticated", False)) and est_bn(user)


def est_verifie(request) -> bool:
    return request.session.get(SESSION_OK) == request.user.pk


def double_verification_active(user) -> bool:
    from apps.securite.models import DoubleVerification

    return DoubleVerification.objects.filter(compte=user, active=True).exists()
