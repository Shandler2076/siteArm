# Guide de maintenance

Ce guide explique, pas à pas, comment faire tourner et entretenir le site. Il sera complété à
chaque étape.

## 1. Installer le projet sur votre ordinateur

Prérequis : Python 3.12 ou plus récent, et Git.

```bash
git clone https://github.com/shandler2076/siteArm.git
cd siteArm
python3 -m venv .venv
source .venv/bin/activate          # Windows : .venv\Scripts\activate
pip install -r requirements-dev.txt
cp .env.exemple .env               # puis ouvrez .env et adaptez si besoin
```

Pour que les commandes lisent `.env`, chargez-le dans le terminal :
`set -a; source .env; set +a` (Linux/Mac). Sous Windows, définissez au moins
`DJANGO_DEBUG=True` dans le terminal.

## 2. Préparer la base de données et le territoire

```bash
python manage.py migrate
python manage.py charger_territoire
```

La commande affiche le nombre de régions, circuits et paroisses créés. La relancer ne crée
aucun doublon.

## 3. Créer le compte technique (administrateur)

```bash
python manage.py createsuperuser
```

Choisissez un identifiant (ex. `tech`) et un mot de passe solide. Ce compte donne accès à la
gestion : `http://127.0.0.1:8000/gestion/`. Les identifiants sont enregistrés en majuscules
(`TECH`), mais la connexion accepte aussi les minuscules et les espaces autour.

Mot de passe du compte technique oublié : `python manage.py changepassword TECH`.

## 4. Lancer le site

```bash
python manage.py runserver
```

Ouvrez `http://127.0.0.1:8000/` dans le navigateur.

## 5. Lancer les tests

```bash
pytest -q
ruff check .
```

Tous les tests doivent être verts (« passed »). Sur GitHub, les mêmes tests se lancent à chaque
envoi (onglet **Actions**).

## 6. Si les tests sont rouges sur GitHub

1. Ouvrez l'onglet **Actions** du dépôt et cliquez sur l'exécution en échec.
2. Copiez le message d'erreur.
3. Donnez-le à l'assistant IA avec la phrase : « Les tests échouent sur GitHub, voici l'erreur ».
4. Ne mettez **jamais** en ligne une version dont les tests sont rouges.

## 7. Fermer ou rouvrir une région, un circuit ou une paroisse

Dans la gestion (`/gestion/`), cochez les éléments, choisissez l'action « Fermer la sélection »
(ou « Rouvrir ») puis « Envoyer ». La suppression est impossible, c'est voulu : l'historique des
membres doit rester vrai.

## 8. Variables d'environnement en production

| Variable | Rôle |
|---|---|
| `DJANGO_SECRET_KEY` | Clé secrète longue et aléatoire (obligatoire) |
| `DJANGO_DEBUG` | `False` en production |
| `DJANGO_ALLOWED_HOSTS` | Nom(s) de domaine, ex. `armeedusalut.bj` |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | Adresse(s) complète(s), ex. `https://armeedusalut.bj` |
| `DATABASE_URL` | Fournie par l'hébergeur (PostgreSQL) |

Générer une clé secrète :
`python -c "from django.core.management.utils import get_random_secret_key as g; print(g())"`

## 9. Mettre le site à jour en production

L'hébergeur (choix à venir) installe automatiquement la nouvelle version envoyée sur la branche de
production, puis applique les migrations (`Procfile` : `postdeploy`). Procédure détaillée ajoutée
lors du choix de l'hébergeur.

## 10. Donner les droits du Bureau national à un compte (en attendant l'étape 3)

Jusqu'à l'arrivée des mandats (étape 3), les droits du BN passent par deux autorisations :

1. Ouvrez la gestion : `/gestion/` → **Comptes** → choisissez le compte (ex. celui du Secrétaire national).
2. Dans **Droits** → *Permissions de l'utilisateur*, ajoutez :
   - **membres | membre | Gérer les membres (Bureau national)** : enregistrer des membres, imprimer
     les fiches, valider les photos ;
   - **membres | membre | Voir la photo du CIP** : consulter la photo du CIP.
3. Enregistrez. La page d'accueil du compte affiche alors « Enregistrer un membre » et
   « Photos à valider ».

À l'étape 3, ces droits seront donnés automatiquement aux titulaires des fonctions concernées.

## 11. Fichiers privés (photos, CIP)

Les photos d'identité et les photos du CIP sont rangées dans le dossier `prive/` (réglage
`PRIVATE_MEDIA_ROOT`). Ce dossier **n'est jamais envoyé sur GitHub** (il est dans `.gitignore`) et
n'a aucune adresse publique : chaque fichier est servi par le site après vérification des droits.
**Il doit être sauvegardé** avec la base de données. En production, il sera remplacé par un
stockage objet privé chez l'hébergeur (étape de mise en ligne).

## 12. Adresse du site imprimée sur les fiches

La variable `DJANGO_SITE_URL` (ex. `https://armeedusalut.bj`) est imprimée dans l'encadré
« Vos identifiants de connexion » des fiches d'identification.

## 13. Matricules

- Format `AAAA-RRAS-NNNN` (ex. `2015-01AS-0157`), un compteur par année d'intégration et par
  région d'intégration (gestion → **Membres** → *Compteurs de matricules*, en lecture seule).
- Un membre ne s'ajoute **que** par la page « Enregistrer un membre » : c'est elle qui garantit un
  matricule unique, même si deux personnes enregistrent en même temps.
