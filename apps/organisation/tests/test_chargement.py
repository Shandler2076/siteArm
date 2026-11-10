import json

import pytest
from django.core.management import CommandError, call_command

from apps.organisation.models import Circuit, Paroisse, Region


def test_chargement_complet(db):
    call_command("charger_territoire")
    assert Region.objects.count() == 13
    assert Circuit.objects.count() == 87
    assert Paroisse.objects.count() == 427
    assert Region.objects.get(code="13").nom == "NORD"
    assert Region.objects.get(code="09").circuits.filter(nom="Adja-Ouèrè (Plateau III)").exists()


def test_caracteres_speciaux_conserves(db):
    call_command("charger_territoire")
    assert Circuit.objects.filter(nom="Sô-Tchanhoué").exists()
    assert Paroisse.objects.filter(nom="Paroisse Itè Anu « Vie Neuve » de IKPINLE SEKANME").exists()
    assert Paroisse.objects.filter(nom__contains="d’AKPADJLAME").exists()


def test_idempotent(db):
    call_command("charger_territoire")
    call_command("charger_territoire")
    assert (Region.objects.count(), Circuit.objects.count(), Paroisse.objects.count()) == (
        13,
        87,
        427,
    )


def test_conflit_de_code_refuse_sans_rien_ecrire(db, tmp_path):
    Region.objects.create(code="01", nom="AUTRE NOM")
    f = tmp_path / "t.json"
    f.write_text(
        json.dumps(
            {
                "regions": [
                    {
                        "code": "01",
                        "nom": "PORTO-NOVO",
                        "circuits": [{"nom": "Davo", "paroisses": ["P1"]}],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(CommandError, match="déjà utilisé"):
        call_command("charger_territoire", fichier=str(f))
    assert Circuit.objects.count() == 0
