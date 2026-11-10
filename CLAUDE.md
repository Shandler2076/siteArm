# Contexte du projet — site de gestion des membres de l'Armée du Salut (Bénin)

Site Django en français pour gérer les membres : matricules, parcours, bureaux, mutations,
sanctions, puis grades, événements, communication et médias (modules 2 à 5).

## Documents de référence
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
- PDF : ReportLab + polices DejaVu embarquées (`static/fonts/`) ; `dessiner_fiche` pour les PDF multi-fiches.
- Lots Excel (`apps/lots`) : AUCUNE création de membre avant `valider_lot` (tout ou rien) ; validation
  des lignes par `apps/membres/forms.py::valider_futur_membre` (mêmes règles que l'individuel).

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
