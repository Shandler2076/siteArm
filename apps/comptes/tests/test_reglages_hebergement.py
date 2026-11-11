import os
import subprocess
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parents[3]


def _reglage(nom, **env):
    code = f"import django; django.setup(); from django.conf import settings; print(settings.{nom})"
    base = {k: v for k, v in os.environ.items() if not k.startswith("DJANGO_")}
    base.update(
        DJANGO_SETTINGS_MODULE="config.settings",
        DJANGO_SECRET_KEY="x" * 50,
        DJANGO_SITE_URL="https://essai.example",
        DJANGO_ALLOWED_HOSTS="essai.example",
        DJANGO_ENV_FILE="/inexistant/.env",
    )
    base.update(env)
    r = subprocess.run(
        [sys.executable, "-c", code], cwd=RACINE, env=base, capture_output=True, text=True
    )
    assert r.returncode == 0, r.stderr
    return r.stdout.strip()


def test_dossier_prive_configurable(tmp_path):
    assert _reglage("PRIVATE_MEDIA_ROOT", DJANGO_PRIVATE_MEDIA_ROOT=str(tmp_path)) == str(tmp_path)


def test_redirection_https_desactivable():
    assert _reglage("SECURE_SSL_REDIRECT") == "True"
    assert _reglage("SECURE_SSL_REDIRECT", DJANGO_SECURE_SSL_REDIRECT="False") == "False"


def test_site_demo_par_variable():
    assert _reglage("SITE_DEMO") == "False"
    assert _reglage("SITE_DEMO", DJANGO_SITE_DEMO="True") == "True"


def test_fichier_env_lu(tmp_path):
    f = tmp_path / ".env"
    f.write_text("DJANGO_SITE_DEMO=True\n", encoding="utf-8")
    assert _reglage("SITE_DEMO", DJANGO_ENV_FILE=str(f)) == "True"
