# Module 2, étape 1 — Les grades : plan de réalisation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Chaque membre a un grade (« Camarade » à l'entrée, puis les 12 grades du RI) et un historique de grades. Il est nommé « Grade Prénoms NOM ». Le BNC attribue, promeut (y compris en série) et corrige les grades. Les listes et les statistiques filtrent et croisent par grade. Le site d'essai est recréé avec des grades variés.

**Architecture:**
- Les grades sont des constantes : `apps/membres/grades.py`, `Grade(IntegerChoices)` dont la valeur est le rang : 0 pour **Camarade** (appellation de tout nouveau membre, décision du BNC du 12/11/2026), puis 1 à 12.
- Le grade actuel et sa date sont dénormalisés sur `Membre` (`grade`, `date_grade`), pour filtrer en base.
- La nouvelle application `apps/grades` contient l'historique (`HistoriqueGrade`) et les règles de l'art. 78. Ses services sont les **seuls** points d'entrée qui modifient `Membre.grade`.
- Les listes et les statistiques réutilisent `membres_filtres`, avec de nouveaux filtres. Chaque chiffre reste égal au nombre de lignes de la liste qu'il ouvre.

**Tech Stack:** Django 5.2, PostgreSQL / SQLite, pytest-django, ReportLab, openpyxl.

**Spec:** `docs/cahier-des-charges.md` § 15 (décisions § 15.8) ; règlement intérieur `docs/donnees/reglement-interieur.md` art. 77 à 87.

## Global Constraints

- Tout texte visible en français ; code et noms métier en français ; `ruff check .` propre (ligne de 100).
- TDD : chaque test est écrit et vu échouer avant le code.
- **Nom affiché partout** : `grade prénoms NOM`. Exemple : `Capitaine Marc Aurel KOUDAKPO`. Sans grade : `Marc Aurel KOUDAKPO`.
- **Grade par défaut d'un nouveau membre : Camarade (rang 0).** Il devient Soldat de 3ᵉ classe à sa première consécration (art. 80), attribuée par le BNC sans durée minimale (le RI n'en fixe pas).
- **Libellés exacts des 12 grades, rangs 1 à 12 :**
  1. Soldat de 3ᵉ classe
  2. Soldat de 2ᵉ classe
  3. Soldat de 1ʳᵉ classe
  4. Sous-Capitaine
  5. Capitaine
  6. Senior Capitaine
  7. Commandant
  8. Sous-Supérieur
  9. Supérieur Délégué
  10. Supérieur Général Délégué
  11. Supérieur Général
  12. Supérieur Suprême Spirituel
- **Durées minimales (art. 78)**, rang → rang suivant, en années : 1→2 : 3 ; 2→3 : 3 ; 3→4 : 3 ; 4→5 : 4 ; 5→6 : 5.
- **Soldat de 3ᵉ classe (1)** : depuis Camarade seulement, mode « première consécration », sans durée minimale.
- **Grades 2 à 6** : par test, et seulement depuis le grade juste en dessous, après la durée minimale. Sinon, promotion exceptionnelle (art. 84), avec un motif obligatoire.
- **Grades 7 à 12** : par nomination, depuis n'importe quel grade inférieur, sans durée minimale.
- **Une sanction ne change jamais le grade.** On ne promeut qu'un membre au statut Actif.
- Le BNC seul (`has_perm("membres.gerer_membres")`) attribue, promeut ou corrige un grade. Tout passe par le journal et notifie le membre et le bureau de sa paroisse.
- Toute vue passe par le gardien des périmètres (`apps/bureaux/perimetre.py`). Jamais de NPI ni de photo du CIP dans une liste.
- La tenue n'est pas suivie.

## Review Focus

