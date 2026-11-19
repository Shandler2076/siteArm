from apps.comptes.models import normaliser_identifiant


def identifiant_pour_blocage(request, credentials) -> str:
    """Identifiant normalisé : « 2015-01as-0157 » et « 2015-01AS-0157 » comptent ensemble."""
    valeur = (credentials or {}).get("username")
    if valeur is None and request is not None:
        valeur = request.POST.get("username", "")
    return normaliser_identifiant(valeur or "")


def adresse_ip(request) -> str:
    """Adresse IP du visiteur. Derrière le relais de l'hébergeur (DERRIERE_RELAIS), on prend la
    DERNIÈRE adresse de X-Forwarded-For : c'est celle que le relais a ajoutée ; les précédentes
    viennent du visiteur et peuvent être inventées."""
    from django.conf import settings

    if getattr(settings, "DERRIERE_RELAIS", False):
        relais = request.META.get("HTTP_X_FORWARDED_FOR", "")
        derniere = relais.split(",")[-1].strip()
        if derniere:
            return derniere
    return request.META.get("REMOTE_ADDR", "")


def adresse_bloquee(request) -> bool:
    """Trop d'échecs de connexion depuis cette adresse IP, tous identifiants confondus, pendant la
    durée de blocage d'axes."""
    import datetime

    from axes.models import AccessAttempt
    from django.conf import settings
    from django.db.models import Sum
    from django.utils import timezone

    depuis = timezone.now() - datetime.timedelta(hours=settings.AXES_COOLOFF_TIME)
    total = (
        AccessAttempt.objects.filter(ip_address=adresse_ip(request), attempt_time__gte=depuis)
        .aggregate(n=Sum("failures_since_start"))
        .get("n")
    )
    return (total or 0) >= settings.LIMITE_ECHECS_PAR_IP
