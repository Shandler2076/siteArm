"""Site d'essai : efface TOUTES les données et recrée des membres fictifs (avec grades).

Refusé hors site d'essai et hors PostgreSQL. Le journal est vidé par TRUNCATE (il ne peut pas
l'être autrement) : c'est voulu ici, car il ne contient que des opérations sur des données
fictives. Le compte technique est effacé aussi : à recréer avec createsuperuser.
"""

from django.conf import settings
from django.core.management import BaseCommand, CommandError, call_command
from django.db import connection


class Command(BaseCommand):
    help = "Site d'essai seulement : efface tout et recrée des membres fictifs."

    def add_arguments(self, parser):
        parser.add_argument("--oui", action="store_true", help="Confirme l'effacement total.")
        parser.add_argument("--membres", type=int, default=150)

    def handle(self, *args, oui, membres, **options):
        if not getattr(settings, "SITE_DEMO", False):
            raise CommandError(
                "Refusé : cette commande ne fonctionne que sur un site d'essai "
                "(DJANGO_SITE_DEMO=True)."
            )
        if not oui:
            raise CommandError(
                "Cette commande efface TOUTES les données du site d'essai, compte technique "
                "compris. Relancez-la avec --oui pour confirmer."
            )
        if connection.vendor != "postgresql":
            raise CommandError("Cette commande demande une base PostgreSQL.")
        call_command("flush", interactive=False, verbosity=0)
        call_command("charger_territoire", stdout=self.stdout)
        call_command("peupler_demo", membres=membres, stdout=self.stdout)
        self.stdout.write(
            self.style.WARNING(
                "\nLe compte technique a été effacé : recréez-le avec "
                "« python manage.py createsuperuser », puis réactivez sa double vérification."
            )
        )
