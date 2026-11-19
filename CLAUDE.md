# Contexte du projet — site de gestion des membres de l'Armée du Salut (Bénin)

Site Django en français pour gérer les membres : matricules, parcours, bureaux, mutations,
sanctions, puis grades, événements, communication et médias (modules 2 à 5).

## Mainteneur
- **KOUDAKPO Thoovi Marc Aurel** — mainteneur du site, pour le Bureau National de Commandement
  (BNC). C'est sous ce nom que les documents sont établis (cahier des charges, guides).

## Documents de référence
- Cahier des charges général (v2.9, modules 1 à 5 ; module 4 : courrier § 18.1 ; module 2 = grades + cotisations mensuelles
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
- Événements nationaux (`apps/evenements`, BN seulement) : `services.py` SEUL point d'écriture ;
  autorisation PDF (QR → `/evenements/verifier/<jeton>/`, public, valable/non valable) ; impression par
  le membre ou sa paroisse (`perimetre.peut_imprimer_autorisation`) ; les bureaux ne voient pas les événements.
- Journal lisible : `apps/journal/lecture.py` (une phrase par action ; toute nouvelle action y est ajoutée).
- Double vérification BN (`apps/securite`) : TOTP, intergiciel `DoubleVerificationObligatoire` ;
  désactivée dans les tests par `conftest.py` racine (sauf `apps/securite/tests`).
- PDF : ReportLab + polices DejaVu embarquées (`static/fonts/`) ; `dessiner_fiche` pour les PDF multi-fiches.
- Lots Excel (`apps/lots`) : AUCUNE création de membre avant `valider_lot` (tout ou rien) ; validation
  des lignes par `apps/membres/forms.py::valider_futur_membre` (mêmes règles que l'individuel).
- Menu : `apps/bureaux/menu.py::construire_menu` (groupes thématiques repliables, rubrique active
  par plus long préfixe d'adresse) ; toute nouvelle page du menu y est ajoutée.
- Paroisse actuelle à l'inscription : `enregistrer_membre(paroisse_actuelle=...)` (affectée dès
  l'inscription sur le site ; lots : colonne facultative). Bienvenue au nouveau membre sans mot de passe.
- Notifications : liens par `notifications/services.py::resoudre_lien` (« membre:<matricule> » selon
  les droits) ; clic = lue (`/notifications/<pk>/`).
- Vérifier un membre hors périmètre : Chef et Secrétaire seulement (`perimetre.unites_verification`),
  matricule exact, motif journalisé, carte réduite (`membres/verification.py`).
- Événements : sections facultatives (`avec_sections`, modèle `Session`), rôle (travailleur,
  superviseur, bureau) et formule de l'autorisation sur la convocation.
- Trésorerie (`apps/tresorerie`, `services.py` SEUL point d'écriture) : paiement mobile money parti du
  site (plateforme simulée sur le site d'essai), cotisations spéciales, quittances, reversements
  mensuels (Trésorier national prépare, Président ou Secrétaire national valide) ; rôles dans
  `perimetre.py` (`tresoriers`, `unites_tresorerie`…). Guides : `docs/guides/`.
- Cotisations spéciales : cibles `pour_membres` (tous/certains/aucun), `membres_des_bureaux`,
  `membres_designes`, critères, `pour_unites` (l'unité paie ensemble) et `pour_bureaux` ; clé de
  payeur `cle_payeur` (« unite:paroisse-3 » / « paroisse-3 ») ; amende = cotisation liée à une
  `Sanction` (`creer_amende`), jamais listée.
- Grades : `eligibles_au_grade` (grade visé), `SessionEpreuve` / `Candidat` (test ou examen),
  `promouvoir_admis`, `promotion_speciale`, `ActePromotion` (PDF `grades/pdf.py`, signature du
  Président, extrait par promu).
- Courrier (`apps/courrier`, `services.py` SEUL point d'écriture) : préparer (Secrétaire/Chef) →
  `valider` par le signataire (`perimetre.qualite_signataire` : Président/Chef, ou Secrétaire P.O.)
  avec SA `SignatureDeposee` (stockage privé, visible de lui seul) ; numéro par bureau et par année
  (`numero_complet`, sigles BNC/UP/SC/BRC) ; réception par les responsables (`unites_courrier`),
  accusés ; transmission d'un communiqué par la paroisse ; le BN ne voit QUE ses courriers
  envoyés ou reçus (pas ceux des autres niveaux ; registre BN = national seulement) ; PDF `courrier/pdf.py` (modèle national,
  QR → `/courrier/verifier/<jeton>/`) ; clavier goun `static/js/clavier-goun.js` (lettres
  `ReglagesClavier` : ẹ ọ ṣ + tons ; mots `MotClavier` : liste BN, lexique goun 6 481 mots
  `courrier/data/lexique_gun.json`, mots appris ; `proposer_mots` via `/courrier/mots/?debut=`).
  Numéro automatique à la signature ; langue fr/goun ; ligne d'adresse (« À Monsieur le … » / « Hlan … ») ;
  5 polices `static/fonts/courrier/` (normal, gras, italique, gras italique) + taille + « une page » ;
  mise en forme `services.mise_en_forme` (***gras italique***, **gras**, *italique*, __souligné__) ;
  aperçu sans enregistrement (`services.apercu`, `/courrier/<cle>/apercu/`) ; nature « autre » + titre ; états : à signer → en correction
  (`mettre_en_correction`, `soumettre_a_la_signature`) → envoyé ; abandonné (`reprendre`, `supprimer`,
  effacé après 30 jours : `purger_courriers_abandonnes`, tâche quotidienne).
- Logos : `LOGO_CONGREGATION_SANS_TEXTE` (triangle + anges, sans texte) là où le nom de la
  Congrégation est déjà écrit (courriers, fiche du membre, accueil) ; l'ancien logo avec le texte en
  arc reste sur les autres PDF (listes, statistiques, autorisations).
- Bureaux (19/11/2026) : alertes d'échéance PAR BUREAU à 30/14/7 jours puis échu
  (`bureaux/services.py::alertes_echeances`, modèle `AlerteBureau`) ; page « Bureaux en place »
  (`views_bn.bureaux_en_place`, composition `bn_bureau`). Cotisations : mois dus depuis janvier de
  l'année d'intégration (`cotisations/regles.py::debut_cotisations`), pas depuis l'inscription.
  Événements : « passés » = tenus (convocations envoyées) ; « non aboutis » à part. Menu : lien
  « Accueil » (`/site/`) et « Ma page » dans Mon espace ; bouton « Voir » sur tout mot de passe (`static/js/site.js`).
- Catégories : exclusives ; pas de signalement « catégorie » ; `statuts.admettre_comme_actif`
  (sympathisant → actif, BNC) et `corriger_categorie` (BN).

- Sécurité (lot du 19/11/2026, `docs/securite/analyse-2026-11-19.md`) : réinitialisation d'un
  titulaire de mandat par le BN seul ; double vérification aussi pour le Trésorier national ;
  paiement simulé interdit sans `SITE_DEMO` (refus au démarrage) ; blocage des connexions par
  identifiant ET par IP (`comptes/securite.py`, `DERRIERE_RELAIS`) ; recherches par matricule
  journalisées et limitées (`journal/recherches.py`) ; envois > `TAILLE_MAX_ENVOI` refusés tôt
  (`securite/envois.py`, + Permissions-Policy) ; Pillow : JPEG/PNG seulement ; versions figées ;
  `/gestion/` en lecture seule hors site d'essai (`securite/admin_lecture.py`,
  `DJANGO_ADMIN_LECTURE_SEULE`) ; journal des coordonnées = noms des champs seulement.

- Style coloré (19/11/2026) : variables CSS en tête de `static/css/site.css` (marine #14284B,
  bordeaux #8E1F35, or #F2C230, fond crème #FBF6EA), Poppins (titres) + Inter (texte) servies par
  le site (`static/fonts/site/`, jamais Google Fonts) ; « Ma page » en tuiles
  (`apps/comptes/tableau.py::tuiles`, rien d'un autre membre) ; photos de l'accueil public dans
  `static/img/photos/` (accord des personnes, mention APDP finalité 10).

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
