# Étape 5 — Listes et statistiques en temps réel : plan de réalisation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal :** chaque bureau (paroisse, circuit, région, BN) peut générer à tout moment la liste filtrée des membres de son périmètre (écran, PDF, Excel) et consulter une page « Statistiques » dont chaque chiffre ouvre la liste correspondante ; chaque export est inscrit au journal.

**Architecture :** une nouvelle application `apps/listes` construit, à partir de `membres_visibles(unite)` (gardien des périmètres), un QuerySet filtré en base (âge calculé par comparaison de dates, jamais en Python). Les statistiques sont exprimées comme des « cellules » `(libellé, nombre, filtres)` : le lien de chaque chiffre est la liste avec exactement ces filtres, ce qui garantit « chiffre = nombre de lignes ». Une application minimale `apps/journal` (modèle + `journaliser`) est créée dès maintenant ; l'étape 7 y ajoutera la page de consultation et les autres événements.

**Tech Stack :** Django 5.2, ReportLab + DejaVu (`apps/membres/pdf.py::_polices`, `_ajuste`, couleurs), openpyxl, pytest-django, pypdf (tests).

**Spec :** `docs/superpowers/specs/2026-11-09-module1-fondations-design.md` — §7 (listes et statistiques), §3.6 (catégorie filtre/critère), §9.1 (droits), §9.2 (gardien), §12.1 (tests).

## Global Constraints

- Tout texte visible en français ; code et noms métier en français.
- Toute vue passe par `apps/bureaux/perimetre.py` : `unite_depuis_cle(request.user, cle)` (404 hors périmètre) puis `membres_visibles(unite)`. Filtrage en base, jamais seulement à l'affichage.
- « Générer des listes, consulter les statistiques » : bureaux paroisse/circuit/région (mandat de gestion en cours) et BN ; **jamais** un membre simple ni un titulaire sans droit de gérer (ex. Trésorier paroissial) → 404.
- La photo du CIP (et le NPI) n'apparaissent **jamais** dans une liste ni un export.
- Âge « calculé à la date du jour depuis la date de naissance », au jour près ; mêmes résultats que `Membre.age()`.
- Tranches par défaut : *moins de 18 ans*, *18 à 40 ans*, *plus de 40 ans* ; modifiables par le BN depuis le site.
- Statistiques : membres **actifs** par défaut, autres statuts sélectionnables ; membre sans date de naissance → ligne **« Âge non renseigné »**.
- PDF : en-tête officiel (« ARMÉE DU SALUT DU BÉNIN »), unité, date et heure de génération. Excel : même en-tête en tête de feuille.
- Chaque export (liste PDF, liste Excel, statistiques PDF) est inscrit au journal.
- Le grade (filtre, colonne, statistique) s'active au module 2 : **rien** à faire maintenant, mais ne pas fermer la porte (colonnes et filtres déclarés dans des tables extensibles).
- Tests : `DJANGO_DEBUG=True pytest -q` ; style : `ruff check .` ; TDD (test rouge d'abord).

## Décisions prises dans ce plan (à valider par le mainteneur)

1. **Journal minimal dès l'étape 5** (`apps/journal`) plutôt que d'attendre l'étape 7 : la spec exige l'inscription des exports. Consultation via l'admin technique en attendant la page BN de l'étape 7.
2. **Ce qui est journalisé :** les **téléchargements** (PDF, Excel) et la modification des tranches d'âge. Le simple affichage à l'écran n'est pas journalisé (sinon chaque clic remplirait le journal).
3. **Sens des bornes d'âge :** « moins de X ans » = âge < X ; « plus de Y ans » = âge > Y (40 ans pile n'est pas « plus de 40 ») ; « entre X et Y ans » = X ≤ âge ≤ Y (bornes incluses). Ainsi les trois tranches par défaut ne se chevauchent pas et couvrent tout le monde.
4. **Tranches modifiables :** le BN saisit des **bornes** (par défaut `18, 40`). Bornes `18, 40, 60` donnent : moins de 18 ; 18 à 40 ; 41 à 60 ; plus de 60.
5. **Statut par défaut de la liste :** « Actif » coché à la première ouverture ; si l'utilisateur décoche tout, tous les statuts sont inclus.
6. **Paroisse et circuit d'un membre** = son affectation ouverte, dans la hiérarchie actuelle (comme le gardien). Filtre « région » proposé au BN seulement (nécessaire pour la répartition par région).
7. Les listes à l'écran sont paginées par 100 ; les exports contiennent **toutes** les lignes.

