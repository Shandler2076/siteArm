from django.apps import AppConfig


class SecuriteConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.securite"
    label = "securite"
    verbose_name = "Sécurité (double vérification)"

    def ready(self):
        from apps.securite.admin_lecture import mettre_la_gestion_en_lecture_seule

        mettre_la_gestion_en_lecture_seule()
