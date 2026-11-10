from apps.comptes.models import normaliser_identifiant


def identifiant_pour_blocage(request, credentials) -> str:
    """Identifiant normalisé : « 2015-01as-0157 » et « 2015-01AS-0157 » comptent ensemble."""
    valeur = (credentials or {}).get("username")
    if valeur is None and request is not None:
        valeur = request.POST.get("username", "")
    return normaliser_identifiant(valeur or "")
