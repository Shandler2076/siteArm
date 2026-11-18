from django.core.management.base import BaseCommand

from apps.courrier.services import DUREE_ABANDON_JOURS, purger_abandonnes


class Command(BaseCommand):
    help = "Efface les courriers abandonnés depuis plus d'un mois (tâche quotidienne)."

    def handle(self, *args, **options):
        n = purger_abandonnes(DUREE_ABANDON_JOURS)
        self.stdout.write(f"{n} courrier(s) abandonné(s) effacé(s).")
