"""Charge les régions, circuits et paroisses depuis un fichier JSON.

Idempotent : ne crée que ce qui manque, ne modifie jamais un code de région, ne supprime rien.
"""

import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.organisation.models import Circuit, Paroisse, Region

FICHIER_PAR_DEFAUT = Path(__file__).resolve().parents[2] / "data" / "territoire_provisoire.json"


class Command(BaseCommand):
    help = "Charge l'organisation territoriale (régions, circuits, paroisses) depuis un JSON."

    def add_arguments(self, parser):
        parser.add_argument("--fichier", default=str(FICHIER_PAR_DEFAUT))

    def handle(self, *args, fichier, **options):
        chemin = Path(fichier)
        if not chemin.exists():
            raise CommandError(f"Fichier introuvable : {chemin}")
        donnees = json.loads(chemin.read_text(encoding="utf-8"))
        compteurs = {"Régions": [0, 0], "Circuits": [0, 0], "Paroisses": [0, 0]}

        def compter(nom, cree):
            compteurs[nom][0 if cree else 1] += 1

        with transaction.atomic():
            for r in donnees["regions"]:
                existante = Region.objects.filter(code=r["code"]).first()
                if existante and existante.nom != r["nom"]:
                    raise CommandError(
                        f"Le code {r['code']} est déjà utilisé par la région « {existante.nom} », "
                        f"pas « {r['nom']} ». Rien n'a été modifié."
                    )
                region, cree = Region.objects.get_or_create(
                    code=r["code"], defaults={"nom": r["nom"]}
                )
                compter("Régions", cree)
                for c in r["circuits"]:
                    circuit, cree = Circuit.objects.get_or_create(region=region, nom=c["nom"])
                    compter("Circuits", cree)
                    for nom_paroisse in c["paroisses"]:
                        _, cree = Paroisse.objects.get_or_create(circuit=circuit, nom=nom_paroisse)
                        compter("Paroisses", cree)

        self.stdout.write(
            " · ".join(f"{k} : {v[0]} créées, {v[1]} existantes" for k, v in compteurs.items())
        )
