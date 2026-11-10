from django.contrib import admin, messages
from django.db.models import Count

from apps.organisation.models import Circuit, Paroisse, Region


class FermableAdmin(admin.ModelAdmin):
    """Pas de suppression : on ferme ou on rouvre."""

    actions = ["fermer_selection", "rouvrir_selection"]
    readonly_fields = ("date_fermeture",)

    def has_delete_permission(self, request, obj=None):
        return False

    @admin.action(description="Fermer la sélection")
    def fermer_selection(self, request, queryset):
        for obj in queryset:
            obj.fermer()
        self.message_user(request, f"{queryset.count()} élément(s) fermé(s).", messages.SUCCESS)

    @admin.action(description="Rouvrir la sélection")
    def rouvrir_selection(self, request, queryset):
        for obj in queryset:
            obj.rouvrir()
        self.message_user(request, f"{queryset.count()} élément(s) rouvert(s).", messages.SUCCESS)


@admin.register(Region)
class RegionAdmin(FermableAdmin):
    list_display = ("code", "nom", "active", "nb_circuits")
    list_filter = ("active",)
    search_fields = ("nom", "code")

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(_nb=Count("circuits"))

    @admin.display(description="circuits", ordering="_nb")
    def nb_circuits(self, obj):
        return obj._nb

    def get_readonly_fields(self, request, obj=None):
        base = super().get_readonly_fields(request, obj)
        return (*base, "code") if obj else base


@admin.register(Circuit)
class CircuitAdmin(FermableAdmin):
    list_display = ("nom", "region", "active", "nb_paroisses")
    list_filter = ("active", "region")
    search_fields = ("nom",)
    list_select_related = ("region",)

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(_nb=Count("paroisses"))

    @admin.display(description="paroisses", ordering="_nb")
    def nb_paroisses(self, obj):
        return obj._nb


@admin.register(Paroisse)
class ParoisseAdmin(FermableAdmin):
    list_display = ("nom", "circuit", "region_affichee", "active")
    list_filter = ("active", "circuit__region", "circuit")
    search_fields = ("nom", "circuit__nom")
    list_select_related = ("circuit__region",)

    @admin.display(description="région", ordering="circuit__region__code")
    def region_affichee(self, obj):
        return obj.circuit.region
