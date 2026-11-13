# Récapitulatif du projet — Site de gestion des membres de l'Armée du Salut du Bénin

---

*État au 12 novembre 2026. Document établi pour KOUDAKPO Thoovi Marc Aurel, mainteneur du
site, pour le Bureau National de Commandement.*

Ce document rassemble **tout ce qu'il faut savoir** sur le site : ce qui est fait, où se trouve chaque
chose, comment le site est construit, comment le sauvegarder et le réinstaller sur un autre ordinateur,
et ce qui reste à faire. Il complète le cahier des charges (le *quoi*) et le guide de maintenance (le
*comment*).

## 1. Le site en une page

| | |
|---|---|
| **But** | Gérer les membres de l'Armée du Salut du Bénin : fiche, matricule, parcours, bureaux, mutations, sanctions, listes et statistiques. |
| **Pour qui** | Bureau National (BNC), bureaux de région, de circuit et de paroisse, et chaque membre. |
| **État** | **Module 1 (Fondations) terminé.** Mise en ligne en cours : site d'essai en ligne avec des données fictives. |
| **Site d'essai** | `https://armeedusalut.alwaysdata.net` (offre gratuite alwaysdata, PostgreSQL). |
| **Code** | Dépôt GitHub privé `Shandler2076/siteArm`, branche `main`. |
| **Langage** | Python 3.12+, Django 5.2, PostgreSQL (SQLite possible pour un essai). |
| **Tests** | 580 tests automatiques, tous verts (SQLite et PostgreSQL) ; relancés par GitHub à chaque modification. |
| **Taille** | Environ 13 300 lignes de code Python (hors migrations), 67 fichiers de tests, 99 versions enregistrées depuis août 2026. |

## 2. Ce qui a été réalisé

### 2.1 Module 1, étape par étape

| Étape | Contenu | État |
|---|---|---|
| 1 | Territoire (13 régions, 87 circuits, 427 paroisses, provisoire), comptes, connexion | Fait |
| 2 | Fiche membre, matricule `AAAA-RRAS-NNNN`, fiche PDF officielle, photo d'identité | Fait |
| 3 | Fonctions et mandats, installation des bureaux, gardien des périmètres, espaces bureau | Fait |
| 4 | Enregistrement par lots (fichier Excel, tout ou rien) | Fait |
| 5 | Listes et statistiques en temps réel (filtres, âge, PDF, Excel), journal | Fait |
| 6 | Mutations, décès, démissions, réhabilitations, changements de catégorie | Fait |
| 7 | Sanctions, journal immuable, double vérification du BN, correction exceptionnelle | Fait |
| 8 | Mise en ligne : comparatif d'hébergement, site d'essai, dossier APDP | **En cours** |

### 2.2 Ajouts de la journée du 11 novembre 2026

- **Page d'accueil publique** (mission, organisation, chiffres du territoire), « Se connecter » dans
  le coin, **filigrane** du logo de l'Armée du Salut sur toutes les pages.
- **PDF** : logo de l'Église à gauche, logo de l'Armée du Salut à droite.
- **Menu de tableau de bord à gauche**, bouton « ← Retour », **fonctions affichées une par ligne**.
- **Double vérification avec un seul téléphone** (bouton qui ouvre l'application, ou « Copier la
  clé »).
- **Page « Protection de vos données »** et **dossier de demande d'autorisation APDP**.
- **Cahier des charges complet** (version 2.0, puis 2.1 et 2.2 avec les grades et les cotisations).
- **Wireframe** des principaux écrans.
- **Sauvegarde chiffrée** sur clé USB, avec procédure de restauration essayée.

## 3. Où se trouve chaque chose

### 3.1 Les documents (dossier `docs/`)

| Document | Fichier |
|---|---|
| Cahier des charges (version à jour) | `docs/cahier-des-charges.md` et `.pdf` |
| Cahier des charges technique du module 1 | `docs/superpowers/specs/2026-11-09-module1-fondations-design.md` (PDF : `docs/cahier-des-charges-module1.pdf`) |
| Plans de réalisation des étapes 1 à 7 | `docs/superpowers/plans/` |
| Guide de maintenance | `docs/guide-maintenance.md` |
| Guide du site d'essai alwaysdata | `docs/guide-alwaysdata.md` et `.pdf` |
| Guide de l'enregistrement par lots | `docs/guide-lots-regions.md` |
| Comparatif d'hébergement | `docs/hebergement/comparatif-hebergement.md` et `.pdf` |
| Dossier APDP | `docs/apdp/dossier-apdp.md` et `.pdf` |
| Règlement intérieur (projet) | `docs/donnees/reglement-interieur.md` |
| Territoire provisoire | `docs/donnees/regions-circuits-paroisses.md` |
| Captures d'écran | `docs/captures/` |
| Ce récapitulatif | `docs/recapitulatif-du-projet.md` et `.pdf` |
| Fichier de contexte pour un assistant technique | `CLAUDE.md` (racine du projet) |

