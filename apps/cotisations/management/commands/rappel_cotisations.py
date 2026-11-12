"""Tâche quotidienne ; le rappel ne part que le samedi (versements en attente depuis plus de
30 jours), au Secrétaire de circuit. --forcer l'envoie un autre jour."""

from django.core.management import BaseCommand
from django.utils import timezone

from apps.cotisations.services import rappeler_en_attente


class Command(BaseCommand):
    help = "Le samedi, rappelle aux circuits les versements en attente depuis plus de 30 jours."

    def add_arguments(self, parser):
        parser.add_argument("--forcer", action="store_true", help="Envoyer même hors samedi.")

    def handle(self, *args, forcer=False, **options):
        jour = timezone.localdate()
        if jour.weekday() != 5 and not forcer:
            self.stdout.write("Le rappel des cotisations part le samedi.")
            return
        n = rappeler_en_attente(jour, forcer=forcer)
        self.stdout.write(
            f"{n} versement(s) en attente depuis plus de 30 jours : circuits avertis."
        )
