# Module 2, étape 2 — Les cotisations mensuelles (CM) : plan de réalisation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** suivre mois par mois la cotisation de chaque membre (100 F), du mois de mise en service jusqu'au mois en cours.
- La paroisse saisit les versements, le circuit les valide.
- Chaque validation est répartie : paroisse 30 %, circuit 20 %, région 20 %, national 30 %.
- Chaque niveau dispose d'un tableau de bord, de listes, de statistiques et de documents PDF : état des cotisations et reçus.

**Architecture:**
- Nouvelle application `apps/cotisations`.
  - `regles.py` (fonctions pures) calcule les mois dus et la situation d'un membre.
  - `services.py` est le **seul** point d'entrée des écritures : saisie, validation, refus, annulation, parts reçues, réglages. Chaque opération est journalisée (avec une phrase lisible dans `apps/journal/lecture.py`) et notifiée.
- Qui peut faire quoi : une nouvelle fonction du gardien des périmètres, `unites_cotisations`, ajoute les **trésoriers** aux titulaires d'une fonction de gestion.
- Les listes et statistiques existantes reçoivent des filtres et des colonnes « cotisations ». Comme avant, chaque chiffre est égal au nombre de lignes de la liste qu'il ouvre.

**Tech Stack:** Django 5.2, PostgreSQL / SQLite, pytest-django, ReportLab, openpyxl.

**Spec:** `docs/cahier-des-charges.md` § 16 (v2.4 : décisions § 16.9, répartition § 16.4 bis).

## Global Constraints

