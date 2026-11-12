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
python manage.py fin_des_sanctions
```

La seconde commande applique les sanctions datées dans le futur le jour de leur début et remet
« Actif » les membres dont la sanction temporaire est arrivée à sa date de fin.

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

## 18. Mouvements : mutations, décès, démission, réhabilitation, catégorie

- Code : `apps/mouvements`. Toute la logique est dans `services.py` ; les pages ne font que
  vérifier les droits puis appeler ces fonctions.
- **Seul point d'entrée des statuts et catégories** : `apps/mouvements/statuts.py`
  (`changer_statut`, `changer_categorie`). Chaque changement est inscrit dans l'historique du membre
  (bloc « Historique » des fiches) ; le compte est désactivé pour Décédé, Démissionnaire et Exclu,
  réactivé pour Actif. Ne jamais changer `membre.statut` directement (sauf correction technique).
- **Mutation** : demandée par la paroisse d'arrivée (onglet « Demandes » → « Demander une
  mutation »), avis du circuit puis de la région de départ (une fois chacun), décision du BN
  (« Décisions à prendre » sur l'accueil), même si un avis manque. À la validation : parcours mis à
  jour, mandats clos dans les unités quittées, notifications. Une seule mutation en cours par membre.
- **Décès / démission** : signalés depuis la fiche du membre (bureau de paroisse ou BN), confirmés
  par le BN. Une mutation en cours est annulée ; les mandats en cours sont clos.
- **Réhabilitation** : démissionnaire ou exclu, au plus tôt 6 mois (mois calendaires) après la date
  inscrite dans l'historique ; engagement de bonne conduite obligatoire pour un exclu ; jamais pour un
  membre exclu à nouveau après une réhabilitation (RI art. 172). La validation par le BN télécharge
  la fiche avec un nouveau mot de passe provisoire.
- **Date de démission ou d'exclusion inconnue** (statut posé avant l'étape 6) : la réhabilitation est
  bloquée. Pour régulariser, le mainteneur crée l'événement manquant dans un shell Django :
  `changer_statut(membre, membre.statut, par=None, date_effet=<date réelle>, motif="Régularisation")`
  (le statut ne change pas, seule la date est inscrite).
- **Changement de catégorie** : signalé par la paroisse, le circuit ou la région, validé par le BN.
- Tout est inscrit au journal (`mutation_demandee`, `mutation_avis`, `mutation_decidee`,
  `signalement`, `signalement_decide`).

## 19. Sanctions, journal, double vérification, correction exceptionnelle

### Sanctions
- Seul le BNC inscrit une sanction : fiche BN du membre → « Inscrire une sanction » (degré, type,
  dates, motif résumé, référence de la décision). Code : `apps/mouvements/sanctions.py`.
- Effets : suspension (15 jours au plus) ou retrait temporaire de responsabilités → « Sanctionné » ;
  exclusion temporaire ou définitive → « Exclu », compte désactivé, mandats clos, mutation en cours
  annulée ; avertissements, amende, blâme, « autre » → inscrits sans changer le statut.
- Retour automatique à « Actif » à la date de fin (commande quotidienne `fin_des_sanctions`, §14),
  sauf si une autre sanction en cours justifie encore le statut.
- Une sanction ne se supprime jamais : en cas d'erreur, le BN la **lève** (bouton « Lever » sur la
  fiche BN, motif obligatoire) ; c'est inscrit dans l'historique et au journal.
- La fin d'une exclusion temporaire n'est pas une réhabilitation (art. 172 : seul un membre
  réhabilité par décision du BN puis exclu à nouveau ne peut plus être réhabilité).

### Journal
- Page « Journal » de l'accueil du BN (`/journal/`) : filtres par action, auteur, texte, dates.
- Le journal ne peut être ni modifié ni effacé, même depuis l'administration ou le code
  (`JournalImmuable`). Sont inscrits : connexions (réussies et échouées), consultations de fiches,
  coordonnées modifiées (ancienne et nouvelle valeur), réinitialisations, décisions sur les photos,
  enregistrements, lots, installations de bureau, listes et statistiques téléchargées, mutations,
  signalements, sanctions, corrections exceptionnelles, double vérification.

### Double vérification (comptes du BN)
- Obligatoire pour tout compte ayant un mandat national (et le compte technique) : à la première
  connexion, la personne enregistre le site dans une application d'authentification (Google
  Authenticator, Microsoft Authenticator…) en scannant un QR code ; ensuite un code à 6 chiffres est
  demandé à chaque connexion. Un code ne sert qu'une fois ; 5 codes faux ferment la session.
- **Téléphone perdu** : après vérification de l'identité de la personne, le mainteneur lance
  `python manage.py reinitialiser_double_verification <matricule>` ; la personne refait l'activation
  à sa prochaine connexion. Inscrit au journal.
- Réglage `DJANGO_DOUBLE_VERIFICATION_BN` (laisser `True` en production ; les tests le désactivent
  sauf ceux de `apps/securite`).

### Correction exceptionnelle des données d'intégration
- Fiche BN → « Correction exceptionnelle (intégration) » : année, paroisse d'intégration, motif
  obligatoire.
- Si l'année ou la région change : nouveau matricule (compteur de la nouvelle année/région), le
  membre se connecte désormais avec ce nouveau matricule (il est notifié) ; l'ancien reste dans
  l'historique. Si le membre n'a jamais été muté, son affectation d'intégration est corrigée aussi.

## 20. Sauvegarde sur clé USB et restauration

### Faire une sauvegarde (chez alwaysdata)

Dans la console SSH :

```bash
bash ~/siteArm/deploiement/alwaysdata/sauvegarder.sh
```

Le script demande deux fois une **phrase de passe** (12 caractères au moins ; par exemple quatre mots
sans rapport entre eux). Il crée dans `~/sauvegardes/` un fichier unique et **chiffré** (AES-256)
`siteArm-sauvegarde-AAAA-MM-JJ_HHhMM.tar.gz.gpg`, qui contient :

| Dossier | Contenu |
|---|---|
| `code/` | tout le code et tout son historique (`siteArm.bundle`) et la version sauvegardée |
| `base/` | toutes les données : `donnees.json` (lisible par toute base) et, si le site utilise PostgreSQL, `postgresql.dump` (copie exacte) |
| `fichiers/prive/` | photos d'identité, photos du CIP, fichiers des lots |
| `reglages/.env` | réglages secrets du site |

> **La phrase de passe ne peut pas être retrouvée.** Écrivez-la sur papier et rangez-la **à part**
> de la clé USB (par exemple sous enveloppe au BNC). Sans elle, la sauvegarde est illisible — c'est ce
> qui la protège si la clé est perdue ou volée.

### Copier la sauvegarde sur l'ordinateur, puis sur la clé USB

Sur l'ordinateur, ouvrez PowerShell (Windows) ou Terminal (Mac, Linux) et collez la commande `scp`
affichée à la fin du script (le mot de passe SSH est demandé). Le fichier arrive dans le dossier
courant ; copiez-le sur la clé USB ou le disque dur. Gardez **deux copies** à deux endroits
différents, et refaites une sauvegarde au moins **une fois par mois** et avant toute grosse mise à
jour. Vous pouvez ensuite effacer les anciennes sauvegardes du serveur : `rm ~/sauvegardes/*.gpg`.

### Ouvrir une sauvegarde

- **Windows** : installez **Gpg4win** (gratuit, gpg4win.org), double-cliquez sur le fichier `.gpg`,
  saisissez la phrase de passe ; ouvrez ensuite le `.tar.gz` obtenu avec 7-Zip.
- **Mac / Linux** : `gpg -d siteArm-sauvegarde-….tar.gz.gpg | tar -xzf -`

### Restaurer sur un nouvel ordinateur ou un nouvel hébergement

1. Récupérer le code : `git clone code/siteArm.bundle siteArm` (ou depuis GitHub).
2. Installer le projet (§ 1), puis copier `reglages/.env` dans le dossier `siteArm/` et l'adapter
   (adresse du site, `DATABASE_URL`, `DJANGO_PRIVATE_MEDIA_ROOT`).
3. Créer les tables dans une base **vide** : `python manage.py migrate`.
4. Remettre les données :
   - PostgreSQL, copie exacte : `pg_restore --no-owner --clean --if-exists -d "$DATABASE_URL" base/postgresql.dump`
   - ou n'importe quelle base : `python manage.py loaddata base/donnees.json`
5. Recopier `fichiers/prive/` dans le dossier indiqué par `DJANGO_PRIVATE_MEDIA_ROOT`.
6. Vérifier : se connecter, ouvrir une fiche, une photo, la liste nationale et le journal.

Cette procédure a été essayée le 11 novembre 2026 (sauvegarde, déchiffrement, restauration dans une
base neuve : mêmes nombres de membres et d'entrées du journal).

## 21. Grades (module 2)

- Les grades sont fixés dans `apps/membres/grades.py` : **Camarade** (rang 0, tout nouveau membre),
  puis les 12 grades du règlement intérieur (art. 77), et les durées minimales de l'art. 78.
- Le grade actuel et sa date sont sur la fiche (`Membre.grade`, `Membre.date_grade`) ; l'historique
  est dans `apps/grades` (`HistoriqueGrade`, jamais supprimé).
- **Seul** `apps/grades/services.py` modifie un grade : `promouvoir` (première consécration, test,
  nomination, promotion exceptionnelle), `promouvoir_en_serie` (tout ou rien), `corriger_grade`,
  `attribuer_grade_initial` (à l'enregistrement). Chaque opération est journalisée et notifiée.
- Le nom affiché est « Grade Prénoms NOM » (`Membre.nom_complet`) ; le nom du compte
  (`Compte.nom_affiche`) est tenu à jour par les services des grades.
- Pages du BN : fiche du membre (« Promouvoir », « Corriger le grade ») et menu « Promotions en
  série ». Listes : filtres grade, « à partir de », éligibles ; statistiques par grade et tableaux
  croisés (grade × âge, sexe, unité).
- Fichier Excel des lots : colonnes facultatives « Grade » et « Date du grade » (régularisation des
  membres déjà gradés) ; un ancien fichier sans ces colonnes reste accepté.
- Site d'essai : `python manage.py reinitialiser_demo --oui --base <nom de la base>` recrée les membres fictifs avec grades
  (PostgreSQL seulement ; à refaire ensuite : `createsuperuser`).

## 22. Cotisations mensuelles (module 2)

- Application `apps/cotisations`. **Seul** `services.py` écrit : `saisir_versement`, `saisir_collecte`
  (tout ou rien), `valider` (numéro de reçu `R2026-000123`, parts figées), `refuser`, `annuler`,
  `marquer_part_recue`, `regler`, `rappeler_en_attente`. Calculs dans `regles.py` (`situations`
  en quelques requêtes pour tout un périmètre).
- Réglages du BN (menu « Réglages des cotisations ») : **mois de départ** (rien n'est dû avant ;
  tant qu'il n'est pas fixé, la saisie est fermée) et **tarifs** datés (montant, parts dont le total
  fait 100 %). Par défaut : 100 F, paroisse 30 %, circuit 20 %, région 20 %, national 30 %.
- Accès : gardien des périmètres, `unites_cotisations` (fonctions de gestion **et trésoriers**),
  `peut_voir_cotisations_de` pour les PDF d'un membre.
- Tâche quotidienne : `python manage.py rappel_cotisations` (versements en attente depuis plus de
  30 jours → notification au circuit), ajoutée à `taches_quotidiennes.sh`.
- Pour la **vraie mise en service** : le BN fixe le mois de départ dans les réglages.

## 23. Événements nationaux (module 3)

- Application `apps/evenements`. **Seul** `services.py` écrit : `creer_evenement`,
  `modifier_evenement` (report notifié), `annuler_evenement`, `convoquer` (notification directe du
  Bureau national), `retirer`, `pointer` (présent, absent, excusé).
- Pages du BN : menu « Événements » (création, sessions, convocation par filtres, pointage sur
  téléphone, exports, impression de toutes les autorisations).
- Membre : « Mes événements » et son autorisation PDF (carte 85 × 120 mm, photo, QR code). La
  paroisse du membre peut l'imprimer (`perimetre.peut_imprimer_autorisation`) ; pas le circuit ni la
  région. Les bureaux ne voient pas les événements.
- Le QR code ouvre `/evenements/verifier/<jeton>/` (page publique) : « Autorisation valable » ou
  « Non valable » (convocation retirée, événement annulé, code inconnu). Le jeton est aléatoire.
- Validité de la carte : `Evenement.validite_debut` (vide = début) et `validite_heures` (24 par
  défaut) ; `services.etat_scan` donne valable / pas encore valable / expirée / non valable.
- L'adresse imprimée dans le QR code vient de `DJANGO_SITE_URL` : elle doit être l'adresse réelle du
  site (sinon le scan n'aboutit pas).
