from django.apps import AppConfig


class SecuriteConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.securite"
    label = "securite"
    verbose_name = "Sécurité (double vérification)"
