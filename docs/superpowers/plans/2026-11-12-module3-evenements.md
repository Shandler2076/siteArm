# Module 3 — Espace « Événements » (événements nationaux) : plan de réalisation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** le Bureau national (Secrétaire national) peut :
- créer un événement national, avec ses sessions ;
- convoquer des membres en les cochant, ce qui les notifie ;
- pointer leur présence.

Pour les grands événements, chaque convoqué télécharge une **autorisation** de petit format avec sa photo et un QR code de vérification. La participation reste dans l'historique et sur la fiche du membre.

**Architecture:**
- Nouvelle application `apps/evenements` ; `services.py` est le **seul** point d'écriture.
- Toutes les pages de gestion sont réservées au BN (`has_perm("membres.gerer_membres")`). Les bureaux de région, de circuit et de paroisse ne voient pas les événements (décision du 12/11/2026).
- **Exception** : le bureau de la **paroisse** du membre peut imprimer ses **autorisations valables** (et rien d'autre de l'événement), depuis la fiche du membre dans l'espace de la paroisse.
- Le membre voit ses propres convocations ; la page de vérification du QR code est publique, mais elle n'affiche que « valable / non valable », le nom et la session.
- La sélection des convoqués réutilise les filtres des listes (`FiltreListeForm`, `membres_filtres` au niveau national).

**Tech Stack:** Django 5.2, ReportLab, segno (QR code, déjà installé), pytest-django.

**Spec:** `docs/cahier-des-charges.md` § 17 (v2.5).

## Global Constraints

- Français ; ruff ; TDD ; suites SQLite **et** PostgreSQL vertes.
- **Seuls les événements nationaux**, gérés par le Bureau national.
- Rien ne s'efface :
  - un événement s'**annule** (motif) ;
  - un convoqué se **retire** (motif) ;
  - tout est journalisé (phrases lisibles dans `apps/journal/lecture.py`).
- Convocation, retrait, report et annulation → **notification** au membre (site + e-mail).
- **Présences** : présent, absent, excusé ; seulement pour un convoqué (non retiré).
- **Autorisation** : seulement si l'événement a l'option. Le PDF de petit format contient : photo validée, grade prénoms NOM, matricule, événement (dénomination, date, lieu), « Est autorisé(e) à travailler — session … », et un QR code vers `/evenements/verifier/<jeton>/`.
- **Jeton du QR code** : aléatoire, 32 caractères, unique par convocation ; on ne le déduit jamais du matricule.
- **Vérification** :
  - affiche « Autorisation valable » si la convocation est active et l'événement non annulé, sinon « Non valable » ;
  - ne montre **ni coordonnées, ni NPI, ni photo du CIP** ;
  - montre seulement la photo d'identité, le nom, le grade, la session et l'événement, pour que le contrôleur reconnaisse la personne.
- Jamais de NPI ni de photo du CIP dans les listes et exports.
- Page « Protection de vos données » et dossier APDP mis à jour (participation aux événements, autorisation).

## Review Focus

1. Un **membre retiré** ou un **événement annulé** : son autorisation (PDF déjà imprimé) apparaît **non valable** au scan, et son PDF n'est plus téléchargeable.
2. Un **jeton inventé ou modifié** dans l'URL de vérification : « Non valable », sans erreur 500 et sans fuite d'information.
3. Un **membre sans photo validée** : l'autorisation sort quand même, avec le cadre « Photo à venir ».
4. **Convoquer deux fois** le même membre (ou le reconvoquer après un retrait) : une seule convocation active ; le retrait reste dans l'historique.
5. Un **membre simple** qui tente d'ouvrir l'autorisation d'un autre (identifiant de convocation dans l'URL) : 404.

---

### Task 1: Modèles et services

**Files:** Create `apps/evenements/{__init__,apps,models,services,admin}.py`, `tests/{conftest,test_services}.py`, migration ; Modify `config/settings.py`, `apps/journal/models.py` + `lecture.py`.

**Interfaces — Produces:**
- `Evenement` :
  - `nom`, `debut: datetime`, `fin: datetime | None`, `lieu`, `description` ;
  - `avec_autorisation: bool`, `etat` (prévu / annulé), `motif_annulation` ;
  - `cree_par`, `date_creation`.
- `Session` : `evenement`, `nom`, `ordre` ; unique (`evenement`, `nom`).
- `Convocation` :
  - `evenement`, `membre`, `session` (nullable), `active: bool`, `jeton` (unique) ;
  - `presence` : `""` (non pointé), présent, absent, excusé ;
  - `pointe_par`, `date_pointage`, `convoque_par`, `date_convocation`, `motif_retrait`.
  - Contrainte unique partielle (`evenement`, `membre`) si `active`.
  - La suppression lève une erreur (`delete()`).
- `EvenementRefuse(Exception)`.
- Services :
  - `creer_evenement(..., sessions: list[str], par) -> Evenement` ;
  - `modifier_evenement(ev, ..., par)` : report → notification aux convoqués actifs ;
  - `annuler_evenement(ev, motif, par)` ;
  - `convoquer(ev, membres, session=None, par) -> list[Convocation]` : ignore les déjà convoqués actifs, change leur session si elle est différente, réactive un retiré, notifie ;
  - `retirer(convocation, motif, par)` ;
  - `pointer(convocation, presence, par)` : refusé sur un événement annulé ou une convocation retirée ;
  - `convocation_par_jeton(jeton) -> Convocation | None` ;
  - `autorisation_valable(c) -> bool`.
