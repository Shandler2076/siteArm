"""À programmer chaque jour chez l'hébergeur : alertes d'échéance des mandats."""

from django.core.management.base import BaseCommand

from apps.bureaux.services import alertes_echeances


class Command(BaseCommand):
    help = "Envoie les alertes d'échéance (60 jours) et de mandats échus non renouvelés."

    def handle(self, *args, **options):
        echeances, echus = alertes_echeances()
        self.stdout.write(f"Échéances : {echeances} · Échus : {echus}")
