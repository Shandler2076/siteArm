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
`DJANGO_DEBUG=True` dans le terminal. Un email qui échoue n'interrompt jamais le site : l'erreur est inscrite dans les
journaux de l'hébergeur.

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

## 10. Installer le Bureau National de Commandement (première fois)

Depuis l'étape 3, les droits viennent des **mandats** (fonction + unité + dates) :

1. Connectez-vous avec le **compte technique** (`createsuperuser`, §3).
2. Enregistrez d'abord, comme membres, le Président et le Secrétaire national
   (« Enregistrer un membre »).
3. Ouvrez **Installer un bureau** → niveau « Bureau National de Commandement » → saisissez le
   matricule de chaque titulaire et la date de début → « Installer le bureau ».
4. Le Président et le Secrétaire national ont alors toutes les pages du BNC. Ils installent ensuite
   les bureaux des régions, circuits et paroisses de la même façon.

Ce que font les fonctions est réglable dans **Fonctions et droits** (case « droit de gérer »).
Un titulaire qui n'est plus « Actif » (sanctionné, exclu, démissionnaire, décédé) perd
immédiatement ses droits de bureau. Les comptes de bureau sont déconnectés après 30 minutes
d'inactivité.

*Transition :* l'autorisation manuelle « Gérer les membres » (gestion → Comptes → Permissions)
donne encore les pages du BNC. À réserver au démarrage ; préférez les mandats.

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

## 14. Tâche quotidienne : échéances des mandats

Programmez chez l'hébergeur une tâche quotidienne (le matin) :

```bash
python manage.py verifier_echeances_mandats
```

Elle prévient les titulaires, leur bureau et le BNC 60 jours avant la fin d'un mandat, puis quand
un mandat est échu sans renouvellement. Elle ne coupe jamais un mandat : c'est l'installation du
nouveau bureau qui le fait.

## 15. Emails des notifications

Les notifications sont aussi envoyées par email aux membres qui ont une adresse. En production,
renseignez le serveur d'envoi (fournisseur d'emails) avec les variables `DJANGO_EMAIL_HOST`,
`DJANGO_EMAIL_PORT`, `DJANGO_EMAIL_HOST_USER`, `DJANGO_EMAIL_HOST_PASSWORD`,
`DJANGO_EMAIL_USE_TLS`, ainsi que `DJANGO_DEFAULT_FROM_EMAIL`
(ex. `Armée du Salut <noreply@armeedusalut.bj>`). En développement, les emails s'affichent dans le
terminal. Un email qui échoue n'interrompt jamais le site : l'erreur est inscrite dans les
journaux de l'hébergeur.

## 16. Enregistrement par lots (Excel)

Circuit : **région → Secrétaire national → site**.

1. Gestion BNC → « Enregistrer par lots (Excel) » → télécharger le **modèle** de la région et
   l'envoyer à la région avec la fiche `docs/guide-lots-regions.md`.
2. À réception : « Nouveau lot » → choisir la région → déposer le fichier.
3. **Écran de contrôle** : rien n'est encore créé. Corriger une ligne, l'écarter, garder ou
   écarter un doublon possible, ou redéposer un fichier corrigé. Le lot reste en brouillon : on peut
   y revenir plus tard.
4. « Valider et générer » (actif quand il n'y a plus d'erreur ni de doublon à trancher) →
   cocher « Je confirme ». Tout est créé en une fois ; si une ligne échoue, **rien** n'est créé et
   le message indique la ligne.
5. Page de résultat : « Imprimer les fiches avec identifiants » (de nouveaux mots de passe sont
   créés à chaque impression) et « Liste récapitulative » à renvoyer à la région.

Les fichiers déposés sont archivés dans `prive/lots/` (à sauvegarder avec la base).

## 17. Listes et statistiques

- Code : `apps/listes`. Toutes les listes partent de `membres_visibles(unite)` (gardien des
  périmètres) ; les filtres sont appliqués en base (`apps/listes/filtres.py::membres_filtres`).
- **Âge**, calculé au jour près à la date du jour (`apps/listes/ages.py`) :
  « moins de X ans » = âge < X ; « plus de Y ans » = âge > Y (40 ans pile n'est pas « plus de 40 ») ;
  « entre X et Y ans » = bornes incluses. Un membre sans date de naissance n'apparaît que dans
  « Âge non renseigné ».
- **Tranches d'âge** des statistiques : modifiables par le BN (accueil → « Tranches d'âge des
  statistiques », adresse `/bureau/bn/tranches-age/`). On saisit des bornes : « 18, 40 » (par défaut)
  donne moins de 18 / 18 à 40 / plus de 40 ; « 18, 40, 60 » ajoute 41 à 60.
- **Chaque chiffre des statistiques est un lien vers la liste** filtrée correspondante : le nombre
  est calculé avec exactement les mêmes filtres que la liste (`apps/listes/statistiques.py`).
  Un test vérifie cette égalité pour toutes les unités.
- **Exports** : PDF et Excel des listes, PDF des statistiques. La photo du CIP et le NPI ne figurent
  jamais dans une liste. Dans l'Excel, aucun texte n'est interprété comme une formule.
- **Journal** (`apps/journal`, fonction `journaliser`) : chaque téléchargement (liste PDF, liste
  Excel, statistiques PDF) et chaque changement de tranches d'âge y est inscrit (auteur, unité,
  filtres, nombre de lignes). Consultation provisoire : administration technique → Journal.
  La page de consultation du BN viendra à l'étape 7. Le simple affichage à l'écran n'est pas inscrit.
- **Grade** : filtre, colonne et statistique arriveront avec le module 2 (ajouter une entrée dans
  `COLONNES_LISTE`, un champ dans `FiltreListeForm` et une section dans `calculer_statistiques`).
