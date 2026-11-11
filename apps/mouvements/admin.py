from django.contrib import admin

from apps.mouvements.models import AvisMutation, HistoriqueMembre, Mutation, Sanction, Signalement


class LectureSeule(admin.ModelAdmin):
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(HistoriqueMembre)
class HistoriqueAdmin(LectureSeule):
    list_display = ("membre", "type", "ancien", "nouveau", "date_effet", "par")
    list_filter = ("type",)
    search_fields = ("membre__matricule", "membre__nom")


@admin.register(Mutation)
class MutationAdmin(LectureSeule):
    list_display = ("pk", "membre", "paroisse_depart", "paroisse_arrivee", "etat", "date_demande")
    list_filter = ("etat",)


@admin.register(AvisMutation)
class AvisAdmin(LectureSeule):
    list_display = ("mutation", "niveau", "favorable", "par", "date")


@admin.register(Signalement)
class SignalementAdmin(LectureSeule):
    list_display = ("membre", "type", "etat", "date_effet", "unite", "date_demande")
    list_filter = ("type", "etat")


@admin.register(Sanction)
class SanctionAdmin(LectureSeule):
    list_display = ("membre", "type", "degre", "date_debut", "date_fin", "levee_le")
    list_filter = ("type", "degre")
