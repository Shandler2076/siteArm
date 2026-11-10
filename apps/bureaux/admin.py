from django.contrib import admin

from apps.bureaux.models import Fonction, Mandat


@admin.register(Fonction)
class FonctionAdmin(admin.ModelAdmin):
    list_display = ("nom", "niveau", "droit_gerer", "membre_du_bureau", "duree_mandat_annees")
    list_filter = ("niveau", "droit_gerer")
    list_editable = ("droit_gerer",)

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Mandat)
class MandatAdmin(admin.ModelAdmin):
    list_display = ("membre", "fonction", "unite", "date_debut", "date_fin_prevue", "date_fin")
    list_filter = ("fonction__niveau", "fonction")
    search_fields = ("membre__matricule", "membre__nom", "membre__prenoms")
    autocomplete_fields = ()
    raw_id_fields = ("membre", "paroisse", "circuit", "region")

    def has_delete_permission(self, request, obj=None):
        return False
