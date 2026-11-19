from urllib.parse import urlencode

from django.contrib import admin
from django.shortcuts import redirect
from django.urls import include, path

admin.site.site_header = "Armée du Salut — Gestion"
admin.site.site_title = "Armée du Salut — Gestion"
admin.site.index_title = "Administration"



def connexion_de_la_gestion(request):
    """La gestion n'a pas sa propre connexion : tout passe par /connexion/ (limites par
    identifiant ET par adresse IP, double vérification). Un membre déjà connecté qui n'a pas accès
    à la gestion reçoit un refus (sinon : boucle entre /gestion/ et /connexion/)."""
    if request.user.is_authenticated:
        from django.core.exceptions import PermissionDenied

        raise PermissionDenied("La gestion technique est réservée au compte technique.")
    suivant = request.GET.get("next") or "/gestion/"
    return redirect(f"/connexion/?{urlencode({'next': suivant})}")


urlpatterns = [
    path("gestion/login/", connexion_de_la_gestion),
    path("gestion/", admin.site.urls),
    path("membres/", include("apps.membres.urls")),
    path("notifications/", include("apps.notifications.urls")),
    path("bureau/", include("apps.mouvements.urls")),
    path("bureau/", include("apps.listes.urls")),
    path("bureau/", include("apps.bureaux.urls")),
    path("lots/", include("apps.lots.urls")),
    path("journal/", include("apps.journal.urls")),
    path("grades/", include("apps.grades.urls")),
    path("cotisations/", include("apps.cotisations.urls")),
    path("evenements/", include("apps.evenements.urls")),
    path("tresorerie/", include("apps.tresorerie.urls")),
    path("courrier/", include("apps.courrier.urls")),
    path("securite/", include("apps.securite.urls")),
    path("", include("apps.comptes.urls")),
]
