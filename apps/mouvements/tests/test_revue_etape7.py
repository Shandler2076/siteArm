"""Corrections de la relecture finale de l'étape 7 (sanctions, journal)."""

from datetime import date

import pytest
from django.db import DatabaseError, connection, transaction
from django.db.models import ProtectedError

from apps.journal.models import EntreeJournal, JournalImmuable
from apps.journal.services import journaliser
from apps.mouvements.sanctions import appliquer_sanctions, enregistrer_sanction
from apps.mouvements.services import blocage_rehabilitation, decider_signalement, signaler


def test_rehabilitation_apres_exclusion_definitive_tient(monde, compte_technique):
    m1 = monde["m1"]
    s = enregistrer_sanction(
        membre=m1,
        degre=3,
        type="exclusion_definitive",
        date_debut=date(2025, 1, 1),
        motif="Faute grave",
        reference="D-1",
        par=compte_technique,
        jour=date(2025, 1, 1),
    )
    m1.refresh_from_db()
    sig = signaler(
        membre=m1,
        type="rehabilitation",
        par=compte_technique,
        unite="national",
        reference="Engagement 9",
        jour=date(2026, 11, 11),
    )
    decider_signalement(
        signalement=sig, confirmer=True, par=compte_technique, jour=date(2026, 11, 11)
    )
    s.refresh_from_db()
    assert s.levee_le == date(2026, 11, 11) and "Réhabilitation" in s.motif_levee
    appliquer_sanctions(date(2026, 11, 12))
    m1.refresh_from_db()
    assert m1.statut == "actif"
    enregistrer_sanction(  # un réhabilité peut de nouveau être sanctionné
        membre=m1,
        degre=1,
        type="blame",
        date_debut=date(2026, 12, 1),
        motif="Retard",
        reference="D-2",
        par=compte_technique,
        jour=date(2026, 12, 1),
    )


def test_suppression_compte_ne_touche_pas_le_journal(monde):
    compte = monde["m4"].compte
    journaliser(compte, "test")
    with pytest.raises(ProtectedError):
        compte.delete()
    e = EntreeJournal.objects.get(action="test")
    assert e.auteur == compte and e.auteur_identifiant == compte.identifiant


def test_base_manager_ne_peut_pas_effacer(compte_technique):
    journaliser(compte_technique, "test")
    with pytest.raises(JournalImmuable):
        EntreeJournal._base_manager.all().delete()


def test_sql_direct_refuse_par_la_base(compte_technique):
    e = journaliser(compte_technique, "test")
    table = EntreeJournal._meta.db_table
    for sql in (
        f"UPDATE {table} SET action = 'x' WHERE id = %s",
        f"DELETE FROM {table} WHERE id = %s",
    ):
        with pytest.raises(DatabaseError), transaction.atomic(), connection.cursor() as c:
            c.execute(sql, [e.pk])
    assert EntreeJournal.objects.get(pk=e.pk).action == "test"


def test_rehabilitation_sans_exclusion_sanction_inchangee(monde, compte_technique):
    from apps.mouvements.statuts import changer_statut

    m1 = monde["m1"]
    changer_statut(m1, "demissionnaire", par=None, date_effet=date(2025, 1, 1), motif="Démission")
    assert blocage_rehabilitation(m1, date(2026, 11, 11)) is None