## Review Focus

1. **Paramètres d'URL fantaisistes** (`age_x=abc`, âge négatif, « entre 40 et 18 », `paroisse=<id hors périmètre>`, `fonction=999`) → message d'erreur dans le formulaire, aucune ligne hors périmètre, jamais d'erreur 500. Test : Tâche 3 `test_parametres_invalides_sans_fuite`.
2. **Injection de formule Excel** : un nom saisi `=HYPERLINK(...)` ou `+33…` doit rester du texte dans le fichier (openpyxl traite toute chaîne commençant par `=` comme une formule). Test : Tâche 5 `test_excel_pas_de_formule`.
3. **Né un 29 février / aujourd'hui 29 février** : filtre d'âge en base identique à `Membre.age()`. Test : Tâche 2 `test_29_fevrier`.
4. **Membre sans affectation ouverte** (possible au niveau national) : colonnes paroisse/circuit vides, ligne « Sans affectation » dans la répartition par région, pas de plantage. Tests : Tâche 3 `test_membre_sans_affectation`, Tâche 6 `test_repartition_sans_affectation`.
5. **Gros export national** : nombre de requêtes constant (pas de N+1 sur paroisse, circuit, fonctions). Test : Tâche 3 `test_lignes_sans_n_plus_1` (`django_assert_max_num_queries(6)` pour 30 membres comme pour 3).

---

## Structure des fichiers

