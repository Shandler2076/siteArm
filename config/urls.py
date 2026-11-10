from django.contrib import admin
from django.urls import path

admin.site.site_header = "Armée du Salut — Gestion"
admin.site.site_title = "Armée du Salut — Gestion"
admin.site.index_title = "Administration"

urlpatterns = [
    path("gestion/", admin.site.urls),
]
