from django.apps import AppConfig


class BureauxConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.bureaux"
    label = "bureaux"
    verbose_name = "Bureaux et mandats"
