from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import BaseUserCreationForm, UserChangeForm

from apps.comptes.models import Compte


class CreationCompteForm(BaseUserCreationForm):
    class Meta:
        model = Compte
        fields = ("identifiant",)


class ModificationCompteForm(UserChangeForm):
    class Meta:
        model = Compte
        fields = "__all__"


@admin.register(Compte)
class CompteAdmin(UserAdmin):
    add_form = CreationCompteForm
    form = ModificationCompteForm
    list_display = ("identifiant", "nom_affiche", "is_active", "is_staff")
    list_filter = ("is_active", "is_staff")
    search_fields = ("identifiant", "nom_affiche")
    ordering = ("identifiant",)
    readonly_fields = ("last_login", "date_creation")
    fieldsets = (
        (None, {"fields": ("identifiant", "password", "nom_affiche")}),
        ("État", {"fields": ("is_active", "doit_changer_mot_de_passe")}),
        ("Droits", {"fields": ("is_staff", "is_superuser", "groups", "user_permissions")}),
        ("Dates", {"fields": ("last_login", "date_creation")}),
    )
    add_fieldsets = (
        (None, {"classes": ("wide",), "fields": ("identifiant", "password1", "password2")}),
    )
