from django.contrib import admin

from apps.membres.models import Affectation, CompteurMatricule, Membre, PhotoIdentite


class LectureSeuleMixin:
    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False


class AffectationEnLigne(LectureSeuleMixin, admin.TabularInline):
    model = Affectation
    extra = 0
    fields = ("date_debut", "date_fin", "paroisse", "circuit_a_date", "region_a_date", "motif")


@admin.register(Membre)
class MembreAdmin(admin.ModelAdmin):
    """L'enregistrement passe uniquement par /membres/bn/enregistrer/ (matricule garanti)."""

    list_display = ("matricule", "nom_complet", "categorie", "statut", "region_integration")
    list_filter = ("categorie", "statut", "region_integration")
    search_fields = ("matricule", "nom", "prenoms", "npi")
    readonly_fields = (
        "matricule", "annee_integration", "paroisse_integration", "region_integration",
        "compte", "date_enregistrement", "enregistre_par",
    )
    exclude = ("photo_cip",)
    inlines = [AffectationEnLigne]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(CompteurMatricule)
class CompteurMatriculeAdmin(LectureSeuleMixin, admin.ModelAdmin):
    list_display = ("annee", "region", "dernier_numero")
    list_filter = ("annee", "region")


@admin.register(PhotoIdentite)
class PhotoIdentiteAdmin(LectureSeuleMixin, admin.ModelAdmin):
    list_display = ("membre", "etat", "date_depot", "date_decision", "decide_par")
    list_filter = ("etat",)
    exclude = ("fichier",)
