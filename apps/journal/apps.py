from django.apps import AppConfig


class JournalConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.journal"
    label = "journal"
    verbose_name = "Journal"

    def ready(self):
        from django.contrib.auth.signals import user_logged_in, user_login_failed

        from apps.journal import models
        from apps.journal.services import journaliser

        def connexion(sender, request, user, **kwargs):
            journaliser(user, models.CONNEXION)

        def echec(sender, credentials, request=None, **kwargs):
            identifiant = str(credentials.get("username", ""))[:60]
            journaliser(None, models.CONNEXION_ECHOUEE, identifiant=identifiant)

        user_logged_in.connect(connexion, dispatch_uid="journal_connexion")
        user_login_failed.connect(echec, dispatch_uid="journal_connexion_echouee")
