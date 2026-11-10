import os
import subprocess
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parents[3]


def _env_production(**extra):
    env = {k: v for k, v in os.environ.items() if not k.startswith(("DJANGO_", "PYTEST"))}
    env.update({"DJANGO_DEBUG": "False", "DJANGO_ALLOWED_HOSTS": "exemple.bj"})
    env.update(extra)
    return env


def _manage(*args, env):
    return subprocess.run(
        [sys.executable, "manage.py", *args], cwd=RACINE, env=env, capture_output=True, text=True
    )


def test_check_deploy_sans_avertissement():
    env = _env_production(
        DJANGO_SECRET_KEY="k7#Qp2!vZr9@Lm4$Wt8^Hy1&Bn6*Xc3(Df5)Gs0-Ja+Ue7%Ri2=Oa9",
        DJANGO_CSRF_TRUSTED_ORIGINS="https://exemple.bj",
        DJANGO_SITE_URL="https://exemple.bj",
    )
    r = _manage("check", "--deploy", "--fail-level", "WARNING", env=env)
    assert r.returncode == 0, r.stdout + r.stderr


def test_secret_obligatoire_en_production():
    r = _manage("check", env=_env_production())
    assert r.returncode != 0
    assert "DJANGO_SECRET_KEY" in r.stderr