- Français partout ; ruff (ligne de 100) ; TDD (test vu en échec d'abord) ; suite verte sous SQLite **et** PostgreSQL.
- **Montant** : 100 F par mois (réglage BNC avec date d'effet ; les mois passés gardent leur montant).
- **Répartition** : paroisse 30 %, circuit 20 %, région 20 %, national 30 % (réglage BNC, total = 100 %).
- **Mois de départ** : réglage BNC (mois de mise en service). Tant qu'il n'est pas fixé, rien n'est dû et la saisie est fermée.
- **Ce qui est dû** :
  - pour **tous les membres** (actifs, d'honneur, sympathisants, sanctionnés, mineurs) ;
  - à partir du mois de départ, ou du mois d'enregistrement s'il est plus tardif, jusqu'au mois en cours ;
  - rien pour les mois où la personne est exclue, démissionnaire ou décédée.
- **À jour** : tous les mois dus jusqu'au mois en cours sont payés **et validés**. Sinon « en retard de N mois (N × montant) ». Le paiement d'avance est permis pour les mois de l'année en cours.
- **Saisie** par la paroisse. **Validation ou refus** (avec motif) par le circuit. Un mois en attente de validation n'est pas encore payé.
- **Reçu PDF après validation**. Rappel automatique au circuit pour les versements en attente depuis **30 jours**.
- Rien ne se supprime : un versement s'**annule** (avec motif), et l'annulation reste visible.
- **Rien sur la fiche du membre ni sur la fiche PDF** : documents à part (« État des cotisations mensuelles », reçu).
- Un membre simple ne voit que **ses** cotisations. Les bureaux voient leur périmètre (gardien des périmètres).
- Toute nouvelle donnée est reportée sur la page « Protection de vos données » et dans le dossier APDP.

## Décisions de conception (à valider par le mainteneur)

1. **Les trésoriers ont accès aux cotisations.** Le Trésorier paroissial, de circuit, régional et national (et son adjoint) n'a pas de « droit de gérer » dans le règlement intérieur. Pourtant, c'est lui qui encaisse. Il obtient donc l'accès aux **seules pages des cotisations** de son unité : il ne voit pas les fiches complètes des membres.
2. **Montant saisi** : il doit correspondre à un nombre entier de mois. Le site le répartit sur les mois non payés les plus anciens, puis sur les mois suivants de l'année (paiement d'avance). Exemple : 300 F = 3 mois.
3. **Parts « reçues »** : marquées par niveau (circuit, région, national), **par paroisse et par mois de validation**. Un versement ancien validé en décembre compte dans la part de décembre.
4. **Numéro de reçu** : `R2026-000123`, unique, attribué à la validation.

## Review Focus

1. Un **montant qui ne correspond pas** à un nombre entier de mois (150 F), nul ou négatif : refusé avec un message, rien n'est enregistré.
2. **Deux saisies simultanées** couvrant le même mois pour le même membre : une seule passe (contrainte en base sur les mois actifs).
3. Un membre **muté** en cours d'année : ses versements passés restent rattachés à la paroisse qui a encaissé ; la nouvelle paroisse voit sa situation complète.
4. Un membre **décédé ou exclu** : aucun mois dû après la date de sortie ; s'il est réhabilité, les mois sont de nouveau dus à partir du retour.
5. Un **changement de tarif** en cours d'année : les mois antérieurs gardent l'ancien montant ; le « reste dû » additionne les bons montants.

---

### Task 1: Modèles, réglages et règles de calcul

**Files:** Create `apps/cotisations/{__init__,apps,models,regles,admin}.py`, `apps/cotisations/tests/{__init__,conftest,test_regles,test_modeles}.py`, migration ; Modify `config/settings.py`.

**Interfaces — Produces:**
- `ParametresCotisations` (une seule ligne : `mois_depart: date | None`) avec `courant()`.
- `Tarif` : `date_effet` (1er du mois), `montant: int`, `part_paroisse`, `part_circuit`, `part_region`, `part_national` (pourcentages entiers, total 100 vérifié dans `clean`). Fonction `tarif_du(mois) -> Tarif`.
- `EtatVersement` : `EN_ATTENTE`, `VALIDE`, `REFUSE`, `ANNULE`.
- `Versement` :
  - `membre`, `paroisse` (qui a encaissé), `montant`, `date_versement`, `etat` ;
  - `saisi_par`, `valide_par`, `date_validation`, `motif` (refus ou annulation) ;
  - `numero_recu` (unique, vide tant que non validé) ;
  - parts figées à la validation : `parts: JSON`.
  - La suppression lève `PermissionDenied`.
- `MoisCotise` : `versement`, `membre`, `mois` (1er du mois), `montant`, `actif: bool`. Contrainte unique **partielle** (`membre`, `mois`) quand `actif=True`.
- `PartRecue` : `niveau` (circuit, région, national), `paroisse`, `mois_validation`, `montant`, `marquee_par`, `date`. Contrainte unique (`niveau`, `paroisse`, `mois_validation`).
- `regles.py` :
  - `mois_dus(membre, jusqu_a: date) -> list[date]` (départ, enregistrement, périodes hors statut via `HistoriqueMembre`) ;
  - `Situation` (`dus`, `payes`, `en_attente`, `retard: int`, `reste_du: int`, `a_jour: bool`, `total_annee: int`, `total_depuis_debut: int`) ;
  - `situation(membre, mois_courant) -> Situation` ;
  - `situations(qs, mois_courant) -> dict[pk, Situation]` (requêtes groupées, sans requête par membre).

- [ ] **Tests** :
  - `test_rien_du_sans_mois_de_depart` ;
  - `test_mois_dus_depuis_depart_ou_enregistrement` ;
  - `test_pas_du_apres_deces_et_de_nouveau_apres_rehabilitation` ;
  - `test_a_jour_et_retard` (2 mois validés sur 3 dus → retard 1, reste 100) ;
  - `test_en_attente_ne_compte_pas` ;
  - `test_changement_de_tarif` (100 puis 150 → reste dû exact) ;
  - `test_parts_total_100` (refus de 30/20/20/20) ;
  - `test_mois_cotise_unique_actif` (IntegrityError ; un mois inactif n'empêche pas) ;
  - `test_versement_ne_se_supprime_pas` ;
  - `test_situations_groupees_egales_individuelles` (10 membres, `django_assert_max_num_queries(6)`).
- [ ] Échec → implémentation → suite verte → commit `feat(cotisations): modèles, réglages, règles des mois dus et situation`.

### Task 2: Services (seul point d'entrée) et droits

**Files:** Create `apps/cotisations/services.py`, `tests/test_services.py` ; Modify `apps/bureaux/perimetre.py` (`unites_cotisations`), `apps/journal/models.py` (`VERSEMENT_SAISI`, `VERSEMENT_VALIDE`, `VERSEMENT_REFUSE`, `VERSEMENT_ANNULE`, `PART_RECUE`, `REGLAGE_COTISATIONS`), `apps/journal/lecture.py` (phrases et actions nationales).

**Interfaces — Produces:**
- `CotisationRefusee(Exception)`.
- `unites_cotisations(compte, jour=None) -> list[Unite]` : unités gérées, plus les unités où le compte a un mandat en cours de « Trésorier… » (adjoint compris) ; le BN en fait partie.
- `saisir_versement(membre, *, montant: int, date_versement, par, mois: list[date] | None = None) -> Versement` : paroisse actuelle du membre ; répartition automatique si `mois` est None ; verrou sur le membre.
- `saisir_collecte(paroisse, *, coches: dict[membre_pk, list[date]], date_versement, par) -> list[Versement]` : tout ou rien.
- `valider(versements, *, par) -> list[Versement]` : numéro de reçu, parts figées, notification au membre.
- `refuser(versement, *, motif, par)` : mois libérés, notification à la paroisse.
- `annuler(versement, *, motif, par)` : paroisse si en attente, BN si validé ; mois libérés.
- `marquer_part_recue(*, niveau, paroisse, mois_validation, par) -> PartRecue` (montant = somme des parts de ce niveau).
- `regler(*, mois_depart=None, tarif: dict | None = None, par)` : BN.
- `rappeler_en_attente(aujourdhui) -> int` (versements de plus de 30 jours → `notifier_unite` du circuit).

- [ ] **Tests** :
  - `test_saisie_repartie_sur_mois_les_plus_anciens` (300 F → 3 plus anciens) ;
  - `test_paiement_d_avance_dans_l_annee` ;
  - `test_montant_non_multiple_refuse` (150 F, 0, -100) ;
  - `test_saisie_fermee_sans_mois_de_depart` ;
  - `test_mois_deja_paye_refuse` ;
  - `test_collecte_tout_ou_rien` ;
  - `test_validation_numero_recu_et_parts` (30/20/20/30 sur 300 F → 90/60/60/90) ;
  - `test_refus_libere_les_mois_et_notifie` ;
  - `test_annulation_par_bn_apres_validation` ;
  - `test_part_recue_montant_et_unicite` ;
  - `test_rappel_30_jours` ;
  - `test_tresorier_a_acces_cotisations_seulement` (Trésorier paroissial : `unites_cotisations` contient sa paroisse, `unites_gerees` non) ;
  - `test_journal_phrases_cotisations` (« A enregistré un versement de 300 F pour … (janvier à mars 2027). »).
- [ ] Commit `feat(cotisations): saisie, validation, refus, annulation, parts reçues, rappel ; accès des trésoriers`.

### Task 3: Pages paroisse et circuit

**Files:** Create `apps/cotisations/{forms,views,urls}.py`, `templates/cotisations/{paroisse,versement,a_valider,parts}.html`, `tests/test_vues.py` ; Modify `config/urls.py`, `templates/_menu.html` (rubrique « Cotisations » par unité de `unites_cotisations`).

- **Paroisse** :
  - grille membres × 12 mois de l'année (payé / en attente / non payé / non dû / avance) ; cases à cocher pour la **collecte** ;
  - formulaire individuel (membre, montant, date) ; annulation d'un versement en attente.
- **Circuit** : versements **à valider** par paroisse (cocher, valider, ou refuser avec motif).
- **Circuit / région / national** : page « Parts » (paroisse × mois de validation, part due, bouton « Reçue »).
- [ ] **Tests** :
  - `test_grille_paroisse` ;
  - `test_collecte_depuis_la_grille` ;
  - `test_validation_par_le_circuit` ;
  - `test_refus_motif_obligatoire` ;
  - `test_tresorier_paroissial_saisit_mais_ne_voit_pas_les_fiches` (403 sur `bureaux:fiche_membre`) ;
  - `test_paroisse_ne_valide_pas` (403) ;
  - `test_autre_paroisse_404` ;
  - `test_membre_simple_403`.
- [ ] Commit `feat(cotisations): grille de collecte de la paroisse, validation par le circuit, parts reçues`.

### Task 4: Tableau de bord, espace du membre, documents PDF

**Files:** Create `apps/cotisations/pdf.py`, `templates/cotisations/{tableau_de_bord,mes_cotisations}.html` ; Modify `templates/accueil.html` (bloc cotisations pour les unités de `unites_cotisations`), `templates/_menu.html` (« Mes cotisations »).

- **Tableau de bord par unité** (année et mois choisis) :
  - membres à jour et en retard (liens vers les listes de la Task 5) ;
  - montant validé, en attente, reste dû ;
  - part du niveau, reçue ou en attente ;
  - versements à valider (pour le circuit).
- **Mes cotisations** (membre) : sa grille de l'année, total, à jour / en retard, et ses reçus.
- **PDF** (en-tête officiel, logos) :
  - `etat_cotisations_pdf(membre, annee)` ;
  - `recu_pdf(versement)`, format A6, refusé tant que non validé ;
  - l'état d'une unité vient des listes (Task 5).
- [ ] **Tests** :
  - `test_tableau_de_bord_chiffres` ;
  - `test_mes_cotisations_seulement_les_miennes` ;
  - `test_etat_pdf_contient_total_et_mention` (« À jour au … » ou « En retard de 2 mois (200 F CFA) ») ;
  - `test_recu_pdf_apres_validation_seulement` ;
  - `test_fiche_pdf_sans_cotisations`.
- [ ] Commit `feat(cotisations): tableau de bord, mes cotisations, état des cotisations et reçu en PDF`.

### Task 5: Listes et statistiques

**Files:** Modify `apps/listes/filtres.py` (filtre `cotisation` : `a_jour`, `en_retard`, `retard_min` (N mois)), `apps/listes/colonnes.py` (`mois_payes` « Mois payés (année) », `total_verse` « Total versé (F) », `reste_du` « Reste dû (F) »), `apps/listes/statistiques.py` (section « Cotisations » : à jour, en retard, en retard de 3 mois et plus ; montants par unité inférieure), exports.

- Les filtres de cotisation sont appliqués à partir de `situations()` : `pk__in` des membres concernés, toujours à l'intérieur de `membres_visibles`.
- [ ] **Tests** :
  - `test_filtre_a_jour_et_en_retard` ;
  - `test_filtre_combine_grade_et_retard` (Capitaines en retard d'au moins 2 mois) ;
  - `test_colonnes_cotisations_pdf_excel` ;
  - `test_chaque_chiffre_cotisation_egal_sa_liste`.
- [ ] Commit `feat(listes): filtres, colonnes et statistiques des cotisations`.

### Task 6: Réglages BN, tâche quotidienne, démo, documents

**Files:**
- Create : `templates/cotisations/reglages.html`, la commande `rappel_cotisations`.
- Modify :
  - `deploiement/alwaysdata/taches_quotidiennes.sh` ;
  - `peupler_demo` : mois de départ = janvier de l'année en cours ; versements variés (à jour, en retard, en attente, refusé, d'avance) ; quelques parts reçues ;
  - `templates/protection_donnees.html`, `docs/apdp/dossier-apdp.md` (+ PDF) ;
  - `docs/guide-maintenance.md` (§ 22 Cotisations), `docs/guide-alwaysdata.md`, `docs/recapitulatif-du-projet.md` (+ PDF), `CLAUDE.md`.
- [ ] **Tests** :
  - `test_reglages_bn_seulement` ;
  - `test_reglage_tarif_total_100` ;
  - `test_commande_rappel` ;
  - `test_demo_cotisations_variees`.
- [ ] Suite complète SQLite + PostgreSQL verte, `makemigrations --check`, ruff.
- [ ] Commit `feat(cotisations): réglages du BN, rappel quotidien, démo, documentation`.

---

## Après le plan

Relecture finale indépendante, une passe de corrections, puis PR vers `main`.

Sur le site d'essai :
1. `mettre_a_jour.sh` ;
2. `reinitialiser_demo --oui --base …` ;
3. `createsuperuser` ;
4. ⟳ Redémarrer.
