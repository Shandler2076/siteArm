from django.apps import AppConfig


class MouvementsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.mouvements"
    label = "mouvements"
    verbose_name = "Mouvements (mutations, décès, démissions…)"