1. **Grade écrit librement dans un fichier Excel** (« capitaine », « Soldat de 3e classe », « 3ème classe », « Sous capitaine ») : il doit être reconnu. Un libellé inconnu donne une erreur de ligne claire, jamais une erreur 500.
2. **Promotion datée avant la date du grade actuel, ou dans le futur** : refusée avec un message, rien n'est enregistré.
3. **Promotion en série dont un membre ne remplit pas les conditions** : rien n'est appliqué (tout ou rien). Le message nomme chaque membre en cause.
4. **Membre sans grade** (enregistré avant cette étape) : il est nommé sans grade et apparaît dans « Grade non renseigné ». La promotion est refusée et oriente vers la correction.
5. **Statistiques avec filtres de page** (par exemple région + plus de 40 ans) : chaque chiffre du tableau grade × tranche d'âge est égal au nombre de lignes de la liste qu'il ouvre.

---

### Task 1: Grades, champs du membre, historique, nom affiché

**Files:**
- Create: `apps/membres/grades.py`, `apps/grades/__init__.py`, `apps/grades/apps.py`, `apps/grades/models.py`, `apps/grades/admin.py`, `apps/grades/tests/__init__.py`, `apps/grades/tests/conftest.py`, `apps/grades/tests/test_modeles.py`
- Modify:
  - `apps/membres/models.py` (champs `grade`, `date_grade` ; `nom_complet`) ;
  - `config/settings.py` (`INSTALLED_APPS` += `apps.grades`) ;
  - les tests qui comparent l'ancien format « NOM Prénoms » : `apps/membres/tests/test_enregistrement.py` et ceux que la suite signale.
- Migrations : `apps/membres/migrations/00xx_grade.py`, `apps/grades/migrations/0001_initial.py`

**Interfaces:**
- Produces:
  - `Grade(models.IntegerChoices)` : `CAMARADE=0`, `SOLDAT_3=1` … `SUPREME=12`, libellés exacts ci-dessus.
  - `DUREES_MINIMALES: dict[int, int]` (`{1: 3, 2: 3, 3: 3, 4: 4, 5: 5}`).
  - `PAR_NOMINATION = 7` (premier rang attribué par nomination).
  - `grade_depuis_texte(texte: str) -> Grade | None`.
  - `Membre.grade` : `PositiveSmallIntegerField(choices=Grade.choices, null=True, blank=True)`.
  - `Membre.date_grade` : `DateField(null=True, blank=True)`.
  - `Membre.nom_complet` → `"Capitaine Marc Aurel KOUDAKPO"`.
  - `ModeGrade(TextChoices)` : `ENTREE` (« Entrée dans le mouvement », Camarade), `PREMIERE_CONSECRATION`, `REGULARISATION`, `TEST`, `NOMINATION`, `EXCEPTIONNELLE`, `CORRECTION`.
  - `HistoriqueGrade` : `membre` (FK PROTECT, `related_name="grades"`), `grade`, `date_effet`, `mode`, `reference` (blank), `motif` (blank), `enregistre_par` (FK Compte, SET_NULL), `date_saisie` (auto). Tri par défaut `["date_effet", "date_saisie"]`. La suppression lève `PermissionDenied`, comme `Membre`.

