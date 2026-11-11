from django.core.management.base import BaseCommand, CommandError

from apps.comptes.models import Compte, normaliser_identifiant
from apps.journal.models import DOUBLE_VERIFICATION
from apps.journal.services import journaliser
from apps.securite.models import DoubleVerification


class Command(BaseCommand):
    help = "Désactive la double vérification d'un compte (téléphone perdu)."

    def add_arguments(self, parser):
        parser.add_argument("identifiant")

    def handle(self, *args, identifiant, **options):
        compte = Compte.objects.filter(identifiant=normaliser_identifiant(identifiant)).first()
        if compte is None:
            raise CommandError(f"Aucun compte « {identifiant} ».")
        n = DoubleVerification.objects.filter(compte=compte).update(
            active=False, secret="", dernier_pas=None
        )
        journaliser(
            None, DOUBLE_VERIFICATION, evenement="reinitialisation", compte=compte.identifiant
        )
        self.stdout.write(
            f"Double vérification réinitialisée pour {compte.identifiant}."
            if n
            else f"{compte.identifiant} n'avait pas de double vérification."
        )
