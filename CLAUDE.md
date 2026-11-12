# Contexte du projet — site de gestion des membres de l'Armée du Salut (Bénin)

Site Django en français pour gérer les membres : matricules, parcours, bureaux, mutations,
sanctions, puis grades, événements, communication et médias (modules 2 à 5).

## Mainteneur
- **KOUDAKPO Thoovi Marc Aurel** — mainteneur du site, pour le Bureau National de Commandement
  (BNC). C'est sous ce nom que les documents sont établis (cahier des charges, guides).

## Documents de référence
- Cahier des charges général (v2.4, modules 1 à 5 ; module 2 = grades + cotisations mensuelles
  détaillé § 15-16, décisions du BNC § 15.8 / 16.9 ; nom affiché « Grade Prénoms NOM » ; grade par défaut « Camarade ») : `docs/cahier-des-charges.md` (+ PDF)
- Cahier des charges du module 1 : `docs/superpowers/specs/2026-11-09-module1-fondations-design.md`
  (version PDF : `docs/cahier-des-charges-module1.pdf`)
- Plans de réalisation : `docs/superpowers/plans/`
- Territoire (provisoire, version définitive attendue après le 25/12/2026) :
  `docs/donnees/regions-circuits-paroisses.md` → `apps/organisation/data/territoire_provisoire.json`

## Règles métier à ne jamais casser
- Matricule `AAAA-RRAS-NNNN` (ex. `2015-01AS-0157`) : année d'intégration, code région 2 chiffres,
  « AS » fixe, numéro d'ordre par (année, région). Définitif, généré dans une opération verrouillée.
- Code de région : 2 chiffres, jamais réattribué. On ne supprime jamais région/circuit/paroisse :
  on les ferme (`fermer()` / `rouvrir()`).
- Pas d'inscription libre : les membres sont enregistrés par le Bureau national.
- Droits par mandat (fonction + unité + dates) ; un « gardien des périmètres » central (étape 3)
  filtre toutes les données. Un membre simple ne voit jamais un autre membre.
- Photo du CIP : visible par le BN uniquement. Validation des photos : BN uniquement.
- Sanctions : seul le BNC les inscrit sur le site (procédures locales hors site). Statuts : Actif,
  Sanctionné, Exclu, Démissionnaire, Décédé. Catégorie (actif / d'honneur / sympathisant) sans
  effet sur le matricule. Fonctions et durées de mandat : règlement intérieur (`docs/donnees/`).

## Points techniques
- Matricule : `apps/membres/services.py::attribuer_matricule` (verrou `select_for_update`, à appeler
  dans une transaction) ; enregistrement : `enregistrer_membre` (tout ou rien).
- Fichiers sensibles : `stockage_prive` (`PRIVATE_MEDIA_ROOT`, dossier `prive/`), servis uniquement
  par `apps/membres/views_fichiers.py` (404 si pas le droit).
- Gardien des périmètres : `apps/bureaux/perimetre.py` est le SEUL endroit qui décide qui voit
  quels membres (unites_gerees, membres_visibles, unite_depuis_cle…). Toute nouvelle vue passe par lui.
- Droits BNC : `apps/bureaux/backends.py::MandatBackend` traduit un mandat national de gestion en
  permissions `membres.gerer_membres` / `membres.voir_cip` (vérifier avec `has_perm`).
- Notifications : `apps/notifications/services.py::notifier` / `notifier_unite`.
- Journal : `apps/journal/services.py::journaliser(par, action, unite="", **details)` ; toute
  action sensible y est inscrite (constantes dans `apps/journal/models.py`).
- Listes et statistiques (`apps/listes`) : filtres en base (`membres_filtres`), âge au jour près
  (`ages.py` : « plus de 40 » = 41 ans et plus), chaque chiffre de statistique = nombre de lignes de
  la liste qu'il ouvre (mêmes filtres). Jamais de NPI ni de photo du CIP dans une liste.
- Mouvements (`apps/mouvements`) : mutations (demande paroisse d'arrivée → avis circuit/région de
  départ → décision BN), signalements (décès, démission, réhabilitation, catégorie → décision BN).
  `statuts.py::changer_statut` / `changer_categorie` sont les SEULS points d'entrée des statuts et
  catégories (historique + compte + mandats). Décisions atomiques avec revérification.
- Sanctions (`apps/mouvements/sanctions.py`) : BNC seulement ; statut via `changer_statut` ;
  fin automatique par la commande quotidienne `fin_des_sanctions` ; une sanction se lève, ne se
  supprime pas. Correction exceptionnelle : `apps/membres/services.py::corriger_integration`.
- Journal immuable (`JournalImmuable`) ; page BN `/journal/`.
- Grades (`apps/membres/grades.py` : Camarade = 0, puis 12 grades RI ; `apps/grades`) : `services.py`
  est le SEUL point d'entrée (promouvoir, promouvoir_en_serie, corriger_grade, attribuer_grade_initial ;
  durées art. 78, nomination ≥ Commandant, exceptionnelle art. 84). Nom affiché `nom_complet` =
  « Grade Prénoms NOM ». Démo : `reinitialiser_demo --oui` (PostgreSQL).