- [ ] **Step 1: Tests**
  - `test_grades_dans_l_ordre` : `[g.label for g in Grade]` == `["Camarade"]` + les 12 libellés ; `Grade.CAMARADE == 0` ; `Grade.CAPITAINE == 5`.
  - `test_grade_depuis_texte` (paramétré) :
    - reconnus : « camarade » → 0 ; « capitaine » → 5 ; « Soldat de 3e classe », « soldat de 3ème classe », « 3ᵉ classe » → 1 ; « Soldat de 1ere classe » → 3 ; « sous capitaine » → 4 ; « SUPERIEUR SUPREME SPIRITUEL » → 12 ;
    - non reconnus : « Général », « » → `None`.
  - `test_nom_complet_avec_grade` : `Membre(nom="koudakpo", prenoms="Marc Aurel", grade=5).nom_complet == "Capitaine Marc Aurel KOUDAKPO"`.
  - `test_nom_complet_camarade` : `grade=0` → `"Camarade Marc Aurel KOUDAKPO"` (0 n'est pas « sans grade »).
  - `test_nom_complet_sans_grade` : `grade=None` → `"Marc Aurel KOUDAKPO"`.
  - `test_historique_ne_se_supprime_pas` : `PermissionDenied`.
- [ ] **Step 2:** Lancer `pytest apps/grades -q` → ÉCHEC (module introuvable).
- [ ] **Step 3: Implémenter.**
  - `grade_depuis_texte` normalise le texte : `cle_nom` de `apps/membres/models.py`, puis `ᵉ→e`, `ʳ→r`, `ème/eme/ere/re → e`, tirets et espaces multiples → un espace. On compare ensuite à la forme normalisée de chaque libellé, et aussi au libellé sans « Soldat de » pour les rangs 1 à 3.
  - Migrations par `makemigrations`.
  - Mettre à jour les tests qui attendaient « NOM Prénoms ».
- [ ] **Step 4:** `DJANGO_DEBUG=True pytest -q` → tout vert ; `ruff check .`.
- [ ] **Step 5:** Commit `feat(grades): douze grades, grade du membre, historique, nom « Grade Prénoms NOM »`.

### Task 2: Services des grades (seul point d'entrée)

**Files:**
- Create: `apps/grades/services.py`, `apps/grades/tests/test_services.py`
- Modify: `apps/journal/models.py` (constantes `GRADE_ATTRIBUE = "grade_attribue"`, `GRADE_PROMOTION = "grade_promotion"`, `GRADE_CORRECTION = "grade_correction"` + `LIBELLES`)

**Interfaces:**
- Consumes: Task 1.
- Produces :
  - `class GradeRefuse(Exception)` (message affichable tel quel).
  - `attribuer_grade_initial(membre, *, grade: int, date_effet: date, par, regularisation: bool) -> HistoriqueGrade` : mode `REGULARISATION` si `regularisation`, sinon `ENTREE` (grade Camarade). N'est **pas** journalisé ni notifié à part : il fait partie de l'enregistrement.
  - `promouvoir(membre, *, grade: int, date_effet: date, reference: str, par, exceptionnelle: bool = False, motif: str = "") -> HistoriqueGrade`.
  - `promouvoir_en_serie(membres: list, *, grade: int, date_effet: date, reference: str, par) -> list[HistoriqueGrade]` : tout ou rien, dans une transaction. En cas de refus, lève `GradeRefuse` avec un message qui liste `"{nom_complet} : {raison}"` pour chaque membre refusé.
  - `corriger_grade(membre, *, grade: int, date_effet: date, motif: str, par) -> HistoriqueGrade`.
  - `eligible(membre, aujourdhui: date) -> bool` et `filtre_eligibles(aujourdhui: date) -> Q` (même règle, en base) : statut Actif et, soit `grade == 0` (Camarade, éligible à la première consécration sans durée), soit `grade` de 1 à 5 avec `date_grade + DUREES_MINIMALES[grade] ans <= aujourdhui`.

- [ ] **Step 1: Tests**, avec un membre Actif Soldat de 3ᵉ classe depuis le 01/01/2020 :
  - `test_premiere_consecration` : un Camarade enregistré le 10/03/2026 passe Soldat de 3ᵉ classe le 11/03/2026 → mode `PREMIERE_CONSECRATION`, accepté ; un Camarade vers le grade 2 → refus (saut).
  - `test_eligible_camarade` : un Camarade actif est éligible, quelle que soit son ancienneté.
  - `test_promotion_apres_duree` : vers le grade 2 au 01/01/2023 → `membre.grade == 2`, `date_grade` mise à jour, historique de mode `TEST`, entrée de journal `GRADE_PROMOTION`, une notification au membre et une à la paroisse, et `membre.compte.nom_affiche == "Soldat de 2ᵉ classe Prénoms NOM"`.
  - `test_promotion_trop_tot_refusee` : au 31/12/2022 → `GradeRefuse`, contenant « 3 ans » ; rien n'est modifié.
  - `test_saut_de_grade_refuse_sauf_exceptionnelle` : vers le grade 3 → refus ; avec `exceptionnelle=True` et `motif=""` → refus « motif obligatoire » ; avec un motif → accepté, mode `EXCEPTIONNELLE`.
  - `test_nomination_sans_duree` : vers Commandant (7) au 02/01/2020 → accepté, mode `NOMINATION`.
  - Refusés :
    - `test_grade_inferieur_ou_egal_refuse` ;
    - `test_date_avant_grade_actuel_refusee` ;
    - `test_date_future_refusee` ;
    - `test_reference_obligatoire` ;
    - `test_membre_non_actif_refuse` (statuts Sanctionné, Exclu et Décédé) ;
    - `test_sans_grade_refuse_vers_correction` (message contenant « correction »).
  - `test_serie_tout_ou_rien` : 3 membres dont un arrivé trop tôt → `GradeRefuse` qui nomme ce membre ; aucun des 3 n'est promu.
  - `test_correction` : grade quelconque (même inférieur) avec motif → mode `CORRECTION`, journal `GRADE_CORRECTION` ; motif vide → refus.
  - `test_eligibles_en_base_egal_python` : sur 6 membres variés, `set(Membre.objects.filter(filtre_eligibles(j)))` == `{m for m in tous if eligible(m, j)}`.
- [ ] **Step 2:** ÉCHEC attendu.
- [ ] **Step 3: Implémenter.**
  - Ajout d'années au 29 février : réutiliser `apps/mouvements/statuts.py::ajouter_mois(date, 12 * n)`.
  - Verrouiller le membre (`select_for_update`) dans `transaction.atomic()`.
  - Mettre à jour `Membre.grade`, `Membre.date_grade` et `compte.nom_affiche` seulement ici.
  - Message de notification : « Votre grade : {libellé} à compter du {date} (décision {référence}). » ; à la paroisse : « {nom_complet} : nouveau grade {libellé}. »
- [ ] **Step 4:** Suite verte, ruff.
- [ ] **Step 5:** Commit `feat(grades): promotion, nomination, promotion exceptionnelle et en série, correction, éligibilité`.

### Task 3: Grade à l'enregistrement (individuel et lots)

**Files:**
- Modify :
  - `apps/membres/services.py::enregistrer_membre` (nouveaux paramètres `grade: int = Grade.CAMARADE`, `date_grade: date | None = None`, `regularisation: bool = False` ; appelle `attribuer_grade_initial` dans la même transaction ; `date_grade` par défaut = date d'intégration).
  - `apps/membres/forms.py::FormulaireEnregistrement` (champs `grade`, `date_grade` non-modèle).
  - `apps/membres/views_bn.py::enregistrer`, `templates/membres/bn_enregistrer.html`.
  - `apps/lots/colonnes.py` (colonnes facultatives `Colonne("Grade", "grade", False)` et `Colonne("Date du grade", "date_grade", False)`).
  - `apps/lots/controle.py` (reconnaissance par `grade_depuis_texte`, date au format JJ/MM/AAAA), `apps/lots/generation.py`.
  - le modèle Excel téléchargeable et `docs/guide-lots-regions.md`.
- Test: `apps/membres/tests/test_enregistrement.py`, `apps/lots/tests/test_controle.py`, `apps/lots/tests/test_generation.py`

**Interfaces:**
- Consumes: `attribuer_grade_initial`, `grade_depuis_texte`.
- Produces: `enregistrer_membre(..., grade=…, date_grade=…, regularisation=…)`.

- [ ] **Step 1: Tests**
  - `test_enregistrement_camarade_par_defaut` : `grade == 0`, un historique de mode `ENTREE`, `date_grade == 01/01/annee` ; `compte.nom_affiche` commence par « Camarade ».
  - `test_enregistrement_regularisation_capitaine` : formulaire BN avec grade 5 et date 15/03/2018 → historique `REGULARISATION` ; `compte.nom_affiche` commence par « Capitaine ».
  - `test_date_grade_avant_naissance_refusee` (erreur de formulaire).
  - Lots :
    - `test_lot_grade_libre_reconnu` (« capitaine » → 5) ;
    - `test_lot_grade_inconnu_erreur_de_ligne` (message « Grade : grade inconnu (…) ») ;
    - `test_lot_sans_colonne_grade_camarade` (anciens fichiers toujours acceptés ; grade Camarade).
  - `test_lot_valide_cree_historique` : mode `REGULARISATION` quand la colonne est remplie, `ENTREE` sinon.
- [ ] **Step 2:** ÉCHEC.
- [ ] **Step 3: Implémenter.** Le grade et sa date ne passent pas par `valider_futur_membre` : ce sont des champs propres à l'enregistrement, validés dans le formulaire et dans `normaliser_ligne`.
- [ ] **Step 4:** Suite verte.
- [ ] **Step 5:** Commit `feat(grades): grade et date du grade à l'enregistrement individuel et par lots (régularisation)`.

### Task 4: Fiches, PDF et pages du BNC

**Files:**
- Create : `apps/grades/forms.py`, `apps/grades/views.py`, `apps/grades/urls.py` (monté sur `grades/` dans `config/urls.py`), `templates/grades/promouvoir.html`, `templates/grades/corriger.html`, `templates/grades/serie.html`, `templates/grades/_historique.html`, `apps/grades/tests/test_vues.py`
- Modify :
  - `templates/membres/ma_fiche.html`, `templates/bureaux/fiche_membre.html`, `templates/membres/bn_fiche.html` (grade actuel + `_historique.html` ; liens BN « Promouvoir » / « Corriger le grade ») ;
  - `apps/membres/pdf.py::dessiner_fiche` (ligne « Grade » avant « Catégorie ») ;
  - `templates/_menu.html` (BN : « Promotions en série ») ;
  - `templates/accueil.html` et `_menu.html` restent sur `nom_affiche`, désormais tenu à jour.

**Interfaces:**
- Consumes: Task 2.
- Produces : URL `grades:bn_promouvoir` (`bn/<matricule>/promouvoir/`), `grades:bn_corriger` (`bn/<matricule>/corriger/`), `grades:bn_serie` (`bn/serie/`).

- [ ] **Step 1: Tests**
  - `test_ma_fiche_affiche_grade_et_historique`.
  - `test_fiche_bureau_affiche_grade` (paroisse).
  - `test_pdf_contient_grade` (texte extrait du PDF).
  - `test_promouvoir_bn_ok` (POST → redirection vers la fiche BN et message « Grade enregistré »).
  - `test_promouvoir_refuse_affiche_message` (pas de 500).
  - `test_pages_grades_interdites_hors_bn` (bureau de région → 403 ; membre simple → 403).
  - `test_serie` :
    - GET `?grade=2` liste les membres Actifs de grade 1, l'éligibilité étant indiquée ; GET `?grade=1` liste les Camarades ;
    - POST avec 2 cases cochées → 2 promus ;
    - POST avec un membre non éligible → aucun promu, message qui le nomme.
- [ ] **Step 2:** ÉCHEC.
- [ ] **Step 3: Implémenter.**
  - Formulaire de promotion : grade cible (ne propose que des grades supérieurs), date d'effet (aujourd'hui par défaut), référence de la décision, case « promotion exceptionnelle (art. 84) », motif.
  - Page de série :
    - filtre facultatif par région ;
    - grades 1 à 6 : seulement les membres du grade juste en dessous (pour le grade 1 : les Camarades — c'est la liste de la prochaine consécration) ;
    - grades 7 et plus : tous les grades inférieurs ;
    - tri par région puis nom.
- [ ] **Step 4:** Suite verte.
- [ ] **Step 5:** Commit `feat(grades): grade et historique sur les fiches et le PDF ; pages BN de promotion et de correction`.

### Task 5: Listes — filtre, colonnes, éligibles

**Files:**
- Modify :
  - `apps/listes/filtres.py` (`FiltreListeForm` : `grade` = `MultipleChoiceField` avec Camarade, les 12 grades + `("aucun", "Grade non renseigné")` ; `grade_min` = `ChoiceField` « À partir de » ; `eligible` = `BooleanField` « Éligibles au grade suivant » ; `membres_filtres` les applique, `eligible` via `filtre_eligibles`) ;
  - `apps/listes/filtres.py::resume_filtres` ;
  - `apps/listes/colonnes.py` (`"grade": ("Grade", 34)`, `"date_grade": ("Grade depuis", 22)`) ;
  - `templates/listes/liste.html` ;
  - `templates/_menu.html` (lien « Éligibles » par unité → liste `?envoye=1&eligible=1&colonnes=…grade,date_grade`).
- Test: `apps/listes/tests/test_filtres.py`, `apps/listes/tests/test_exports.py`

**Interfaces:**
- Produces : clés de filtre d'URL `grade` (multiple, valeurs `"0"`…`"12"` ou `"aucun"`), `grade_min`, `eligible`. Utilisées par la Task 6.

- [ ] **Step 1: Tests**
  - `test_filtre_grade_et_age_et_region` : Capitaines de plus de 40 ans d'une région → exactement les membres attendus.
  - `test_filtre_grade_min` (« à partir de Capitaine » inclut Senior Capitaine et Commandant).
  - `test_filtre_grade_non_renseigne`.
  - `test_filtre_eligible`.
  - `test_colonne_grade_pdf_et_excel` (libellé du grade dans les deux exports ; jamais de NPI).
  - `test_resume_filtres_mentionne_grade`.
- [ ] **Step 2:** ÉCHEC.
- [ ] **Step 3:** Implémenter.
- [ ] **Step 4:** Suite verte.
- [ ] **Step 5:** Commit `feat(listes): filtre et colonnes grade, membres éligibles au grade suivant`.

### Task 6: Statistiques par grade et tableaux croisés

**Files:**
- Modify :
  - `apps/listes/statistiques.py` :
    - section « Par grade » (Camarade, 12 grades, « Grade non renseigné ») ;
    - `@dataclass Tableau(titre: str, colonnes: list[str], lignes: list[tuple[str, list[Cellule]]])` ;
    - `calculer_tableaux(unite, base: dict, aujourdhui) -> list[Tableau]` : grade × tranche d'âge, grade × sexe, grade × unité inférieure (pas pour une paroisse) ; on n'affiche que les lignes de grade non vides, plus le total.
  - `calculer_statistiques(unite, statuts, aujourdhui, base: dict | None = None)` : les filtres de page `base` (mêmes clés que la liste, sans `colonnes`) s'appliquent à **toutes** les cellules.
  - `apps/listes/views.py` (formulaire de filtres sur la page Statistiques, réutilisant `FiltreListeForm` sans les colonnes) ; `templates/listes/statistiques.html`.
  - `apps/listes/exports.py::statistiques_pdf` (tableaux croisés, une page par tableau si nécessaire, orientation paysage pour les unités inférieures).
- Test: `apps/listes/tests/test_statistiques.py`

**Interfaces:**
- Consumes : filtres de la Task 5.

- [ ] **Step 1: Tests**
  - `test_par_grade_compte_juste`.
  - `test_chaque_cellule_croisee_egale_sa_liste` : pour chaque cellule de chaque tableau, `cellule.nombre == membres_filtres(unite, _nettoyer(unite, cellule.filtres), j).count()`. Les filtres de page sont région + `age=plus` + `age_x=40`.
  - `test_filtres_de_page_s_appliquent_a_toutes_les_sections`.
  - `test_paroisse_sans_tableau_unites_inferieures`.
  - `test_pdf_statistiques_contient_tableau_grade`.
- [ ] **Step 2:** ÉCHEC.
- [ ] **Step 3:** Implémenter.
- [ ] **Step 4:** Suite verte. Vérifier le temps de la page nationale sur 2 000 membres (une requête `count` par cellule, à garder sous 2 s). Au-delà, regrouper avec `values("grade").annotate(Count)` **seulement** pour les tableaux, en gardant le test d'égalité.
- [ ] **Step 5:** Commit `feat(statistiques): répartition par grade, tableaux croisés grade × âge, sexe et unité, filtres de page`.

### Task 7: Site d'essai recréé avec des grades, documents

**Files:**
- Modify : `apps/membres/management/commands/peupler_demo.py`.
- Create : `apps/membres/management/commands/reinitialiser_demo.py`, `apps/membres/tests/test_demo.py` (compléter s'il existe).
- Modify (docs) :
  - `docs/guide-alwaysdata.md` (§ « Recréer les données fictives ») ;
  - `docs/guide-maintenance.md` (§ 21 Grades) ;
  - `templates/protection_donnees.html` et `docs/apdp/dossier-apdp.md` (+ PDF) : le grade et son historique parmi les données ;
  - `docs/recapitulatif-du-projet.md` (+ PDF) ;
  - `CLAUDE.md` (point technique « Grades »).

**Interfaces:**
- Consumes : `enregistrer_membre(grade=…, date_grade=…, regularisation=True)`, `promouvoir`.

- [ ] **Step 1: Tests**
  - `test_demo_grades_varies` : sur 300 membres (graine fixe), au moins 8 grades différents, dont Camarade, Capitaine et Senior Capitaine ; aucun grade dont la date précède la date d'intégration ; les historiques respectent les durées de l'art. 78.
  - `test_reinitialiser_demo_refuse_hors_demo` (`SITE_DEMO=False` → `CommandError`).
  - `test_reinitialiser_demo_refuse_sans_confirmation` (sans `--oui`).
  - `test_reinitialiser_demo_postgresql` (ignoré sous SQLite) : après la commande, il y a de nouveaux membres et le territoire est présent.
- [ ] **Step 2:** ÉCHEC.
- [ ] **Step 3: Implémenter.**
  - `peupler_demo` attribue un grade selon l'ancienneté (années depuis l'intégration) et l'âge :
    - Camarade pour les intégrés depuis moins d'un an, puis 1 à 6 par paliers de l'art. 78, avec un historique de promotions datées ;
    - environ 5 % de nominations (7 à 9) chez les plus anciens ;
    - le Président et le Secrétaire national de démonstration ont des grades élevés.
  - `reinitialiser_demo --oui` : `SITE_DEMO` obligatoire et PostgreSQL obligatoire (message clair sous SQLite). Il exécute `flush` (TRUNCATE, ce qui contourne le blocage du journal, voulu ici pour des données fictives seulement), puis `charger_territoire` et `peupler_demo`, et rappelle de recréer le compte technique (`createsuperuser`).
- [ ] **Step 4:** Suite complète verte, `ruff check .`, `makemigrations --check`.
- [ ] **Step 5:** Commit `feat(demo): membres fictifs avec grades variés ; commande reinitialiser_demo ; documentation des grades`.

---

## Après le plan

Relecture finale indépendante de toute la branche, une passe de corrections, puis PR vers `main`. Sur le site d'essai : `mettre_a_jour.sh`, puis `reinitialiser_demo --oui`, `createsuperuser`, et ⟳ Redémarrer.

La situation des cotisations à côté des éligibles (§ 15.6) viendra avec l'étape 2 (cotisations).
