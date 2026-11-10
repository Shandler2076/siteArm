from django.db import migrations

# Règlement intérieur, art. 14 à 18. (nom, droit de gérer, membre du bureau)
FONCTIONS = {
    ("paroisse", 2): [
        ("Chef d'Unité paroissiale", True, True),
        ("Secrétaire paroissial", True, True),
        ("Trésorier paroissial", False, True),
    ],
    ("circuit", 2): [
        ("Chef de Section de Circuit", True, True),
        ("Secrétaire de Circuit", True, True),
        ("Trésorier de Circuit", False, True),
        ("Organisateur de Circuit", False, True),
        ("Formateur de Circuit", False, True),
        ("Vérificateur de Circuit", False, False),
    ],
    ("region", 2): [
        ("Coordinateur régional", True, True),
        ("Coordinateur régional adjoint", False, True),
        ("Secrétaire régional", True, True),
        ("Rapporteur régional", False, True),
        ("Trésorier régional", False, True),
        ("Organisateur régional", False, True),
        ("Organisateur régional adjoint", False, True),
        ("Formateur régional", False, True),
        ("Conseiller régional", False, True),
        ("Vérificateur régional", False, False),
    ],
    ("national", 4): [
        ("Président", True, True),
        ("Vice-président", False, True),
        ("Secrétaire national", True, True),
        ("Secrétaire national adjoint", False, True),
        ("Trésorier national", False, True),
        ("Trésorier national adjoint", False, True),
        ("Responsable national à l'organisation (affaires sociales)", False, True),
        ("Responsable national adjoint à l'organisation (information et propagande)", False, True),
        ("Responsable national chargé de la formation", False, True),
        ("Responsable national adjoint chargé de la formation", False, True),
        ("Responsable national chargé des relations extérieures", False, True),
        ("Conseiller aux affaires spirituelles", False, True),
        ("Conseiller juridique et disciplinaire", False, True),
    ],
}


def charger(apps, schema_editor):
    Fonction = apps.get_model("bureaux", "Fonction")
    for (niveau, duree), fonctions in FONCTIONS.items():
        for ordre, (nom, gerer, bureau) in enumerate(fonctions, start=1):
            Fonction.objects.get_or_create(
                niveau=niveau, nom=nom,
                defaults={"droit_gerer": gerer, "membre_du_bureau": bureau,
                          "duree_mandat_annees": duree, "ordre": ordre},
            )


class Migration(migrations.Migration):
    dependencies = [("bureaux", "0001_initial")]
    operations = [migrations.RunPython(charger, migrations.RunPython.noop)]
