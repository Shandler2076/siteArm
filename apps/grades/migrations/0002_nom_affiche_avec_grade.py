"""Les comptes existants prennent le nom affiché « Grade Prénoms NOM » (revue finale)."""

from django.db import migrations

from apps.membres.grades import Grade


def recalculer(apps, schema_editor):
    Membre = apps.get_model("membres", "Membre")
    Compte = apps.get_model("comptes", "Compte")
    for m in Membre.objects.exclude(compte=None).only("nom", "prenoms", "grade", "compte_id"):
        nom = f"{m.prenoms} {m.nom.upper()}".strip()
        if m.grade is not None:
            nom = f"{Grade(m.grade).label} {nom}"
        Compte.objects.filter(pk=m.compte_id).update(nom_affiche=nom[:150])


class Migration(migrations.Migration):
    dependencies = [("grades", "0001_initial"), ("comptes", "0001_initial")]
    operations = [migrations.RunPython(recalculer, migrations.RunPython.noop)]
