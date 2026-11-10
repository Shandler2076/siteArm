from django.contrib import admin

from apps.journal.models import EntreeJournal


@admin.register(EntreeJournal)
class EntreeJournalAdmin(admin.ModelAdmin):
    list_display = ("date", "auteur", "action", "unite")
    list_filter = ("action",)
    readonly_fields = ("date", "auteur", "action", "unite", "details")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
