from django.contrib import admin

from apps.securite.models import DoubleVerification


@admin.register(DoubleVerification)
class DoubleVerificationAdmin(admin.ModelAdmin):
    list_display = ("compte", "active", "date_activation")
    fields = ("compte", "active", "date_activation")
    readonly_fields = ("compte", "active", "date_activation")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