- Cotisations (`apps/cotisations`) : `services.py` SEUL point d'écriture (saisie paroisse, validation
  circuit, refus, annulation, parts reçues, réglages BN) ; `regles.py` (mois dus, `situations`) ; accès
  `perimetre.unites_cotisations` (gestion + trésoriers) ; rien sur la fiche membre (état + reçu PDF à part).
- Journal lisible : `apps/journal/lecture.py` (une phrase par action ; toute nouvelle action y est ajoutée).
- Double vérification BN (`apps/securite`) : TOTP, intergiciel `DoubleVerificationObligatoire` ;
  désactivée dans les tests par `conftest.py` racine (sauf `apps/securite/tests`).
- PDF : ReportLab + polices DejaVu embarquées (`static/fonts/`) ; `dessiner_fiche` pour les PDF multi-fiches.
- Lots Excel (`apps/lots`) : AUCUNE création de membre avant `valider_lot` (tout ou rien) ; validation
  des lignes par `apps/membres/forms.py::valider_futur_membre` (mêmes règles que l'individuel).

## Hébergement
- Comparatif : `docs/hebergement/comparatif-hebergement.md` ; site d'essai chez alwaysdata (offre
  gratuite) : `docs/guide-alwaysdata.md` + scripts `deploiement/alwaysdata/` (installer, mettre à
  jour, tâches quotidiennes). Réglages lus aussi depuis `.env` (`config/env.py`, l'environnement a
  priorité). Site d'essai : `DJANGO_SITE_DEMO=True` (bandeau + `peupler_demo`, données FICTIVES).
- Sauvegarde complète chiffrée (code en git bundle, dumpdata + pg_dump, fichiers privés, .env ; gpg
  AES-256) : `deploiement/alwaysdata/sauvegarder.sh` ; restauration : `docs/guide-maintenance.md` § 20.
- Récapitulatif de tout le projet : `docs/recapitulatif-du-projet.md` (+ PDF), à tenir à jour.

## Protection des données (APDP)
- Dossier de demande d'autorisation (traitement + transfert hors Bénin, art. 391) :
  `docs/apdp/dossier-apdp.md` (+ PDF). Page publique `/protection-des-donnees/`
  (`templates/protection_donnees.html`, contact `DJANGO_CONTACT_DONNEES`). Toute nouvelle donnée
  ou finalité doit y être reportée.

## Commandes
- Tests : `DJANGO_DEBUG=True pytest -q`
- Style : `ruff check .`
- Migrations : `DJANGO_DEBUG=True python manage.py makemigrations` puis `migrate`
- Charger le territoire : `python manage.py charger_territoire`

## Conventions
- Tout texte visible est en français. Code et noms métier en français.
- TDD : test d'abord, le voir échouer, puis le code. Rien en production sans tests verts.
- Secrets uniquement en variables d'environnement (voir `.env.exemple`).
- Le mainteneur décide : toute modification passe par sa relecture avant mise en ligne.