- Journal : `EVENEMENT_CREE`, `EVENEMENT_MODIFIE`, `EVENEMENT_ANNULE`, `CONVOCATION`, `CONVOCATION_RETIREE`, `PRESENCE`, avec leurs phrases.

- [ ] **Tests** :
  - `test_creer_avec_sessions` ;
  - `test_convoquer_notifie_et_ne_double_pas` ;
  - `test_reconvoquer_apres_retrait` ;
  - `test_retrait_invalide_l_autorisation` ;
  - `test_annulation_notifie_et_invalide` ;
  - `test_report_notifie` ;
  - `test_pointer_presence_et_refus_si_retire` ;
  - `test_jeton_aleatoire_unique` ;
  - `test_journal_phrases_evenements`.
- [ ] Commit `feat(evenements): événements nationaux, sessions, convocations, présences`.

### Task 2: Pages du Bureau national

**Files:** Create `apps/evenements/{forms,views,urls}.py`, `templates/evenements/{liste,formulaire,detail,convoquer,pointage}.html`, `tests/test_vues.py` ; Modify `config/urls.py`, `templates/_menu.html` (BN : « Événements »).

- **Liste** des événements (à venir, passés, annulés).
- **Création et modification** (sessions saisies une par ligne, case « Générer une autorisation »).
- **Fiche de l'événement** :
  - convoqués par session, avec présence et taux de présence ;
  - actions : retirer, annuler l'événement ;
  - exports PDF et Excel de la liste des convoqués.
- **Convoquer** : filtres des listes (niveau national), cases à cocher, choix de la session, bouton « Convoquer les membres cochés ».
- **Pointage**, sur téléphone :
  - liste triée par nom, recherche par nom ou matricule ;
  - trois boutons : Présent, Absent, Excusé ;
  - la vérification par QR code renvoie vers la ligne du convoqué.
- [ ] **Tests** :
  - `test_pages_reservees_au_bn` (bureau de région 403, membre 403) ;
  - `test_creer_puis_convoquer_par_filtres` (Capitaines d'une région) ;
  - `test_pointage` ;
  - `test_export_convoques_sans_npi`.
- [ ] Commit `feat(evenements): pages du Bureau national (création, convocation, pointage, exports)`.

### Task 3: Espace du membre, autorisation PDF et vérification

**Files:** Create `apps/evenements/pdf.py`, `templates/evenements/{mes_evenements,verifier}.html`, `tests/test_autorisation.py` ; Modify les fiches (`templates/membres/ma_fiche.html`, `bureaux/fiche_membre.html`, `membres/bn_fiche.html` : bloc « Événements »), `templates/_menu.html` (« Mes événements »).

- **« Mes événements »** : convocations, session, présence ; bouton « Mon autorisation (PDF) » si l'option est active et l'autorisation valable.
- **`autorisation_pdf(convocation) -> bytes`** :
  - format carte (85 × 120 mm, portrait), logos, photo d'identité, mentions de la spec, QR code (segno) ;
  - pour le BN, **toutes les autorisations** d'un événement en une fois (plusieurs cartes par page A4).
- **`/evenements/verifier/<jeton>/`** (sans connexion) : grand bandeau vert « Autorisation valable » ou rouge « Non valable », avec photo, grade et nom, événement, session.
- **Fiche du membre** : historique des événements (convocation, session, présence).
- **Paroisse** : sur `bureaux/fiche_membre.html`, au niveau paroisse seulement, un bloc « Autorisations à imprimer » (événement, session, lien PDF). L'accès au PDF est permis au membre, au BN et au bureau de la paroisse actuelle du membre, jamais au circuit ni à la région (nouvelle fonction du gardien des périmètres : `peut_imprimer_autorisation(compte, convocation)`).
- [ ] **Tests** :
  - `test_paroisse_imprime_l_autorisation_de_son_membre` ;
  - `test_circuit_et_region_ne_peuvent_pas_imprimer` (404) ;
  - `test_mes_evenements_seulement_les_miens` ;
  - `test_autorisation_pdf_contenu` (nom, matricule, session, « autorisé(e) à travailler ») ;
  - `test_autorisation_sans_photo` ;
  - `test_pas_d_autorisation_si_option_desactivee` ;
  - `test_autorisation_d_un_autre_404` ;
  - `test_verifier_valable_et_non_valable` (retrait, annulation, jeton inventé) ;
  - `test_verifier_ne_montre_ni_npi_ni_coordonnees` ;
  - `test_historique_sur_la_fiche`.
- [ ] Commit `feat(evenements): mes événements, autorisation PDF avec QR code, vérification, historique sur la fiche`.

### Task 4: Démo, documents

- **`peupler_demo`** :
  - un événement « Pèlerinage de la Nativité 2026 » (24 décembre), avec les sessions Mère, Culte et Fruits et l'option autorisation, une trentaine de convoqués répartis ;
  - un « Conclave du Bureau national », sans autorisation, passé, avec des présences pointées.
- **Documents** : `templates/protection_donnees.html`, `docs/apdp/dossier-apdp.md` (+ PDF), `docs/guide-maintenance.md` (§ 23), `docs/recapitulatif-du-projet.md` (+ PDF), `CLAUDE.md`.
- [ ] **Tests** : `test_demo_evenements` ; suites complètes SQLite + PostgreSQL ; ruff ; `makemigrations --check`.
- [ ] Commit `feat(evenements): démo (pèlerinage de la Nativité), documentation`.

---

## Après le plan

Relecture finale indépendante, corrections, PR vers `main`. Sur le site d'essai : `mettre_a_jour.sh`, `reinitialiser_demo --oui --base …`, `createsuperuser`, ⟳ Redémarrer.
