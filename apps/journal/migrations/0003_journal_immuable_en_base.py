"""Le journal est protégé par la base elle-même : UPDATE et DELETE sont refusés (§9.4).

Remarque SQLite : une future migration qui reconstruit la table supprime ces déclencheurs ;
il faudra alors les recréer (voir docs/guide-maintenance.md §19).
"""

from django.db import migrations

TABLE = "journal_entreejournal"

POSTGRES = f"""
CREATE OR REPLACE FUNCTION journal_immuable() RETURNS trigger AS $$
BEGIN
    RAISE EXCEPTION 'Le journal ne peut être ni modifié ni effacé.';
END;
$$ LANGUAGE plpgsql;
DROP TRIGGER IF EXISTS journal_immuable ON {TABLE};
CREATE TRIGGER journal_immuable BEFORE UPDATE OR DELETE ON {TABLE}
    FOR EACH ROW EXECUTE FUNCTION journal_immuable();
"""
POSTGRES_RETOUR = f"""
DROP TRIGGER IF EXISTS journal_immuable ON {TABLE};
DROP FUNCTION IF EXISTS journal_immuable();
"""
SQLITE = [
    f"""CREATE TRIGGER IF NOT EXISTS journal_pas_de_modification BEFORE UPDATE ON {TABLE}
        BEGIN SELECT RAISE(ABORT, 'Le journal ne peut pas être modifié.'); END;""",
    f"""CREATE TRIGGER IF NOT EXISTS journal_pas_d_effacement BEFORE DELETE ON {TABLE}
        BEGIN SELECT RAISE(ABORT, 'Le journal ne peut pas être effacé.'); END;""",
]
SQLITE_RETOUR = [
    "DROP TRIGGER IF EXISTS journal_pas_de_modification;",
    "DROP TRIGGER IF EXISTS journal_pas_d_effacement;",
]


def creer(apps, schema_editor):
    vendeur = schema_editor.connection.vendor
    if vendeur == "postgresql":
        schema_editor.execute(POSTGRES)
    elif vendeur == "sqlite":
        for sql in SQLITE:
            schema_editor.execute(sql)


def supprimer(apps, schema_editor):
    vendeur = schema_editor.connection.vendor
    if vendeur == "postgresql":
        schema_editor.execute(POSTGRES_RETOUR)
    elif vendeur == "sqlite":
        for sql in SQLITE_RETOUR:
            schema_editor.execute(sql)


class Migration(migrations.Migration):
    dependencies = [("journal", "0002_alter_entreejournal_options_and_more")]

    operations = [migrations.RunPython(creer, supprimer)]
