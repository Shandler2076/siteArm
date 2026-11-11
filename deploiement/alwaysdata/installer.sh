#!/usr/bin/env bash
# Installation du site chez alwaysdata (à lancer UNE fois, dans la console SSH).
# Usage : bash ~/siteArm/deploiement/alwaysdata/installer.sh
# Peut être relancé sans risque : il ne remplace pas un fichier .env existant.
set -euo pipefail

DOSSIER="$(cd "$(dirname "$0")/../.." && pwd)"
VENV="${VENV:-$HOME/venv-siteArm}"
PRIVE="${PRIVE:-$HOME/prive-siteArm}"
cd "$DOSSIER"

echo "== 1/6 Environnement Python ($VENV)"
if [ ! -x "$VENV/bin/python" ]; then
    python3 -m venv "$VENV"
fi
"$VENV/bin/pip" install --quiet --upgrade pip
"$VENV/bin/pip" install --quiet -r requirements.txt

echo "== 2/6 Réglages (.env)"
if [ -f .env ]; then
    echo "   .env existe déjà : conservé."
else
    COMPTE="${COMPTE:-}"
    if [ -z "$COMPTE" ]; then
        read -r -p "   Nom de votre compte alwaysdata [$USER] : " COMPTE
        COMPTE="${COMPTE:-$USER}"
    fi
    ADRESSE="${ADRESSE:-$COMPTE.alwaysdata.net}"
    if [ -z "${DATABASE_URL:-}" ]; then
        echo "   Base PostgreSQL créée dans l'administration (laisser vide pour utiliser SQLite) :"
        read -r -p "   Nom de la base (ex. ${COMPTE}_site) : " BASE
        if [ -n "$BASE" ]; then
            read -r -p "   Utilisateur PostgreSQL [$COMPTE] : " UTILISATEUR
            UTILISATEUR="${UTILISATEUR:-$COMPTE}"
            read -r -s -p "   Mot de passe de cet utilisateur : " MDP_BASE; echo
            HOTE="postgresql-$COMPTE.alwaysdata.net"
            MDP_ENC="$("$VENV/bin/python" -c 'import sys,urllib.parse;print(urllib.parse.quote(sys.argv[1],safe=""))' "$MDP_BASE")"
            DATABASE_URL="postgres://$UTILISATEUR:$MDP_ENC@$HOTE:5432/$BASE"
        else
            mkdir -p "$HOME/donnees-siteArm"
            DATABASE_URL="sqlite:///$HOME/donnees-siteArm/site.sqlite3"
        fi
    fi
    CLE="$("$VENV/bin/python" -c 'import secrets;print(secrets.token_urlsafe(50))')"
    umask 077
    cat > .env <<FIN
# Réglages du site — NE JAMAIS envoyer ce fichier sur GitHub ni le partager.
DJANGO_DEBUG=False
DJANGO_SECRET_KEY=$CLE
DJANGO_ALLOWED_HOSTS=$ADRESSE
DJANGO_CSRF_TRUSTED_ORIGINS=https://$ADRESSE
DJANGO_SITE_URL=https://$ADRESSE
DATABASE_URL=$DATABASE_URL
DJANGO_PRIVATE_MEDIA_ROOT=$PRIVE
DJANGO_SITE_DEMO=${SITE_DEMO:-True}
DJANGO_DOUBLE_VERIFICATION_BN=True
DJANGO_SECURE_SSL_REDIRECT=True
DJANGO_DEFAULT_FROM_EMAIL=Armée du Salut <noreply@$ADRESSE>
FIN
    chmod 600 .env
    echo "   .env créé pour https://$ADRESSE"
fi

echo "== 3/6 Dossier privé des photos ($PRIVE)"
mkdir -p "$PRIVE"
chmod 700 "$PRIVE"

echo "== 4/6 Base de données"
"$VENV/bin/python" manage.py migrate --noinput

echo "== 5/6 Fichiers statiques"
"$VENV/bin/python" manage.py collectstatic --noinput --verbosity 0

echo "== 6/6 Territoire (régions, circuits, paroisses)"
"$VENV/bin/python" manage.py charger_territoire

chmod +x deploiement/alwaysdata/*.sh
echo
echo "Installation terminée. Suite du guide : créer le site (Web > Sites), puis le compte technique :"
echo "   $VENV/bin/python manage.py createsuperuser"
