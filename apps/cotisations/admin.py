from django.contrib import admin

from apps.cotisations.models import PartRecue, Tarif, Versement


class LectureSeule(admin.ModelAdmin):
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Versement)
class VersementAdmin(LectureSeule):
    list_display = ("membre", "montant", "date_versement", "etat", "numero_recu")
    list_filter = ("etat",)
    search_fields = ("membre__matricule", "numero_recu")


admin.site.register(Tarif, LectureSeule)
admin.site.register(PartRecue, LectureSeule)
