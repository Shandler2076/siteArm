from django.conf import settings

SANS_MENU = ("/securite/", "/mot-de-passe/", "/connexion/")


def site(request):
    user = getattr(request, "user", None)
    connecte = bool(user and user.is_authenticated)
    return {
        "site_demo": getattr(settings, "SITE_DEMO", False),
        # Menu de gauche : seulement une fois connecté et vérifié (pas sur les pages d'accès).
        "afficher_menu": connecte
        and not getattr(user, "doit_changer_mot_de_passe", False)
        and not request.path.startswith(SANS_MENU),
        "page_accueil": request.path == "/",
    }
