# Guide pas à pas : mettre le site d'essai en ligne chez alwaysdata (offre gratuite)

---

**Durée** : environ 45 minutes la première fois. **Coût** : 0 F (offre « Free » d'alwaysdata).
**Il faut** : un ordinateur (c'est plus confortable qu'un téléphone), une adresse e-mail, et l'accès au
compte GitHub du projet (`Shandler2076/siteArm`).

> **Important — données fictives uniquement.** Tant que la déclaration à l'APDP n'est pas faite,
> on n'enregistre **aucun vrai membre** sur ce site d'essai. Un bandeau jaune le rappelle sur
> chaque page. L'étape 8 du guide remplit le site avec des membres fictifs.
>
> **Ne communiquez jamais un mot de passe** (alwaysdata, GitHub, base de données) dans une
> conversation, un e-mail ou un message WhatsApp.

Dans ce guide, remplacez **COMPTE** par le nom de votre compte alwaysdata (par exemple
`armeedusalut`). Le site aura l'adresse `https://COMPTE.alwaysdata.net`.

## 1. Créer le compte gratuit

1. Allez sur **alwaysdata.com** → « Inscription » (ou « Sign up »).
2. Choisissez l'offre **Free** (gratuite). Aucune carte bancaire n'est demandée.
3. Choisissez le **nom du compte** (COMPTE) : en minuscules, sans espace, par exemple `armeedusalut`.
   Il apparaîtra dans l'adresse du site d'essai.
4. Confirmez votre adresse e-mail (lien reçu par e-mail), puis connectez-vous à l'**administration**
   (admin.alwaysdata.com).

## 2. Choisir la version de Python

Administration → **Environnement** → **Python** : choisissez la version **3.12** (ou plus récente),
puis enregistrez.

## 3. Créer la base de données PostgreSQL

1. Administration → **Bases de données** → **PostgreSQL** → onglet **Utilisateurs** → « Ajouter un
   utilisateur » : nom `COMPTE` (proposé par défaut), un **mot de passe** que vous notez en lieu sûr.
2. Onglet **Bases de données** → « Ajouter une base de données » : nom `COMPTE_site`, et donnez tous
   les droits à l'utilisateur créé juste avant.
3. Notez : le **nom de la base** (`COMPTE_site`), l'**utilisateur** et son **mot de passe**.
   L'adresse du serveur est `postgresql-COMPTE.alwaysdata.net` (le script la remplit tout seul).

> Si PostgreSQL n'est pas proposé dans l'offre gratuite, passez cette étape : le script utilisera
> SQLite (une base dans un simple fichier), largement suffisante pour un essai.

## 4. Ouvrir la console (SSH)

1. Administration → **Accès distant** → **SSH** : vérifiez que l'utilisateur SSH `COMPTE` existe et
   cochez « **Activer la connexion par mot de passe** » ; définissez ce mot de passe.
2. Ouvrez la console :
   - **depuis un ordinateur Windows** : ouvrez « PowerShell » et tapez
     `ssh COMPTE@ssh-COMPTE.alwaysdata.net` ;
   - **depuis un Mac ou Linux** : ouvrez « Terminal » et tapez la même commande ;
   - **depuis un téléphone** : application gratuite **Termius**, nouvel hôte
     `ssh-COMPTE.alwaysdata.net`, utilisateur `COMPTE`.
3. Tapez le mot de passe SSH (rien ne s'affiche pendant la saisie : c'est normal), puis Entrée.

Toutes les commandes suivantes se tapent (ou se collent) dans cette console, **une ligne à la fois**.

## 5. Récupérer le code du site depuis GitHub

Le dépôt GitHub est privé : on donne au serveur une « clé de lecture » (il pourra lire le code, pas
le modifier).

1. Dans la console :
   ```bash
   ssh-keygen -t ed25519 -N "" -f ~/.ssh/id_ed25519
   cat ~/.ssh/id_ed25519.pub
   ```
   La deuxième commande affiche une ligne qui commence par `ssh-ed25519`. Copiez-la **entièrement**.
2. Sur GitHub : dépôt **siteArm** → **Settings** → **Deploy keys** → **Add deploy key** :
   titre `alwaysdata essai`, collez la ligne, **ne cochez pas** « Allow write access » → **Add key**.
3. De retour dans la console :
   ```bash
   cd ~
   git clone git@github.com:Shandler2076/siteArm.git
   ```
   (À la question « Are you sure you want to continue connecting », tapez `yes`.)

## 6. Lancer l'installation

```bash
bash ~/siteArm/deploiement/alwaysdata/installer.sh
```

Le script demande :
- le **nom du compte** (Entrée pour accepter la proposition) ;
- le **nom de la base PostgreSQL** (`COMPTE_site`), l'**utilisateur** et son **mot de passe** —
  ou rien (Entrée) pour utiliser SQLite.

Il installe tout (environ 3 à 5 minutes) : programmes Python, réglages secrets dans un fichier
`.env` protégé, base de données, territoire (13 régions, 87 circuits, 427 paroisses). Il se termine
par « Installation terminée ».

## 7. Créer le site dans l'administration

Administration → **Web** → **Sites** → « **Ajouter un site** » :

| Champ | Valeur |
|---|---|
| Nom | `Site d'essai` |
| Adresses | `COMPTE.alwaysdata.net` |
| Type | **Python WSGI** |
| Chemin de l'application | `/home/COMPTE/siteArm/config/wsgi.py` |
| Répertoire de travail | `/home/COMPTE/siteArm` |
| Répertoire du virtualenv | `/home/COMPTE/venv-siteArm` |
| Version de Python | la même qu'à l'étape 2 |
| Onglet SSL : « Forcer HTTPS » | coché |

Enregistrez. Après une minute, ouvrez `https://COMPTE.alwaysdata.net` : la page de connexion
s'affiche avec le bandeau jaune « Site d'essai ».

## 8. Créer le compte technique et les données fictives

Dans la console :

```bash
cd ~/siteArm
~/venv-siteArm/bin/python manage.py createsuperuser
~/venv-siteArm/bin/python manage.py peupler_demo
```

- La première commande crée **votre compte technique** (identifiant et mot de passe à choisir ;
  l'e-mail peut rester vide).
- La seconde crée environ 150 **membres fictifs** et affiche un tableau de **comptes de
  démonstration** : Président, Secrétaire national, bureau d'une région, d'un circuit, d'une
  paroisse, et un membre simple. **Notez ces identifiants et mots de passe tout de suite** : ils ne
  seront plus affichés.

> Les comptes du Bureau national (et le compte technique) doivent installer une application
> d'authentification sur leur téléphone (Google Authenticator ou Microsoft Authenticator) : le site
> la demande à la première connexion. **Un seul téléphone suffit** : sur le téléphone, touchez
> « Ajouter à mon application d'authentification » (ou « Copier la clé ») ; depuis un ordinateur,
> scannez le QR code avec le téléphone.

## 9. Programmer la tâche quotidienne

Administration → **Avancé** → **Tâches planifiées** → « Ajouter une tâche » :

| Champ | Valeur |
|---|---|
| Type | Exécuter la commande |
| Commande | `/home/COMPTE/siteArm/deploiement/alwaysdata/taches_quotidiennes.sh` |
| Fréquence | tous les jours à **06:00** |

## 10. Que tester ?

| Avec le compte… | Essayez… |
|---|---|
| Secrétaire national | double vérification ; enregistrer un membre ; lots Excel ; « Décisions à prendre » (une mutation et un changement de catégorie attendent) ; inscrire une sanction ; journal ; statistiques nationales |
| Secrétaire régional / de circuit | liste et statistiques de son périmètre ; avis sur une mutation |
| Secrétaire paroissial | fiche d'un membre ; signaler un décès ; demander une mutation ; mot de passe oublié |
| Membre simple | sa fiche, son parcours, sa photo, ses coordonnées ; il ne voit personne d'autre |
| Sur téléphone | tout ce qui précède, en conditions réelles de réseau |

Notez ce qui ne vous convient pas : je corrigerai avant la vraie mise en ligne.

## 11. Mettre à jour le site après une nouvelle version

Quand une nouvelle version est fusionnée sur GitHub :

```bash
bash ~/siteArm/deploiement/alwaysdata/mettre_a_jour.sh
```

puis Administration → **Web** → **Sites** → bouton **Redémarrer** du site.

## 12. En cas de problème

| Symptôme | Solution |
|---|---|
| « Trop de redirections » dans le navigateur | Dans la console : `nano ~/siteArm/.env`, mettez `DJANGO_SECURE_SSL_REDIRECT=False`, enregistrez (Ctrl+O, Entrée, Ctrl+X), puis redémarrez le site. alwaysdata force déjà le HTTPS (étape 7). |
| « Bad Request (400) » | L'adresse du site ne correspond pas à `DJANGO_ALLOWED_HOSTS` dans `~/siteArm/.env`. |
| « Server Error (500) » | Journal des erreurs : Administration → **Web** → **Sites** → **Journaux**, ou dans la console `ls ~/admin/logs/`. Envoyez-moi le message d'erreur (sans mot de passe). |
| Le site est lent ou s'arrête | L'offre gratuite a peu de mémoire (256 Mo) : normal pour un essai ; le pack payant en a davantage. |
| Mot de passe d'un compte de démonstration oublié | Connectez-vous avec le compte technique et réimprimez une fiche avec identifiants depuis la fiche du membre. |

## 13. Après l'essai

- **Si alwaysdata convient** : Administration → **Abonnement** → passer au pack payant (≈ 7 € HT par
  mois). Le site reste où il est.
- **Avant la vraie mise en ligne** (après la déclaration APDP), on repart d'une **base vide** :
  nouvelle base de données, `DJANGO_SITE_DEMO=False` dans `.env`, domaine `.bj`, envoi des e-mails.
  Les membres fictifs ne doivent jamais se mélanger aux vrais. Je vous fournirai la procédure.