### 3.2 Le code (dossier `apps/`)

Chaque dossier de `apps/` est une partie du site, avec ses propres tests (`tests/`).

| Partie | Rôle | Tables principales |
|---|---|---|
| `organisation` | Régions, circuits, paroisses ; fermeture et réouverture | Region, Circuit, Paroisse |
| `comptes` | Comptes de connexion, page d'accueil, mot de passe, page « Protection de vos données » | Compte |
| `membres` | Fiche (en rubriques), matricule, affectations (dont paroisse actuelle à l'inscription), photos, fiche PDF, correction exceptionnelle | Membre, CompteurMatricule, Affectation, PhotoIdentite |
| `bureaux` | Fonctions, mandats, installation des bureaux, **gardien des périmètres** (`perimetre.py`), **menu** (`menu.py`) | Fonction, Mandat |
| `lots` | Enregistrement par fichier Excel | Lot, LigneLot |
| `listes` | Listes filtrées, statistiques, exports PDF et Excel, tranches d'âge | ReglageStatistiques |
| `mouvements` | Mutations, signalements, statuts, catégories, sanctions | HistoriqueMembre, Mutation, AvisMutation, Signalement, Sanction |
| `notifications` | Notifications internes et e-mails, liens vers la bonne page | Notification |
| `tresorerie` | Mobile money (simulé), cotisations spéciales, quittances, reversements mensuels | NumeroMobileMoney, CotisationSpeciale, Paiement, Contribution, Reversement |
| `journal` | Journal des opérations sensibles, non modifiable | EntreeJournal |
| `securite` | Double vérification (codes à 6 chiffres) | DoubleVerification |

Autres dossiers : `config/` (réglages du site), `templates/` (pages), `static/` (logos, styles, polices
des PDF), `deploiement/alwaysdata/` (scripts d'installation, de mise à jour, de tâches quotidiennes et
de sauvegarde), `.github/workflows/tests.yml` (tests automatiques sur GitHub).

### 3.3 Les commandes utiles

| Commande | Effet |
|---|---|
| `python manage.py charger_territoire` | Charge ou met à jour régions, circuits et paroisses |
| `python manage.py peupler_demo` | Remplit le **site d'essai** de membres fictifs (refusé sur le vrai site) |
| `python manage.py verifier_echeances_mandats` | Avertit des mandats qui arrivent à échéance (tâche quotidienne) |
| `python manage.py fin_des_sanctions` | Applique le début et la fin des sanctions (tâche quotidienne) |
| `python manage.py reinitialiser_double_verification <identifiant>` | Réinitialise la double vérification d'un compte du BN |
| `DJANGO_DEBUG=True pytest -q` | Lance tous les tests |
| `ruff check .` | Vérifie la propreté du code |

Scripts chez alwaysdata : `installer.sh` (une fois), `mettre_a_jour.sh` (après chaque nouvelle
version, puis ⟳ Redémarrer), `taches_quotidiennes.sh` (programmé chaque jour à 6 h),
`sauvegarder.sh` (sauvegarde chiffrée).

## 4. La base de données

La base contient **toutes les données des membres**. Elle est décrite par le code (les « modèles » du
§ 3.2) ; sa structure évolue par des **migrations** (dossiers `migrations/`), appliquées
automatiquement par `mettre_a_jour.sh`.

| Groupe | Ce qui est enregistré |
|---|---|
| Territoire | Régions (code à 2 chiffres, jamais réattribué), circuits, paroisses, avec date de fermeture éventuelle |
| Membres | Identité, coordonnées, NPI, intégration, matricule, catégorie, statut |
| Parcours | Affectations successives (paroisse, dates), historique des statuts, catégories et matricules |
| Bureaux | Fonctions du règlement intérieur, mandats (fonction, unité, dates) |
| Mouvements | Mutations et avis, signalements et décisions, sanctions |
| Sécurité | Comptes (mots de passe chiffrés), double vérification, tentatives de connexion, journal |
| Fichiers | Photos d'identité, photos du CIP, fichiers des lots : **hors de la base**, dans un dossier privé |

Règles que la base garantit elle-même : matricule unique, numérotation verrouillée, journal impossible
à modifier ou à effacer (même directement dans la base).

**Aujourd'hui, la base du site d'essai ne contient que des données fictives** (158 membres créés par
`peupler_demo`). Les vraies données n'y entreront qu'après l'autorisation de l'APDP, dans une **base
neuve**.

## 5. Sécurité, en résumé

- Pas d'inscription libre : seul le BN enregistre les membres.
- Chaque bureau ne voit que son périmètre ; un membre simple ne voit que sa propre fiche.
- Photo du CIP visible par le BN seulement ; photos dans un dossier privé, jamais par un simple lien.
- Mots de passe chiffrés, blocage après plusieurs échecs, double vérification pour le BN.
- Journal de toutes les opérations sensibles, non modifiable.
- Secrets (clé du site, mot de passe de la base) uniquement dans le fichier `.env` du serveur, jamais
  sur GitHub.

## 6. Sauvegarder et changer d'ordinateur

**Rien d'essentiel n'est stocké sur votre ordinateur** : le code est sur GitHub, le site et ses données
chez l'hébergeur. Si l'ordinateur tombe en panne, il suffit d'un autre ordinateur avec un navigateur et
l'accès à GitHub et à alwaysdata.

Pour avoir **en plus une copie complète sur une clé USB ou un disque dur** :

1. Dans la console alwaysdata : `bash ~/siteArm/deploiement/alwaysdata/sauvegarder.sh`.
2. Choisir une **phrase de passe** (notée sur papier, rangée à part de la clé).
3. Copier le fichier créé sur l'ordinateur (commande `scp` affichée), puis sur la clé USB.

Le fichier est **chiffré** : code complet avec son historique, données, photos et réglages. Sans la
phrase de passe, personne ne peut l'ouvrir. Détail et restauration : guide de maintenance, § 20.

À garder aussi, **sur papier ou dans un gestionnaire de mots de passe** (jamais dans un message) :
les accès GitHub, alwaysdata (administration et SSH), la base PostgreSQL, le compte technique du site,
et la phrase de passe des sauvegardes.

## 7. Ce qui reste à faire

| Sujet | Qui | État |
|---|---|---|
| **Grades** (Camarade puis 12 grades, nom « Capitaine Marc Aurel KOUDAKPO », historique, promotions, listes et statistiques croisées, démo avec grades) | Mainteneur | **Réalisé le 12 novembre** (PR #10) ; à essayer sur le site d'essai |
| **Cotisations mensuelles (CM)** (100 F ; paroisse 30 %, circuit 20 %, région 20 %, national 30 % ; saisie paroisse et trésoriers, validation circuit, parts reçues, état et reçu PDF, listes et statistiques) | Mainteneur | **Réalisé le 12 novembre** ; à essayer sur le site d'essai |
| Option « Faire confiance à cet appareil 30 jours » pour la double vérification | BNC | **À décider** |
| Rubriques [à compléter] du dossier APDP, signature, dépôt | BNC | À faire |
| Durées de conservation, puis effacement automatique | BNC, puis mainteneur | À valider |
| Choix de l'hébergeur définitif et du nom de domaine `.bj` | BNC | Après les essais |
| Territoire définitif | Église | Après le 25 décembre 2026 |
| Caractéristiques de la photo en tenue | BNC | À fournir |
| Modification des coordonnées d'un membre par le bureau de sa paroisse ; alerte si le site est inaccessible | Mainteneur | Prévu |
| Vraie mise en ligne (base neuve, `DJANGO_SITE_DEMO=False`, domaine `.bj`, e-mails) | Mainteneur | Après l'autorisation de l'APDP |
| **Événements nationaux** (convocations notifiées, sessions, autorisation avec QR code, pointage, historique) | Mainteneur | **Réalisé le 12 novembre** ; à essayer sur le site d'essai |
| **Corrections du 13 novembre** : menu repliable, paroisse actuelle, identifiants, événements (sections, rôles, formule, recherche), notifications reliées, vérifier un membre, statistiques à paramètres | Mainteneur | **Réalisé le 13 novembre** ; à essayer sur le site d'essai |
| **Trésorerie** : mobile money (plateforme simulée), payer pour un autre, cotisations spéciales, quittances, espace du Trésorier, reversements mensuels | Mainteneur | **Réalisé le 13 novembre** (simulation) ; choix de la plateforme réelle et ouverture du compte : BNC |
| Guides d'utilisation (`docs/guides/`, 11 guides) | Mainteneur | **Rédigés le 13 novembre** ; captures d'écran à ajouter après essai |
| Modules 4 et 5 : communication, médias | — | À concevoir |

## 8. Comment une modification est faite

1. Le besoin est décrit (cahier des charges), puis découpé en tâches (plan).
2. Chaque tâche : **test écrit d'abord**, puis le code, puis tous les tests.
3. Relecture indépendante, puis proposition de modification (« pull request ») sur GitHub, où les tests
   tournent à nouveau.
4. **Le mainteneur relit et fusionne.**
5. Sur alwaysdata : `mettre_a_jour.sh`, puis ⟳ Redémarrer ; essai sur le site d'essai.
