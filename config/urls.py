from django.contrib import admin
from django.urls import include, path

admin.site.site_header = "Armée du Salut — Gestion"
admin.site.site_title = "Armée du Salut — Gestion"
admin.site.index_title = "Administration"

urlpatterns = [
    path("gestion/", admin.site.urls),
    path("membres/", include("apps.membres.urls")),
    path("notifications/", include("apps.notifications.urls")),
    path("bureau/", include("apps.listes.urls")),
    path("bureau/", include("apps.bureaux.urls")),
    path("lots/", include("apps.lots.urls")),
    path("", include("apps.comptes.urls")),
]
