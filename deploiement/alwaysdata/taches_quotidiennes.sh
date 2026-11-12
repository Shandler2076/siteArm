#!/usr/bin/env bash
# Tâche quotidienne (à programmer chaque matin dans « Tâches planifiées »).
set -euo pipefail
DOSSIER="$(cd "$(dirname "$0")/../.." && pwd)"
VENV="${VENV:-$HOME/venv-siteArm}"
cd "$DOSSIER"
"$VENV/bin/python" manage.py verifier_echeances_mandats
"$VENV/bin/python" manage.py fin_des_sanctions
"$VENV/bin/python" manage.py rappel_cotisations
