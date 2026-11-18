"""Courriers abandonnés avant le 18/11/2026 : date d'abandon fixée à la migration, pour qu'ils
soient effacés un mois plus tard comme les autres."""

from django.db import migrations
from django.utils import timezone


def dater(apps, schema_editor):
    Courrier = apps.get_model("courrier", "Courrier")
    Courrier.objects.filter(etat="annule", date_abandon__isnull=True).update(
        date_abandon=timezone.now()
    )


class Migration(migrations.Migration):
    dependencies = [("courrier", "0003_presentation_et_abandon")]
    operations = [migrations.RunPython(dater, migrations.RunPython.noop)]
