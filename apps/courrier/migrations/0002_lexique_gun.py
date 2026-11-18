"""Lexique goun fourni par le mainteneur le 18/11/2026 (gun de la Bible de 1923)."""

import json
import unicodedata
from pathlib import Path

from django.db import migrations

FICHIER = Path(__file__).resolve().parent.parent / "data" / "lexique_gun.json"


def _cle(mot):
    decompose = unicodedata.normalize("NFD", mot).lower()
    return "".join(c for c in decompose if unicodedata.category(c) != "Mn")[:60]


def charger(apps, schema_editor):
    MotClavier = apps.get_model("courrier", "MotClavier")
    existants = set(MotClavier.objects.values_list("mot", flat=True))
    mots = json.loads(FICHIER.read_text(encoding="utf-8"))["mots"]
    MotClavier.objects.bulk_create(
        [
            MotClavier(mot=mot, cle=_cle(mot), origine="lexique", nombre=nombre, actif=True)
            for mot, nombre in mots
            if mot not in existants
        ],
        batch_size=1000,
    )


def retirer(apps, schema_editor):
    apps.get_model("courrier", "MotClavier").objects.filter(origine="lexique").delete()


class Migration(migrations.Migration):
    dependencies = [("courrier", "0001_initial")]
    operations = [migrations.RunPython(charger, retirer)]
