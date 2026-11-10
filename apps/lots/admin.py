from django.contrib import admin

from apps.lots.models import LigneLot, Lot


class LectureSeule:
    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Lot)
class LotAdmin(LectureSeule, admin.ModelAdmin):
    list_display = ("__str__", "etat", "date_creation", "cree_par", "date_validation")
    list_filter = ("etat", "region")
    exclude = ("fichier",)


@admin.register(LigneLot)
class LigneLotAdmin(LectureSeule, admin.ModelAdmin):
    list_display = ("lot", "numero", "etat", "membre")
    list_filter = ("etat",)
