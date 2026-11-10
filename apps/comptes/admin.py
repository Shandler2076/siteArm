from django.contrib import admin

from apps.comptes.models import Compte


@admin.register(Compte)
class CompteAdmin(admin.ModelAdmin):
    list_display = ("identifiant", "nom_affiche", "is_active", "is_staff")
    search_fields = ("identifiant", "nom_affiche")
    exclude = ("password",)
