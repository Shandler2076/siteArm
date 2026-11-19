"""Faille H2 : le paiement simulé (aucun argent réel) ne doit jamais s'allumer sur le vrai site."""

import os
import subprocess
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parents[2]


def _charger_reglages(**variables):
    env = {
        k: v
        for k, v in os.environ.items()
        if not k.startswith("DJANGO_") and k != "DATABASE_URL"
    }
    env.update(
        DJANGO_SECRET_KEY="cle-de-test",
        DJANGO_SITE_URL="https://exemple.test",
        DJANGO_ALLOWED_HOSTS="exemple.test",
        DJANGO_ENV_FILE=str(RACINE / "inexistant.env"),
        DJANGO_SETTINGS_MODULE="config.settings",
        **variables,
    )
    return subprocess.run(
        [sys.executable, "-c", "import django; django.setup()"],
        cwd=RACINE,
        env=env,
        capture_output=True,
        text=True,
    )


def test_refuse_sur_le_vrai_site():
    r = _charger_reglages(DJANGO_DEBUG="False", DJANGO_PAIEMENT_SIMULE="True")
    assert r.returncode != 0 and "PAIEMENT_SIMULE" in r.stderr


def test_permis_sur_le_site_d_essai():
    r = _charger_reglages(
        DJANGO_DEBUG="False", DJANGO_SITE_DEMO="True", DJANGO_PAIEMENT_SIMULE="True"
    )
    assert r.returncode == 0, r.stderr


def test_ferme_par_defaut_sur_le_vrai_site():
    r = _charger_reglages(DJANGO_DEBUG="False")
    assert r.returncode == 0, r.stderr