| Fichier | Rôle |
|---|---|
| `apps/journal/` (`models.py`, `services.py`, `admin.py`, `apps.py`, `migrations/`) | `EntreeJournal` + `journaliser()` |
| `apps/listes/ages.py` | `date_limite`, `filtrer_age`, `Tranche`, `tranches_depuis_bornes` |
| `apps/listes/models.py` | `ReglageStatistiques` (singleton, bornes d'âge) |
| `apps/listes/filtres.py` | `FiltreListeForm`, `membres_filtres`, `resume_filtres` |
| `apps/listes/colonnes.py` | `COLONNES_LISTE`, `preparer`, `lignes` |
| `apps/listes/exports.py` | `liste_pdf`, `liste_excel`, `statistiques_pdf` |
| `apps/listes/statistiques.py` | `Cellule`, `Section`, `calculer_statistiques` |
| `apps/listes/views.py`, `urls.py` | pages listes, statistiques, exports, tranches (BN) |
| `templates/listes/liste.html`, `statistiques.html`, `tranches.html` | gabarits |
| `templates/bureaux/_entete_unite.html` | onglets « Listes » et « Statistiques » |
| `config/settings.py`, `config/urls.py` | déclaration des deux applications, `path("bureau/", include("apps.listes.urls"))` placé **avant** l'include de `apps.bureaux.urls` |
| `apps/listes/tests/conftest.py` | réimporte les fixtures de `apps/bureaux/tests/conftest.py` (comme `apps/lots/tests/conftest.py`) + fixture `peupler` |

---

### Tâche 1 : Journal minimal

**Files :** Create `apps/journal/{__init__,apps,models,services,admin}.py`, migration `0001`, `apps/journal/tests/test_journal.py` ; Modify `config/settings.py` (INSTALLED_APPS : `apps.journal`, `apps.listes` — créer aussi le squelette `apps/listes/__init__.py`, `apps.py`).

**Interfaces :**
- Produces : `EntreeJournal(date: DateTimeField auto_now_add, auteur: FK Compte null SET_NULL, action: CharField(60), unite: CharField(40, blank), details: JSONField(default=dict))`, `Meta.ordering = ["-date"]`, verbose_name « entrée du journal ».
- Produces : `journaliser(par, action: str, unite: str = "", **details) -> EntreeJournal`.
- Constantes d'action dans `apps/journal/models.py` : `LISTE_PDF = "liste_pdf"`, `LISTE_EXCEL = "liste_excel"`, `STATISTIQUES_PDF = "statistiques_pdf"`, `TRANCHES_AGE = "tranches_age"`.

- [ ] **Step 1 : tests rouges**

```python
def test_journaliser(compte_technique):
    e = journaliser(compte_technique, LISTE_PDF, unite="paroisse-3", lignes=12, filtres={"sexe": "F"})
    e.refresh_from_db()
    assert e.auteur == compte_technique and e.action == "liste_pdf" and e.unite == "paroisse-3"
    assert e.details == {"lignes": 12, "filtres": {"sexe": "F"}} and e.date is not None

def test_admin_lecture_seule(client_technique, compte_technique):
    journaliser(compte_technique, LISTE_PDF)
    assert client_technique.get("/gestion/journal/entreejournal/").status_code == 200
    assert client_technique.get("/gestion/journal/entreejournal/add/").status_code == 403
```

- [ ] **Step 2 :** `DJANGO_DEBUG=True pytest apps/journal -q` → échec (module absent).
- [ ] **Step 3 :** implémenter ; admin : `has_add_permission`, `has_change_permission`, `has_delete_permission` → `False` ; `list_display = ("date", "auteur", "action", "unite")`. Migration via `makemigrations journal`.
- [ ] **Step 4 :** tests verts, `ruff check .`.
- [ ] **Step 5 :** commit `feat(journal): journal minimal des actions (exports)`.

---

### Tâche 2 : Âges et tranches

**Files :** Create `apps/listes/ages.py`, `apps/listes/models.py` (+ migration `0001`, avec une ligne par défaut `bornes="18,40"` créée par migration de données), `apps/listes/tests/test_ages.py`.

**Interfaces :**
- Produces : `date_limite(aujourdhui: date, annees: int) -> date` — même jour/mois `annees` ans plus tôt ; 29 février → 28 février (réutiliser `apps/bureaux/models.py::_ajouter_annees(jour, -annees)`).
- Produces : `filtrer_age(qs, condition: str, x: int | None, y: int | None, aujourdhui: date) -> QuerySet`, conditions `"moins"` (âge < x ⇔ `date_naissance > date_limite(j, x)`), `"plus"` (âge > x ⇔ `date_naissance <= date_limite(j, x + 1)`), `"entre"` (x ≤ âge ≤ y ⇔ `date_limite(j, y + 1) < date_naissance <= date_limite(j, x)`), `"inconnu"` (`date_naissance__isnull=True`). Les trois premières excluent les dates de naissance vides.
- Produces : `@dataclass(frozen=True) Tranche(libelle: str, condition: str, x: int, y: int | None)` et `tranches_depuis_bornes(bornes: list[int]) -> list[Tranche]` : `[18, 40]` → `[Tranche("Moins de 18 ans","moins",18,None), Tranche("18 à 40 ans","entre",18,40), Tranche("Plus de 40 ans","plus",40,None)]` ; `[18, 40, 60]` ajoute `Tranche("41 à 60 ans","entre",41,60)` et finit par `Tranche("Plus de 60 ans","plus",60,None)`.
- Produces : `ReglageStatistiques(bornes: CharField(60, default "18,40"))`, `ReglageStatistiques.courant() -> ReglageStatistiques` (get_or_create pk=1), propriété `liste_bornes -> list[int]`.

- [ ] **Step 1 : tests rouges** (fixture `aujourdhui = date(2026, 11, 10)`, membres créés avec `nouveau_membre` puis `date_naissance` mise à jour)

```python
@pytest.mark.parametrize("naissance, moins18, plus40, entre18_40", [
    (date(2008, 11, 11), True, False, False),   # 17 ans, 18 ans demain
    (date(2008, 11, 10), False, False, True),   # 18 ans aujourd'hui
    (date(1986, 11, 10), False, False, True),   # 40 ans pile
    (date(1985, 11, 11), False, False, True),   # 40 ans, 41 demain
    (date(1985, 11, 10), False, True, False),   # 41 ans aujourd'hui
])
def test_bornes_exactes(...):
    # chaque cas : filtrer_age(...).filter(pk=m.pk).exists() == attendu, et m.age(j) cohérent

def test_29_fevrier(...):
    # né le 2008-02-29 : au 2026-02-28 → pas « plus de 17 » ; au 2026-03-01 → « plus de 17 »
    # aujourd'hui 2028-02-29, né 2010-02-28 → 18 ans (entre 18 et 18) ; né 2010-03-01 → moins de 18
    # dans tous les cas : résultat du filtre == (m.age(j) comparé à la borne)

def test_inconnu_et_exclusion():
    # sans date de naissance : seulement dans "inconnu", jamais dans moins/plus/entre

def test_tranches_par_defaut():
    assert [t.libelle for t in tranches_depuis_bornes(ReglageStatistiques.courant().liste_bornes)] == [
        "Moins de 18 ans", "18 à 40 ans", "Plus de 40 ans"]

def test_tranches_trois_bornes():
    assert [(t.condition, t.x, t.y) for t in tranches_depuis_bornes([18, 40, 60])] == [
        ("moins", 18, None), ("entre", 18, 40), ("entre", 41, 60), ("plus", 60, None)]
```

- [ ] **Step 2 :** rouge. **Step 3 :** implémenter. **Step 4 :** vert + ruff. **Step 5 :** commit `feat(listes): calcul de l'âge en base et tranches d'âge`.

---

### Tâche 3 : Filtres, colonnes et lignes

**Files :** Create `apps/listes/filtres.py`, `apps/listes/colonnes.py`, `apps/listes/tests/conftest.py`, `apps/listes/tests/test_filtres.py`.

**Interfaces :**
- Consumes : `membres_visibles(unite)`, `Unite`, `Niveau` (bureaux) ; `filtrer_age` (Tâche 2).
- Produces : `FiltreListeForm(unite: Unite, data: QueryDict | None)` — champs GET (noms = clés d'URL, réutilisés par les statistiques) :
  `statut` (MultipleChoice, `Statut`), `sexe` (Choice vide/M/F), `categorie` (Choice vide + `Categorie`), `region` / `circuit` / `paroisse` (ModelChoice limités au périmètre : `region` seulement au niveau national ; `circuit` au national et régional ; `paroisse` sauf au niveau paroisse ; unités fermées incluses, libellé suffixé « (fermée) »), `annee` (Integer 1900–année courante), `fonction` (ModelChoice sur `Fonction`, ordonné niveau/ordre), `age` (Choice vide/moins/plus/entre/inconnu), `age_x`, `age_y` (Integer 0–130), `colonnes` (MultipleChoice sur `COLONNES_LISTE`), `envoye` (Hidden). `clean()` : `age_x` requis si `age` ∈ moins/plus/entre ; `age_y` requis et ≥ `age_x` si « entre » (message « L'âge maximum doit être supérieur ou égal à l'âge minimum. »).
  Valeurs initiales quand `envoye` est absent : `statut=["actif"]`, `colonnes=COLONNES_PAR_DEFAUT`.
- Produces : `membres_filtres(unite: Unite, donnees: dict, aujourdhui: date) -> QuerySet[Membre]` — part de `Membre.objects.filter(pk__in=membres_visibles(unite).values("pk"))` ; statut vide = tous ; paroisse/circuit/région via `affectations__date_fin__isnull=True` + `affectations__paroisse[__circuit[__region]]` ; fonction via `mandats` en cours (`Mandat.objects.en_cours(aujourdhui).filter(fonction=…).values("membre")`) ; tri `nom, prenoms`.
- Produces : `resume_filtres(form) -> list[str]`, ex. `["Statut : Actif", "Sexe : Féminin", "Âge : plus de 40 ans", "Circuit : Ekpe A"]` ; liste vide → `["Aucun filtre"]`.
- Produces (`colonnes.py`) : `COLONNES_LISTE: dict[str, tuple[str, float]]` (clé → (titre, largeur PDF en mm)) dans cet ordre : `matricule` (« Matricule », 28), `nom` (« Nom », 32), `prenoms` (« Prénoms », 40), `sexe` (« Sexe », 10), `age` (« Âge », 10), `telephone` (« Téléphone », 24), `whatsapp` (« WhatsApp », 24), `paroisse` (« Paroisse », 36), `circuit` (« Circuit », 30), `categorie` (« Catégorie », 28), `statut` (« Statut », 22), `fonctions` (« Fonction(s) », 45). `COLONNES_PAR_DEFAUT = ["matricule", "nom", "prenoms", "sexe", "age", "telephone", "paroisse"]`.
- Produces : `preparer(qs, aujourdhui) -> QuerySet` (annote `paroisse_actuelle`, `circuit_actuel` par `Subquery` sur l'affectation ouverte ; `Prefetch("mandats", queryset=Mandat.objects.en_cours(aujourdhui).select_related("fonction"), to_attr="mandats_en_cours")`) et `lignes(qs, colonnes: list[str], aujourdhui: date) -> Iterator[list[str | int | None]]` (sexe en lettre M/F, âge entier ou `None`, fonctions jointes par « , »).

- [ ] **Step 1 : tests rouges** (fixture `monde` + membres complémentaires)

```python
def test_perimetre_paroisse(monde):          # P1 : Adjovi, Secretaire, Tresorier ; jamais Bio (P2)
def test_perimetre_circuit_et_national(monde) # Ekpe A = P1+P2 ; national = tous
def test_filtres_combines(monde, ...):        # F + plus de 40 + circuit Ekpe A → exactement le membre attendu
def test_filtre_fonction(monde):              # fonction « Secrétaire paroissial » → [sec_p1] ; mandat terminé → exclu
def test_filtre_categorie_annee_statut(...)   # statut vide = tous ; ["decede"] seul ; catégorie honneur
def test_parametres_invalides_sans_fuite(monde):
    for data in [{"age": "plus", "age_x": "abc"}, {"age": "entre", "age_x": 40, "age_y": 18},
                 {"age": "moins", "age_x": -1}, {"paroisse": monde["P4"].pk}, {"fonction": 999}]:
        form = FiltreListeForm(unite_p1, QueryDict(urlencode(data | {"envoye": 1})))
        assert not form.is_valid()
def test_options_limitees_au_perimetre(monde): # paroisse proposée au circuit Ekpe A = {P1, P2} ; pas de champ region hors national
def test_resume_filtres(...)
def test_lignes_colonnes(monde):              # ["2015-…", "ADJOVI", …, "P1", "Ekpe A", "Secrétaire paroissial"]
def test_membre_sans_affectation(...):         # affectation ouverte fermée à la main → paroisse/circuit None, pas d'erreur
def test_lignes_sans_n_plus_1(...):            # django_assert_max_num_queries(6) pour 3 puis 30 membres
```

- [ ] **Step 2 :** rouge. **Step 3 :** implémenter. **Step 4 :** vert + ruff. **Step 5 :** commit `feat(listes): filtres combinables et colonnes au choix`.

---

### Tâche 4 : Page « Listes » de l'espace bureau

**Files :** Create `apps/listes/views.py`, `apps/listes/urls.py` (`app_name = "listes"`), `templates/listes/liste.html`, `apps/listes/tests/test_pages_listes.py` ; Modify `config/urls.py`, `templates/bureaux/_entete_unite.html` (onglets « Listes », « Statistiques »), `static/css/site.css` (formulaire de filtres repliable `<details>`, cases à cocher en grille sur mobile).

**Interfaces :**
- Produces : URL `listes:liste` → `/bureau/<cle>/listes/` ; vue `liste(request, cle)` : `unite_depuis_cle`, formulaire, si valide tableau paginé par 100 (`Paginator`) avec le total « N membre(s) » et le résumé des filtres ; boutons « Télécharger en PDF » / « Télécharger en Excel » pointant vers `listes:liste_pdf` / `listes:liste_excel` avec la même chaîne de requête (`request.GET.urlencode()`), pagination qui conserve les filtres.

- [ ] **Step 1 : tests rouges**

```python
def test_acces(client, monde):
    # sec_p1 → 200 sur /bureau/paroisse-<P1>/listes/ ; 404 sur paroisse-<P2>
    # m1 (membre simple) et tresorier (sans droit de gérer) → 404 ; anonyme → redirection connexion
def test_statut_actif_par_defaut(client, monde):  # un décédé n'apparaît pas à l'ouverture, apparaît si statut décoché (envoye=1)
def test_colonnes_choisies(client, monde):        # colonnes=matricule&colonnes=telephone → en-têtes exactement « Matricule », « Téléphone »
def test_jamais_cip_ni_npi(client, monde):        # « colonnes=npi » ou « photo_cip » → formulaire invalide ; HTML sans « NPI »
def test_onglets(client, monde):                  # page Membres contient les liens Listes et Statistiques
def test_erreur_affichee(client, monde):          # age=entre&age_x=40&age_y=18 → 200, message d'erreur, aucun tableau
```

- [ ] **Step 2 :** rouge. **Step 3 :** implémenter. **Step 4 :** vert + ruff. **Step 5 :** commit `feat(listes): page Listes de l'espace bureau`.

---

### Tâche 5 : Exports PDF et Excel des listes (+ journal)

**Files :** Create `apps/listes/exports.py`, `apps/listes/tests/test_exports.py` ; Modify `apps/listes/views.py`, `apps/listes/urls.py`.

**Interfaces :**
- Consumes : `membres_filtres`, `preparer`, `lignes`, `resume_filtres`, `COLONNES_LISTE`, `journaliser`.
- Produces : `entete_officiel(c, titre: str, sous_titres: list[str], larg, haut) -> float` (dessine « ARMÉE DU SALUT DU BÉNIN », le titre, les sous-titres, le filet or, retourne le y suivant) et `pied_de_page(c, numero: int)` (« Généré le JJ/MM/AAAA à HH:MM » + « Page n »), partagés avec les statistiques.
- Produces : `liste_pdf(unite: Unite, form, aujourdhui) -> bytes` — titre « Liste des membres — {unite.libelle} », sous-titres = `resume_filtres` + « N membre(s) » ; A4 portrait si la somme des largeurs ≤ 178 mm, sinon paysage ; au-delà de 265 mm, largeurs réduites proportionnellement ; textes coupés avec `_ajuste`.
- Produces : `liste_excel(unite, form, aujourdhui) -> bytes` — feuille « Membres » : A1 « Armée du Salut du Bénin — Liste des membres — {libellé} », A2 « Généré le … à … », A3 résumé des filtres joint par « ; », ligne 5 en-têtes (gras), données dès la ligne 6 ; téléphones en texte ; âge en nombre ; toute chaîne commençant par `=`, `+`, `-`, `@` écrite comme texte (cellule `data_type = "s"`) ; volets figés sous les en-têtes.
- Produces : URLs `listes:liste_pdf` → `/bureau/<cle>/listes/pdf/`, `listes:liste_excel` → `/bureau/<cle>/listes/excel/` ; formulaire invalide → redirection vers la page liste ; `journaliser(request.user, LISTE_PDF|LISTE_EXCEL, unite=unite.cle, lignes=n, filtres=request.GET.urlencode())` ; réponse `attachment; filename="liste-{cle}-{AAAAMMJJ-HHMM}.pdf|.xlsx"`, `Cache-Control: private, no-store`.

- [ ] **Step 1 : tests rouges**

```python
def test_pdf(client, monde):        # application/pdf ; texte pypdf contient « ARMÉE DU SALUT DU BÉNIN », « Généré le », « ADJOVI », pas « BIO »
def test_pdf_paysage_si_beaucoup_de_colonnes(...)  # toutes colonnes → page.mediabox largeur > hauteur
def test_excel(client, monde):      # openpyxl : A1 commence par « Armée du Salut du Bénin », ligne 5 = titres choisis, lignes = nombre de membres
def test_excel_pas_de_formule(...): # membre nommé "=HYPERLINK(\"x\")" → cellule data_type == "s" et valeur intacte
def test_journal(client, monde):    # un PDF puis un Excel → 2 EntreeJournal (liste_pdf, liste_excel), auteur = sec_p1, unite = cle, details["lignes"] correct
def test_export_hors_perimetre_404(client, monde)
def test_affichage_non_journalise(client, monde)   # GET de la page liste → aucune entrée
```

- [ ] **Step 2 :** rouge. **Step 3 :** implémenter. **Step 4 :** vert + ruff. **Step 5 :** commit `feat(listes): exports PDF et Excel journalisés`.

---

### Tâche 6 : Calcul des statistiques

**Files :** Create `apps/listes/statistiques.py`, `apps/listes/tests/test_statistiques.py`.

**Interfaces :**
- Consumes : `membres_filtres`, `filtrer_age`, `tranches_depuis_bornes`, `ReglageStatistiques`.
- Produces : `@dataclass Cellule(libelle: str, nombre: int, filtres: dict[str, str | list[str]])`, `@dataclass Section(titre: str, cellules: list[Cellule])`.
- Produces : `calculer_statistiques(unite: Unite, statuts: list[str], aujourdhui: date) -> list[Section]`, sections dans cet ordre :
  1. « Total » : une cellule « Total des membres » ;
  2. « Par sexe » : « Hommes » (`sexe=M`), « Femmes » (`sexe=F`) ;
  3. « Par tranche d'âge » : une cellule par tranche (`age`, `age_x`, `age_y`) + « Âge non renseigné » (`age=inconnu`) ;
  4. « Par catégorie » : une cellule par `Categorie` ;
  5. « Par statut » : une cellule par `Statut` — cette section **ignore** la sélection de statuts (filtre = ce seul statut) ;
  6. « Par région » (national), « Par circuit » (région), « Par paroisse » (circuit) : une cellule par unité inférieure non fermée **ou** ayant au moins un membre ; au national, cellule « Sans affectation » si au moins un membre n'a pas d'affectation ouverte (filtre `sans_affectation=1`, à ajouter à `FiltreListeForm` et `membres_filtres`, BN seulement). Rien au niveau paroisse.
  Chaque `filtres` contient `statut` (la liste sélectionnée, sauf section 5) et `envoye="1"`. Les comptes se font en base (`count()` sur `membres_filtres(unite, filtres)`, ou agrégats conditionnels — au choix tant que le test d'égalité ci-dessous passe).

- [ ] **Step 1 : tests rouges**

```python
def test_totaux(monde):                       # paroisse P1, statut actif : total, hommes/femmes, catégories attendus
def test_tranches_et_age_inconnu(...):        # la somme des tranches + « Âge non renseigné » == total
def test_statut_selectionnable(...):          # statuts=["decede"] → total = nb de décédés ; section « Par statut » inchangée
def test_repartition(monde):                  # national → 2 régions ; région HOULENOU → Ekpe A, Ekpe B ; circuit Ekpe A → P1, P2 ; paroisse → pas de section
def test_repartition_sans_affectation(...)    # un membre sans affectation ouverte → cellule « Sans affectation » = 1 au national
def test_chiffre_egal_liste(monde):           # pour CHAQUE cellule de CHAQUE unité : form = FiltreListeForm(unite, QueryDict(urlencode(c.filtres, doseq=True))) valide et membres_filtres(...).count() == c.nombre
```

- [ ] **Step 2 :** rouge. **Step 3 :** implémenter. **Step 4 :** vert + ruff. **Step 5 :** commit `feat(listes): calcul des statistiques par unité`.

---

### Tâche 7 : Page « Statistiques » et son export PDF

**Files :** Create `templates/listes/statistiques.html`, `apps/listes/tests/test_pages_statistiques.py` ; Modify `apps/listes/views.py`, `apps/listes/urls.py`, `apps/listes/exports.py`, `static/css/site.css`.

**Interfaces :**
- Produces : `listes:statistiques` → `/bureau/<cle>/statistiques/` (cases à cocher des statuts, « Actif » par défaut ; chaque section en carte ; chaque nombre est un lien `{% url 'listes:liste' unite.cle %}?{{ cellule.lien }}` où `lien = urlencode(filtres, doseq=True)`, calculé dans la vue) ; `listes:statistiques_pdf` → `/bureau/<cle>/statistiques/pdf/` (`statistiques_pdf(unite, sections, statuts, aujourdhui) -> bytes`, en-tête officiel commun, une table libellé/nombre par section) + `journaliser(..., STATISTIQUES_PDF, unite=cle, statuts=statuts)`.

- [ ] **Step 1 : tests rouges**

```python
def test_acces_statistiques(client, monde)       # mêmes règles que les listes (200 / 404)
def test_chaque_lien_donne_le_meme_nombre(client, monde):
    # pour les unités P1, Ekpe A, HOULENOU (BN) et national : lire response.context["sections"],
    # suivre chaque lien et vérifier response.context["page"].paginator.count == cellule.nombre
def test_export_pdf_statistiques(client, monde)  # PDF, « Statistiques — », « Généré le », « Total des membres » ; 1 entrée journal statistiques_pdf
```

- [ ] **Step 2 :** rouge. **Step 3 :** implémenter. **Step 4 :** vert + ruff. **Step 5 :** commit `feat(listes): page Statistiques cliquable et export PDF`.

---

### Tâche 8 : Tranches d'âge modifiables par le BN, accueil et documentation

**Files :** Create `templates/listes/tranches.html`, `apps/listes/forms.py`, `apps/listes/tests/test_tranches.py` ; Modify `apps/listes/views.py`, `apps/listes/urls.py`, `templates/accueil.html` (lien « Tranches d'âge des statistiques » dans le bloc Bureau national), `docs/guide-maintenance.md` (§17 Listes et statistiques : sens des bornes, journal, où modifier les tranches), `CLAUDE.md` (points techniques : `apps/listes`, `apps/journal::journaliser`).

**Interfaces :**
- Consumes : `bn_requis` (`apps/bureaux/views_bn.py`), `ReglageStatistiques`, `journaliser`, `TRANCHES_AGE`.
- Produces : `listes:tranches` → `/bureau/bn/tranches-age/` ; `BornesForm` champ texte « Bornes (âges séparés par des virgules) », validation : 1 à 6 entiers, chacun 1–120, strictement croissants, sinon « Saisissez des âges croissants entre 1 et 120, séparés par des virgules (ex. : 18, 40). » ; aperçu des tranches résultantes ; enregistrement → `journaliser(..., TRANCHES_AGE, avant="18,40", apres="18,40,60")` et message « Tranches d'âge enregistrées. ».

- [ ] **Step 1 : tests rouges**

```python
def test_reserve_au_bn(client, monde)            # sec_p1 → 403 ; client_technique → 200
def test_modifier(client_technique)              # POST "18, 40, 60" → bornes "18,40,60" ; statistiques affichent « 41 à 60 ans » ; 1 entrée journal
@pytest.mark.parametrize("saisie", ["", "40,18", "18,18", "abc", "0", "121", "1,2,3,4,5,6,7"])
def test_refus(client_technique, saisie)         # 200 + message d'erreur ; bornes inchangées
```

- [ ] **Step 2 :** rouge. **Step 3 :** implémenter + docs. **Step 4 :** suite complète en arrière-plan `DJANGO_DEBUG=True pytest -q` + `ruff check .` verts. **Step 5 :** commit `feat(listes): tranches d'âge modifiables par le BN ; docs`.

---

## Fin d'étape

- Relecture finale indépendante de toute la branche (un relecteur, modèle le plus capable), puis une passe de corrections (test rouge → vert pour chaque correction retenue).
- Captures d'écran mobiles de la page Listes et de la page Statistiques dans `docs/captures/`.
- Push puis Pull Request vers `main` (option 2, sans demander).
