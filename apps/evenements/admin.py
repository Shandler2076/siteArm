from django.contrib import admin

from apps.evenements.models import Convocation, Evenement


class LectureSeule(admin.ModelAdmin):
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


admin.site.register(Evenement, LectureSeule)
admin.site.register(Convocation, LectureSeule)
