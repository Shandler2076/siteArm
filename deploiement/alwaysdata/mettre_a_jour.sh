#!/usr/bin/env bash
# Met le site à jour avec la dernière version de GitHub (branche main).
# Usage : bash ~/siteArm/deploiement/alwaysdata/mettre_a_jour.sh
set -euo pipefail
DOSSIER="$(cd "$(dirname "$0")/../.." && pwd)"
VENV="${VENV:-$HOME/venv-siteArm}"
cd "$DOSSIER"
git pull --ff-only origin main
"$VENV/bin/pip" install --quiet -r requirements.txt
"$VENV/bin/python" manage.py migrate --noinput
"$VENV/bin/python" manage.py collectstatic --noinput --verbosity 0
chmod +x deploiement/alwaysdata/*.sh
echo "Mise à jour terminée. Redémarrez le site : administration > Web > Sites > bouton « Redémarrer »."
