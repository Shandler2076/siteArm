"""Tâche quotidienne : rappel aux circuits des versements en attente depuis plus de 30 jours."""

from django.core.management import BaseCommand
from django.utils import timezone

from apps.cotisations.services import rappeler_en_attente


class Command(BaseCommand):
    help = "Rappelle aux circuits les versements de cotisation en attente depuis plus de 30 jours."

    def handle(self, *args, **options):
        n = rappeler_en_attente(timezone.localdate())
        self.stdout.write(
            f"{n} versement(s) en attente depuis plus de 30 jours : circuits avertis."
        )
