from django.core.management.base import BaseCommand

from apps.mouvements.sanctions import appliquer_sanctions


class Command(BaseCommand):
    help = "Début des sanctions datées et retour à « Actif » à la fin des sanctions temporaires."

    def handle(self, *args, **options):
        debuts, fins = appliquer_sanctions()
        self.stdout.write(f"Sanctions commencées : {debuts} ; sanctions terminées : {fins}")
