#!/usr/bin/env bash
# Sauvegarde complète et chiffrée du site, à copier ensuite sur une clé USB ou un disque dur.
# Usage : bash ~/siteArm/deploiement/alwaysdata/sauvegarder.sh
#
# L'archive contient :
#   - code/siteArm.bundle    : tout le code et tout son historique (git bundle) ;
#   - base/donnees.json      : toutes les données, lisibles par n'importe quelle base (dumpdata) ;
#   - base/postgresql.dump   : copie exacte de la base PostgreSQL (si le site utilise PostgreSQL) ;
#   - fichiers/prive/        : photos d'identité, photos du CIP, fichiers des lots ;
#   - reglages/.env          : réglages secrets du site (clé secrète, mot de passe de la base).
# Elle est chiffrée (AES-256) avec une phrase de passe que vous choisissez : sans elle, personne ne
# peut l'ouvrir — vous non plus. Notez-la sur papier et rangez-la à part de la clé USB.
set -euo pipefail

DOSSIER="$(cd "$(dirname "$0")/../.." && pwd)"
VENV="${VENV:-$HOME/venv-siteArm}"
PYTHON="${PYTHON:-$VENV/bin/python}"
DESTINATION="${DESTINATION:-$HOME/sauvegardes}"
MOI="${USER:-$(id -un)}"
DATE="$(date +%Y-%m-%d_%Hh%M)"
NOM="siteArm-sauvegarde-$DATE"
cd "$DOSSIER"

command -v gpg >/dev/null || { echo "Erreur : gpg est introuvable sur ce serveur."; exit 1; }

TRAVAIL="$(mktemp -d)"
trap 'rm -rf "$TRAVAIL"' EXIT
umask 077
mkdir -p "$TRAVAIL/$NOM"/{code,base,fichiers,reglages} "$DESTINATION"
CIBLE="$TRAVAIL/$NOM"

echo "== 1/5 Code et historique"
git bundle create "$CIBLE/code/siteArm.bundle" --all --quiet
git log -1 --format='Dernière version : %h du %cd — %s' --date=format:'%d/%m/%Y %H:%M' \
    > "$CIBLE/code/version.txt"

echo "== 2/5 Données (format universel)"
"$PYTHON" manage.py dumpdata --natural-foreign --exclude contenttypes \
    --exclude auth.permission --exclude admin.logentry --exclude sessions \
    --indent 1 --output "$CIBLE/base/donnees.json"

echo "== 3/5 Base PostgreSQL"
URL="$(grep -E '^DATABASE_URL=' .env 2>/dev/null | head -1 | cut -d= -f2- || true)"
URL="${DATABASE_URL:-$URL}"
case "$URL" in
    postgres://*|postgresql://*)
        # Le mot de passe passe par un fichier PGPASSFILE privé, jamais par la ligne de commande
        # (visible des autres processus du serveur).
        export PGPASSFILE="$TRAVAIL/pgpass"
        # L'adresse (avec le mot de passe) passe par l'environnement, pas par les arguments.
        URL_BASE="$URL" "$PYTHON" - "$PGPASSFILE" > "$TRAVAIL/pgargs" <<'PY'
import os
import sys
import urllib.parse as u

p = u.urlsplit(os.environ["URL_BASE"])
def esc(s):
    return (s or "").replace("\\", "\\\\").replace(":", "\\:")
hote, port = p.hostname or "localhost", str(p.port or 5432)
base, user = u.unquote(p.path.lstrip("/")), u.unquote(p.username or "")
with open(sys.argv[1], "w") as f:
    f.write(":".join(esc(x) for x in (hote, port, base, user, u.unquote(p.password or ""))) + "\n")
print(hote, port, user, base, sep="\n")
PY
        chmod 600 "$PGPASSFILE"
        mapfile -t PG < "$TRAVAIL/pgargs"
        pg_dump --format=custom --no-owner --file "$CIBLE/base/postgresql.dump" \
            --host "${PG[0]}" --port "${PG[1]}" --username "${PG[2]}" --dbname "${PG[3]}" \
            --no-password
        echo "   copie PostgreSQL faite." ;;
    *)
        echo "   le site n'utilise pas PostgreSQL : le format universel suffit." ;;
esac

echo "== 4/5 Fichiers privés et réglages"
PRIVE="$(grep -E '^DJANGO_PRIVATE_MEDIA_ROOT=' .env 2>/dev/null | head -1 | cut -d= -f2- || true)"
PRIVE="${DJANGO_PRIVATE_MEDIA_ROOT:-$PRIVE}"
if [ -n "$PRIVE" ] && [ -d "$PRIVE" ]; then
    cp -a "$PRIVE" "$CIBLE/fichiers/prive"
else
    echo "   aucun dossier privé trouvé."
fi
[ -f .env ] && cp .env "$CIBLE/reglages/.env"
cat > "$CIBLE/LISEZMOI.txt" <<FIN
Sauvegarde du site de l'Armée du Salut du Bénin — $DATE
Restauration : voir docs/guide-maintenance.md, section « Sauvegarde sur clé USB et restauration ».
Pour retrouver le code : git clone code/siteArm.bundle siteArm
FIN

echo "== 5/5 Chiffrement"
if [ -z "${PHRASE:-}" ]; then
    echo "   Choisissez une phrase de passe longue (au moins 4 mots). Rien ne s'affiche : c'est normal."
    read -r -s -p "   Phrase de passe : " PHRASE; echo
    read -r -s -p "   Encore une fois : " PHRASE2; echo
    [ "$PHRASE" = "$PHRASE2" ] || { echo "Les deux saisies diffèrent : recommencez."; exit 1; }
fi
[ "${#PHRASE}" -ge 12 ] || { echo "Phrase de passe trop courte (12 caractères au moins)."; exit 1; }
tar -C "$TRAVAIL" -czf - "$NOM" \
    | gpg --batch --yes --symmetric --cipher-algo AES256 --pinentry-mode loopback \
          --passphrase-fd 3 --output "$DESTINATION/$NOM.tar.gz.gpg" 3<<<"$PHRASE"
chmod 600 "$DESTINATION/$NOM.tar.gz.gpg"

# Rotation : on garde les GARDER dernières sauvegardes (10 par défaut) dans ce dossier.
GARDER="${GARDER:-10}"
ls -1t "$DESTINATION"/siteArm-sauvegarde-*.tar.gz.gpg 2>/dev/null | tail -n +"$((GARDER + 1))" \
    | while read -r ANCIENNE; do rm -f -- "$ANCIENNE"; echo "   ancienne sauvegarde effacée : $ANCIENNE"; done

TAILLE="$(du -h "$DESTINATION/$NOM.tar.gz.gpg" | cut -f1)"
echo
echo "Sauvegarde terminée : $DESTINATION/$NOM.tar.gz.gpg ($TAILLE)"
echo "Pour la copier sur votre ordinateur (PowerShell ou Terminal), puis sur la clé USB :"
echo "   scp $MOI@ssh-$MOI.alwaysdata.net:${DESTINATION#"$HOME"/}/$NOM.tar.gz.gpg ."
