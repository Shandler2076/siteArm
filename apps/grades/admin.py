from django.contrib import admin

from apps.grades.models import HistoriqueGrade


@admin.register(HistoriqueGrade)
class HistoriqueGradeAdmin(admin.ModelAdmin):
    list_display = ("membre", "grade", "date_effet", "mode", "reference")
    list_filter = ("grade", "mode")
    search_fields = ("membre__matricule", "membre__nom")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
