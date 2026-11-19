from django.conf import settings

SESSION_OK = "double_verification_ok"
SESSION_SECRET = "double_verification_secret"
SESSION_ECHECS = "double_verification_echecs"
ECHECS_MAX = 5


def doit_verifier(user) -> bool:
    """Obligatoire pour les comptes ayant les pouvoirs du BN, et pour le Trésorier national
    (et son adjoint) qui prépare les reversements d'argent."""
    from apps.bureaux.perimetre import est_bn, est_tresorier_national

    if not getattr(settings, "DOUBLE_VERIFICATION_BN", True):
        return False
    if not getattr(user, "is_authenticated", False):
        return False
    # Mandat national, compte technique, ou autorisation BN de transition (mêmes pouvoirs).
    return (
        est_bn(user) or user.has_perm("membres.gerer_membres") or est_tresorier_national(user)
    )


def est_verifie(request) -> bool:
    return request.session.get(SESSION_OK) == request.user.pk


def double_verification_active(user) -> bool:
    from apps.securite.models import DoubleVerification

    return DoubleVerification.objects.filter(compte=user, active=True).exists()


def confirmer_identite(user, mot_de_passe: str, code: str = "") -> str | None:
    """Revérifie que c'est bien le titulaire du compte, avant une action sensible (changer sa
    signature…) : son mot de passe, plus le code à 6 chiffres si sa double vérification est
    active. Renvoie None si c'est bon, sinon le message d'erreur."""
    import datetime
    import time

    from django.db import transaction
    from django.utils import timezone

    from apps.journal.models import DOUBLE_VERIFICATION, EntreeJournal
    from apps.journal.services import journaliser
    from apps.securite.models import DoubleVerification
    from apps.securite.totp import verifier

    # Essais erronés comptés dans le journal (commun à tous les processus du site) : 5 en 15 min.
    recents = EntreeJournal.objects.filter(
        auteur=user,
        action=DOUBLE_VERIFICATION,
        details__evenement="confirmation_echouee",
        date__gte=timezone.now() - datetime.timedelta(minutes=15),
    ).count()
    if recents >= ECHECS_MAX:
        return "Trop d'essais erronés : réessayez dans 15 minutes."
    if not user.check_password(mot_de_passe or ""):
        journaliser(user, DOUBLE_VERIFICATION, evenement="confirmation_echouee")
        return "Mot de passe incorrect."
    with transaction.atomic():
        dv = DoubleVerification.objects.select_for_update().filter(compte=user, active=True).first()
        if dv is None:
            return None
        maintenant = timezone.now()
        if dv.bloque_jusqu_a and dv.bloque_jusqu_a > maintenant:
            return "Trop de codes erronés : réessayez plus tard."
        pas = verifier(dv.secret, code, time.time(), dv.dernier_pas)
        if pas is None:
            dv.echecs += 1
            if dv.echecs >= ECHECS_MAX:
                dv.echecs = 0
                dv.bloque_jusqu_a = maintenant + datetime.timedelta(minutes=15)
            dv.save(update_fields=["echecs", "bloque_jusqu_a"])
            journaliser(user, DOUBLE_VERIFICATION, evenement="confirmation_echouee")
            return "Code de double vérification incorrect ou déjà utilisé."
        dv.dernier_pas, dv.echecs = pas, 0
        dv.save(update_fields=["dernier_pas", "echecs"])
    return None
