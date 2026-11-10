# Étape 4 — Enregistrement des membres par lots (Excel) : plan de réalisation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Permettre au BNC d'enregistrer d'un coup les nouveaux membres d'une région à partir du **modèle Excel officiel**, avec un **écran de contrôle** (rien n'est créé avant la confirmation), puis une génération **tout ou rien** des matricules, comptes et affectations, les fiches d'identification PDF et une liste récapitulative.

**Architecture:** Nouvelle application `apps/lots` : modèles `Lot` et `LigneLot` ; `modele_excel.py` (génère le modèle de la région) ; `lecture.py` (lit le fichier, normalise chaque ligne) ; `controle.py` (vérifie chaque ligne avec les **mêmes règles** que l'enregistrement individuel, détecte les doublons) ; `generation.py` (une seule transaction qui appelle `enregistrer_membre` pour chaque ligne retenue) ; vues réservées au BNC. Les fichiers déposés sont rangés dans le stockage **privé**.

**Tech Stack:** Django 5.2, PostgreSQL, openpyxl (lecture/écriture `.xlsx`), ReportLab (PDF, déjà en place), pytest.

**Spec:** `docs/superpowers/specs/2026-11-09-module1-fondations-design.md` — section **6.2** (enregistrement par lots), 3.2 (matricule), 3.6 (catégorie : vide = « membre actif »), 6.1 (règles de l'enregistrement individuel), 9.1 (enregistrement réservé au BN), 10 (notifications).

## Global Constraints

- Réservé au BNC : `request.user.has_perm("membres.gerer_membres")`, sinon 403.
- Format accepté : **`.xlsx` uniquement** (le modèle officiel), **5 Mo** au plus, **2 000 lignes** au plus par lot. Les lignes entièrement vides sont ignorées.
- **Colonnes du modèle** (feuille « Membres », ligne 1 = en-têtes, dans cet ordre) : `Nom*`, `Prénoms*`, `Sexe*` (M/F), `Date de naissance` (JJ/MM/AAAA), `Lieu de naissance`, `Situation matrimoniale`, `NPI`, `Téléphone*`, `WhatsApp`, `Email`, `Quartier`, `Ville`, `Profession`, `Personne à contacter (nom)`, `Personne à contacter (téléphone)`, `Année d'intégration*`, `Paroisse d'intégration*`, `Catégorie` (vide = « Membre actif »). L'astérisque marque les colonnes obligatoires.
- Listes déroulantes dans le modèle : sexe (« M », « F »), situation matrimoniale (libellés du modèle `Membre`), catégorie (« Membre actif », « Membre d'honneur », « Membre sympathisant »), paroisses **actives** de la région (feuille cachée « Listes »). Une feuille « Consignes » explique la saisie en français.
- Les règles de validation sont **exactement** celles de l'enregistrement individuel (téléphones, NPI à 10 chiffres et unique, année entre 1900 et l'année en cours, champs obligatoires) : on réutilise la validation du modèle `Membre`, pas une copie.
- Paroisse : retrouvée **dans la région du lot** par comparaison sans accents ni casse ni espaces superflus (`cle_nom`) ; une paroisse d'une autre région ou fermée est une **erreur**.
- Dates : cellule date Excel, ou texte `JJ/MM/AAAA` ; tout autre format est une erreur (« Date invalide : écrivez JJ/MM/AAAA »).
- États d'une ligne : `correcte`, `doublon` (doublon possible non tranché), `erreur`, `ecartee`, `gardee` (doublon tranché « garder »).
- **Aucun membre, compte, matricule ni compteur** n'est créé ou modifié avant la validation du lot.
- Validation possible seulement s'il ne reste **aucune ligne en erreur ni doublon non tranché** et au moins une ligne à créer ; génération **tout ou rien** (si une ligne échoue, rien n'est créé et un message dit laquelle).
- Le mot de passe provisoire n'est **jamais stocké en clair** : les fiches avec identifiants sont produites par une action « Imprimer les fiches avec identifiants » qui crée de nouveaux mots de passe (comme à l'étape 2).
- Notifications : **une seule** par bureau concerné et par lot (« N nouveaux membres dans votre périmètre (lot n° X). »), pas une par membre.
- Le fichier d'origine et le lot restent archivés, consultables par le BNC.
- Tout texte visible en français ; pages pensées pour le téléphone.

## Review Focus

1. **Dates écrites de plusieurs façons** (cellule date Excel, « 12/03/1985 », « 1985 », « 12-03-85 ») : les deux premières acceptées, les autres refusées avec un message clair → test dans la tâche 3.
2. **Paroisse écrite autrement** (« paroisse saint michel de tokpota davo », espaces doubles, sans accents) : reconnue ; une paroisse d'une autre région : erreur nommant la paroisse → test dans la tâche 3.
3. **Même personne deux fois dans le fichier** : les deux lignes signalées « doublon possible » → test dans la tâche 4.
4. **Panne au milieu de la génération** (capacité de 9 999 atteinte à la 3ᵉ ligne) : rien n'est créé, compteur inchangé, lot toujours en brouillon, message nommant la ligne → test dans la tâche 6.
5. **Fichier qui n'est pas le modèle** (`.xls`, `.csv` renommé, colonnes déplacées ou supprimées) : refusé avec un message qui dit quoi faire ; lignes vides en fin de fichier ignorées → test dans la tâche 3.

---

## Structure des fichiers

```
apps/lots/
  models.py        # Lot, LigneLot, EtatLot, EtatLigne
  colonnes.py      # COLONNES (ordre, en-têtes, champ du modèle, obligatoire)
  modele_excel.py  # modele_pour_region(region) -> bytes
  lecture.py       # lire_classeur(fichier) -> list[dict], FichierInvalide
  controle.py      # controler_lot(lot) ; verifier_ligne(ligne) ; doublons
  generation.py    # valider_lot(lot, par) -> list[Membre] ; GenerationEchouee
  pdf.py           # fiches_du_lot_pdf(...) ; recapitulatif_pdf(lot)
  forms.py  views.py  urls.py  admin.py
  tests/
templates/lots/   # liste, deposer, controle, ligne, confirmer, resultat
```

---

### Task 1 : Modèles du lot

**Files:**
- Create: `apps/lots/{__init__,apps,models,admin}.py`, `apps/lots/migrations/0001_initial.py` (générée), `apps/lots/colonnes.py`
- Modify: `config/settings.py` (`apps.lots`), `requirements.txt` (`openpyxl>=3.1`)
- Test: `apps/lots/tests/test_modeles.py`, `apps/lots/tests/conftest.py`

**Interfaces:**
- Consumes: `Region`, `Membre`, `Compte`, `stockage_prive`.
- Produces:
  - `EtatLot(TextChoices)` : `BROUILLON="brouillon"` (« Brouillon »), `VALIDE="valide"` (« Validé »).
  - `EtatLigne(TextChoices)` : `CORRECTE="correcte"` (« Correcte »), `DOUBLON="doublon"` (« Doublon possible »), `ERREUR="erreur"` (« Erreur »), `ECARTEE="ecartee"` (« Écartée »), `GARDEE="gardee"` (« Doublon gardé »).
  - `Lot` : `region` (FK PROTECT), `fichier` (`FileField(storage=stockage_prive, upload_to="lots/")`), `nom_fichier` (200), `etat` (défaut brouillon), `cree_par` (FK Compte SET_NULL), `date_creation` (auto), `valide_par` (FK Compte null), `date_validation` (null). Propriétés : `nb_par_etat -> dict[str, int]`, `validable -> bool` (aucune ligne `erreur`/`doublon` et au moins une `correcte`/`gardee`). `__str__` → `"Lot n° {pk} — {region.nom}"`.
  - `LigneLot` : `lot` (FK CASCADE, related_name="lignes"), `numero` (n° de ligne Excel, PositiveInteger), `donnees` (JSONField : valeurs **normalisées** prêtes pour `Membre`, dates en ISO, `paroisse_integration` = pk), `brutes` (JSONField : valeurs telles que lues, pour l'affichage), `etat`, `erreurs` (JSONField, liste de chaînes), `doublons` (JSONField, liste de matricules ou « ligne N »), `corrigee_par` (FK Compte null), `date_correction` (null), `membre` (FK Membre null, après génération) ; tri par `numero` ; unique `(lot, numero)`.
  - `colonnes.COLONNES: list[Colonne]` avec `Colonne(entete: str, champ: str, obligatoire: bool)` dans l'ordre des Global Constraints ; `champ` = nom du champ `Membre` ou `"annee_integration"`, `"paroisse_integration"`, `"categorie"`.
- `conftest.py` : réutilise les fixtures de `apps/bureaux/tests/conftest.py` (`territoire`, `nouveau_membre`, `compte_technique`, `client_technique`) et ajoute la fabrique `classeur(lignes: list[list], entetes_modifiees: dict[int, str] | None = None) -> SimpleUploadedFile` qui construit un `.xlsx` au format du modèle (feuille « Membres », en-têtes `COLONNES` — éventuellement remplacés aux index donnés — puis les lignes).

- [ ] **Step 1 : Écrire les tests** — `test_lot_validable` (lot avec lignes correcte+erreur → `validable` faux ; erreur passée à écartée → vrai ; tout écarté → faux), `test_nb_par_etat`, `test_colonnes_ordre_et_obligatoires` (18 colonnes ; obligatoires = Nom, Prénoms, Sexe, Téléphone, Année d'intégration, Paroisse d'intégration), `test_fichier_lot_prive` (`lot.fichier.storage` est `stockage_prive`).
- [ ] **Step 2 : Vérifier l'échec** — `DJANGO_DEBUG=True pytest apps/lots -q` → FAIL (`ModuleNotFoundError`).
- [ ] **Step 3 : Implémenter** modèles, colonnes, migration, admin en lecture seule.
- [ ] **Step 4 : Vérifier** — `DJANGO_DEBUG=True pytest -q && ruff check .` → tout passe.
- [ ] **Step 5 : Commit** — `feat(lots): modèles du lot et des lignes`.

---

### Task 2 : Modèle Excel officiel de la région

**Files:**
- Create: `apps/lots/modele_excel.py`, `apps/lots/views.py`, `apps/lots/urls.py`
- Modify: `config/urls.py` (`lots/` → `apps.lots.urls`, namespace `lots`)
- Test: `apps/lots/tests/test_modele_excel.py`

**Interfaces:**
- Consumes: `COLONNES` (tâche 1), `Paroisse`, `Categorie`, `SituationMatrimoniale`, `Sexe`.
- Produces:
  - `modele_pour_region(region: Region) -> bytes` — classeur avec feuille « Membres » (en-têtes en gras, colonnes obligatoires en rouge foncé, première ligne figée, largeurs lisibles, colonne « Date de naissance » au format `JJ/MM/AAAA`), validations de données (listes déroulantes) sur 2 000 lignes, feuille cachée « Listes » (paroisses actives de la région triées par nom, catégories, situations), feuille « Consignes » (rappel des règles : obligatoire, format de date, une ligne par membre, ne pas modifier les en-têtes, catégorie vide = membre actif).
  - URL `lots:modele` → GET `/lots/modele/<code_region>.xlsx` (BNC) → `Content-Disposition: attachment; filename="modele-membres-region-<code>.xlsx"`.

- [ ] **Step 1 : Écrire les tests**

```python
import io
from openpyxl import load_workbook
from apps.lots.colonnes import COLONNES
from apps.lots.modele_excel import modele_pour_region

def test_modele_structure(territoire):
    wb = load_workbook(io.BytesIO(modele_pour_region(territoire["HOULENOU"])))
    ws = wb["Membres"]
    assert [c.value for c in ws[1]] == [col.entete for col in COLONNES]
    assert wb["Listes"].sheet_state == "hidden"
    paroisses = [c.value for c in wb["Listes"]["A"] if c.value]
    assert paroisses == ["P1", "P2", "P3"]          # région 03 seulement, triées
    assert "Consignes" in wb.sheetnames
    assert len(ws.data_validations.dataValidation) >= 4

def test_paroisse_fermee_absente(territoire):
    territoire["P2"].fermer()
    wb = load_workbook(io.BytesIO(modele_pour_region(territoire["HOULENOU"])))
    assert "P2" not in [c.value for c in wb["Listes"]["A"]]

def test_telechargement_reserve_au_bn(client, client_technique, territoire, nouveau_membre):
    assert client_technique.get("/lots/modele/03.xlsx")["Content-Disposition"].endswith('modele-membres-region-03.xlsx"')
    client.force_login(nouveau_membre(territoire["P1"], "X").compte)
    assert client.get("/lots/modele/03.xlsx").status_code == 403
```

- [ ] **Step 2 : Vérifier l'échec**, **Step 3 : Implémenter**, **Step 4 : Vérifier** — `DJANGO_DEBUG=True pytest -q` → tout passe ; ouvrir le modèle généré avec LibreOffice (`soffice --headless --convert-to pdf`) et en faire une capture pour contrôle visuel.
- [ ] **Step 5 : Commit** — `feat(lots): modèle Excel officiel par région`.

---

### Task 3 : Lecture du fichier et vérification de chaque ligne

**Files:**
- Create: `apps/lots/lecture.py`, `apps/lots/controle.py`
- Modify: `apps/membres/forms.py` (extraire la validation du futur membre en une fonction réutilisable — voir Interfaces)
- Test: `apps/lots/tests/test_lecture.py`, `apps/lots/tests/test_verification.py`

**Interfaces:**
- Consumes: `COLONNES`, `LigneLot`, `EtatLigne` (tâche 1), `cle_nom`, `Membre`.
- Produces:
  - `class FichierInvalide(ValueError)` ; `lire_classeur(fichier) -> list[tuple[int, dict[str, object]]]` — renvoie `(numéro de ligne Excel, {entête: valeur})` pour chaque ligne non vide de la feuille « Membres » ; lève `FichierInvalide` avec un message en français si : pas un `.xlsx` lisible (« Ce fichier n'est pas un classeur Excel (.xlsx). Utilisez le modèle officiel. »), feuille « Membres » absente, en-têtes différents de `COLONNES` (« Les colonnes ne correspondent pas au modèle officiel : colonne {lettre} attendue « {entête} ». »), plus de 2 000 lignes, fichier de plus de 5 Mo.
  - Dans `apps/membres/forms.py` : `valider_futur_membre(donnees: dict, paroisse: Paroisse | None) -> dict[str, list[str]]` — construit un `Membre` non enregistré avec `donnees` (+ `paroisse_integration`, `region_integration`, matricule factice) et appelle `full_clean(exclude=["matricule", "compte", "enregistre_par", "photo_cip"])` ; renvoie les erreurs par champ (dictionnaire vide si tout va bien). `FormulaireEnregistrement._post_clean` l'utilise (aucun changement de comportement : les tests de l'étape 2 restent verts).
  - `normaliser_ligne(brutes: dict, region: Region) -> tuple[dict, list[str]]` — convertit les valeurs lues en `donnees` (texte nettoyé ; `sexe` « M »/« F » ; dates ; année entière ; catégorie depuis son libellé, vide → `actif` ; situation depuis son libellé ; paroisse retrouvée dans la région par `cle_nom`) et renvoie les erreurs de conversion en français préfixées par l'en-tête de colonne (ex. « Date de naissance : date invalide, écrivez JJ/MM/AAAA »).
  - `verifier_ligne(ligne: LigneLot) -> None` — `normaliser_ligne` puis `valider_futur_membre` ; remplit `ligne.donnees`, `ligne.erreurs` (messages « {Colonne} : {message} ») et met `etat = ERREUR` s'il y a des erreurs, sinon `CORRECTE` (les doublons viennent à la tâche 4) ; ne touche pas aux lignes `ecartee`.

- [ ] **Step 1 : Écrire les tests**

```python
import datetime, pytest
from apps.lots.colonnes import COLONNES
from apps.lots.controle import normaliser_ligne
from apps.lots.lecture import FichierInvalide, lire_classeur

LIGNE_OK = ["Hounkpè", "Jean-Marc", "M", "01/05/1990", "", "", "", "0197000000", "", "", "", "", "", "", "", 2015, "P1", ""]

def test_lecture_ignore_lignes_vides(classeur):
    lignes = lire_classeur(classeur([LIGNE_OK, [None] * 18, LIGNE_OK]))
    assert [n for n, _ in lignes] == [2, 4]

@pytest.mark.parametrize("contenu,message", [
    (b"nom;prenoms\nA;B", "pas un classeur Excel"),
])
def test_fichier_non_excel(contenu, message):
    from django.core.files.uploadedfile import SimpleUploadedFile
    with pytest.raises(FichierInvalide, match=message):
        lire_classeur(SimpleUploadedFile("x.xlsx", contenu))

def test_colonnes_deplacees(classeur):
    with pytest.raises(FichierInvalide, match="colonne B attendue « Prénoms* »"):
        lire_classeur(classeur([LIGNE_OK], entetes_modifiees={1: "Téléphone*"}))

@pytest.mark.parametrize("valeur,attendu", [
    (datetime.datetime(1990, 5, 1), "1990-05-01"),
    ("01/05/1990", "1990-05-01"),
    ("1990", None), ("01-05-90", None),
])
def test_dates(territoire, valeur, attendu):
    brutes = dict(zip([c.entete for c in COLONNES], LIGNE_OK))
    brutes["Date de naissance"] = valeur
    donnees, erreurs = normaliser_ligne(brutes, territoire["HOULENOU"])
    if attendu:
        assert donnees["date_naissance"] == attendu and not erreurs
    else:
        assert any("Date de naissance : date invalide, écrivez JJ/MM/AAAA" in e for e in erreurs)

def test_paroisse_ecrite_autrement_et_autre_region(territoire):
    from apps.organisation.models import Paroisse
    p = Paroisse.objects.create(circuit=territoire["Ekpe A"], nom="Paroisse Saint Michel de TOKPOTA DAVO")
    brutes = dict(zip([c.entete for c in COLONNES], LIGNE_OK))
    brutes["Paroisse d'intégration*"] = "  paroisse saint  michel de tokpota davo "
    assert normaliser_ligne(brutes, territoire["HOULENOU"])[0]["paroisse_integration"] == p.pk
    brutes["Paroisse d'intégration*"] = "P4"   # région WEME
    erreurs = normaliser_ligne(brutes, territoire["HOULENOU"])[1]
    assert any("« P4 » n'existe pas dans la région HOULENOU" in e for e in erreurs)

def test_categorie_vide_vaut_actif(territoire):
    brutes = dict(zip([c.entete for c in COLONNES], LIGNE_OK))
    assert normaliser_ligne(brutes, territoire["HOULENOU"])[0]["categorie"] == "actif"
    brutes["Catégorie"] = "Membre d'honneur"
    assert normaliser_ligne(brutes, territoire["HOULENOU"])[0]["categorie"] == "honneur"
```

`test_verification.py` : `test_ligne_correcte` ; `test_erreurs_du_modele_reutilisees` (téléphone « abc » → « Téléphone* : Numéro de téléphone invalide… » ; NPI « 12 » ; année 1800) ; `test_champs_obligatoires_vides` ; `test_npi_deja_utilise` (membre existant avec ce NPI → erreur « Ce NPI est déjà utilisé par un autre membre. ») ; `test_ligne_ecartee_non_touchee`.

- [ ] **Step 2 : Vérifier l'échec**, **Step 3 : Implémenter** (lecture avec `load_workbook(read_only=True, data_only=True)`), **Step 4 : Vérifier** — `DJANGO_DEBUG=True pytest -q` → tout passe, y compris les tests de l'étape 2.
- [ ] **Step 5 : Commit** — `feat(lots): lecture du fichier et vérification des lignes`.

---

### Task 4 : Doublons et contrôle complet du lot

**Files:**
- Modify: `apps/lots/controle.py`
- Test: `apps/lots/tests/test_doublons.py`

**Interfaces:**
- Consumes: `verifier_ligne` (tâche 3), `doublons_possibles`, `cle_nom` (étape 2).
- Produces:
  - `controler_lot(lot: Lot) -> None` — pour chaque ligne non écartée : `verifier_ligne` ; puis, pour les lignes sans erreur, cherche les doublons **avec les membres existants** (`doublons_possibles`) et **au sein du fichier** (même `cle_nom(nom)|cle_nom(prénoms)` et même date de naissance ou date absente, ou même NPI) ; une ligne avec doublon passe à `DOUBLON` (sauf si elle est déjà `GARDEE` et que ses doublons n'ont pas changé) et `ligne.doublons` liste les matricules et/ou « ligne N ».
  - `creer_lot(*, region: Region, fichier, par: Compte) -> Lot` — lit le fichier (`lire_classeur`, peut lever `FichierInvalide`), crée le `Lot` (fichier archivé, `nom_fichier`) et une `LigneLot` par ligne (`brutes`), puis `controler_lot`. Rien d'autre n'est créé.
  - `remplacer_fichier(lot: Lot, fichier, par) -> None` — lot en brouillon uniquement ; remplace toutes les lignes par celles du nouveau fichier, puis `controler_lot`.

- [ ] **Step 1 : Écrire les tests** — `test_meme_personne_deux_fois_dans_le_fichier` (deux lignes « HOUNKPÈ Jean-Marc » et « hounkpe jean marc », même date → les deux en `doublon`, `doublons` contient « ligne 2 »/« ligne 3 ») ; `test_doublon_avec_membre_existant` (contient le matricule) ; `test_creer_lot_ne_cree_aucun_membre` (`Membre`, `Compte`, `CompteurMatricule` inchangés) ; `test_fichier_invalide_aucun_lot` ; `test_remplacer_fichier`.
- [ ] **Step 2 : Vérifier l'échec**, **Step 3 : Implémenter**, **Step 4 : Vérifier** — `DJANGO_DEBUG=True pytest -q` → tout passe.
- [ ] **Step 5 : Commit** — `feat(lots): doublons et contrôle du lot`.

---

### Task 5 : Dépôt du fichier et écran de contrôle

**Files:**
- Create: `apps/lots/forms.py`, `templates/lots/{liste,deposer,controle,ligne}.html`
- Modify: `apps/lots/views.py`, `apps/lots/urls.py`, `templates/accueil.html` (lien « Enregistrer par lots (Excel) » pour le BNC), `static/css/site.css`
- Test: `apps/lots/tests/test_pages.py`

**Interfaces:**
- Consumes: `creer_lot`, `remplacer_fichier`, `controler_lot` (tâche 4), `modele_pour_region` (tâche 2).
- Produces (toutes réservées au BNC, 403 sinon) :
  - `/lots/` (`lots:liste`) : lots (n°, région, date, état, nombre de lignes) + bouton « Nouveau lot » + liens « Télécharger le modèle » par région active.
  - `/lots/nouveau/` (`lots:deposer`) : formulaire région (régions actives) + fichier ; `FichierInvalide` → message sur la page, aucun lot ; succès → `lots:controle`.
  - `/lots/<pk>/` (`lots:controle`) : résumé (nombre de lignes par état, répartition par année d'intégration et par paroisse), tableau de **toutes** les lignes telles que lues (nom, prénoms, sexe, date, paroisse, année, catégorie) avec état, erreurs et doublons (lien vers la fiche BN du membre existant) ; actions par ligne : « Corriger », « Écarter » / « Reprendre », et pour un doublon « Garder » / « Écarter » ; formulaire « Redéposer un fichier corrigé » ; bouton « Valider et générer » **désactivé** tant que `lot.validable` est faux. Un lot validé s'affiche en lecture seule.
  - `/lots/<pk>/lignes/<numero>/` (`lots:ligne`) : formulaire de correction prérempli des valeurs lues ; à l'enregistrement : `brutes` mises à jour, `corrigee_par`/`date_correction` renseignés, puis `controler_lot(lot)`.
  - POST `/lots/<pk>/lignes/<numero>/<action>/` avec `action` ∈ {`ecarter`, `reprendre`, `garder`} (`lots:action_ligne`) ; `garder` seulement pour une ligne `doublon` ; `reprendre` remet la ligne à vérifier (`controler_lot`).
  - Toute modification d'un lot `valide` → 403 ; GET sur une action → 405.

- [ ] **Step 1 : Écrire les tests** — `test_pages_reservees_au_bn` (5 URL → 403 pour un membre simple) ; `test_depot_puis_controle` (affiche « 3 lignes », « Correcte », l'erreur de la ligne fautive) ; `test_depot_fichier_invalide_message` ; `test_bouton_valider_desactive_si_erreur` (`disabled` présent) ; `test_corriger_une_ligne` (erreur → correcte après correction, `corrigee_par` renseigné) ; `test_ecarter_puis_reprendre` ; `test_garder_un_doublon` (ligne `gardee`, lot validable) ; `test_lot_valide_en_lecture_seule` (action → 403) ; `test_redeposer`.
- [ ] **Step 2 : Vérifier l'échec**, **Step 3 : Implémenter**, **Step 4 : Vérifier** — `DJANGO_DEBUG=True pytest -q` → tout passe ; captures téléphone de l'écran de contrôle (largeur 375 px, tableau défilant **dans** son cadre, pas de défilement horizontal de la page).
- [ ] **Step 5 : Commit** — `feat(lots): dépôt et écran de contrôle du lot`.

---

### Task 6 : Validation et génération tout ou rien

**Files:**
- Create: `apps/lots/generation.py`, `templates/lots/confirmer.html`, `templates/lots/resultat.html`
- Modify: `apps/membres/services.py` (`enregistrer_membre(..., notifier: bool = True)`), `apps/lots/views.py`, `apps/lots/urls.py`
- Test: `apps/lots/tests/test_generation.py`

**Interfaces:**
- Consumes: `enregistrer_membre` (étape 2), `notifier_unite`, `Unite` (étape 3), `Lot.validable`.
- Produces:
  - `enregistrer_membre(..., notifier: bool = True)` — avec `notifier=False`, pas de notification individuelle (comportement par défaut inchangé).
  - `class GenerationEchouee(Exception)` (message en français nommant la ligne).
  - `valider_lot(lot: Lot, par: Compte) -> list[Membre]` — refuse si le lot n'est pas `validable` ou n'est plus en brouillon ; verrouille le lot (`select_for_update`) pour qu'il ne soit pas validé deux fois ; dans **une seule** transaction, pour chaque ligne `correcte`/`gardee` dans l'ordre des numéros : `enregistrer_membre(donnees=…, notifier=False)` (date d'intégration : 1ᵉʳ janvier de l'année) ; en cas d'erreur sur une ligne → tout est annulé et `GenerationEchouee("Ligne {n} : {message}. Aucun membre n'a été créé.")` ; sinon `ligne.membre` renseigné, lot `valide` (`valide_par`, `date_validation`) ; après validation de la transaction : **une** notification par paroisse, circuit et région concernés : « {N} nouveaux membres dans votre périmètre (lot n° {pk}). » (« 1 nouveau membre … » au singulier).
  - `/lots/<pk>/confirmer/` (`lots:confirmer`) : GET → récapitulatif (« 47 membres vont être créés pour la région 03 : 30 intégrés en 2026, 17 en 2015 ») et case « Je confirme » ; POST sans la case → message « Cochez la case pour confirmer. » ; POST confirmé → `valider_lot` → `lots:resultat` ; `GenerationEchouee` → message sur la page de contrôle.
  - `/lots/<pk>/resultat/` (`lots:resultat`) : liste des membres créés (nom → matricule) et deux boutons de la tâche 7.

- [ ] **Step 1 : Écrire les tests**

```python
def test_generation_complete(lot_pret, compte_technique, django_capture_on_commit_callbacks):
    with django_capture_on_commit_callbacks(execute=True):
        membres = valider_lot(lot_pret, compte_technique)
    assert [m.matricule for m in membres] == ["2015-03AS-0001", "2015-03AS-0002"]
    lot_pret.refresh_from_db(); assert lot_pret.etat == "valide"
    assert all(l.membre for l in lot_pret.lignes.filter(etat__in=["correcte", "gardee"]))

def test_tout_ou_rien(lot_pret, compte_technique):
    from apps.membres.models import CompteurMatricule
    CompteurMatricule.objects.create(annee=2015, region=lot_pret.region, dernier_numero=9998)
    with pytest.raises(GenerationEchouee, match="Ligne 3 .* Aucun membre n'a été créé"):
        valider_lot(lot_pret, compte_technique)
    assert Membre.objects.count() == 0
    assert CompteurMatricule.objects.get(annee=2015).dernier_numero == 9998
    lot_pret.refresh_from_db(); assert lot_pret.etat == "brouillon"

def test_une_notification_par_bureau(lot_pret, secretaire_p1, compte_technique, django_capture_on_commit_callbacks):
    with django_capture_on_commit_callbacks(execute=True):
        valider_lot(lot_pret, compte_technique)
    msgs = list(Notification.objects.filter(destinataire=secretaire_p1.compte).values_list("message", flat=True))
    assert msgs == [f"2 nouveaux membres dans votre périmètre (lot n° {lot_pret.pk})."]

def test_lot_non_validable_refuse(...) ; test_double_validation_refusee(...) ; test_confirmation_exige_la_case(...)
```

(fixtures `lot_pret` : lot de la région 03 avec deux lignes correctes de 2015 aux numéros 2 et 3 ; `secretaire_p1` : titulaire « Secrétaire paroissial » de P1.)

- [ ] **Step 2 : Vérifier l'échec**, **Step 3 : Implémenter**, **Step 4 : Vérifier** — `DJANGO_DEBUG=True pytest -q` → tout passe (y compris les tests de notifications de l'étape 3).
- [ ] **Step 5 : Commit** — `feat(lots): validation et génération tout ou rien`.

---

### Task 7 : Fiches PDF du lot et liste récapitulative

**Files:**
- Create: `apps/lots/pdf.py`
- Modify: `apps/lots/views.py`, `apps/lots/urls.py`, `apps/membres/pdf.py` (extraire le dessin d'une fiche sur un `canvas` existant pour pouvoir enchaîner plusieurs fiches dans un même PDF ; `fiche_identification_pdf` garde sa signature)
- Test: `apps/lots/tests/test_pdf_lot.py`

**Interfaces:**
- Consumes: `fiche_identification_pdf` / le dessin d'une fiche (étape 2), `generer_mot_de_passe_provisoire`, `Lot` validé.
- Produces:
  - `dessiner_fiche(c: Canvas, membre: Membre, mot_de_passe: str | None) -> None` dans `apps/membres/pdf.py` (une page).
  - `fiches_du_lot_pdf(lot: Lot, par: Compte) -> bytes` — pour chaque membre créé par le lot : **nouveau** mot de passe provisoire (comme l'impression individuelle), `doit_changer_mot_de_passe=True`, une page de fiche **avec** identifiants ; le PDF est construit avant d'enregistrer les mots de passe ; tout dans une transaction.
  - `recapitulatif_pdf(lot: Lot) -> bytes` — en-tête officiel, « Lot n° X — Région … — validé le … », tableau N°, matricule, nom et prénoms, paroisse, catégorie ; **sans** mot de passe ; pied « Généré le … ».
  - POST `/lots/<pk>/fiches.pdf` (`lots:fiches`) avec avertissement « Attention : de nouveaux mots de passe provisoires remplacent les anciens. » ; GET `/lots/<pk>/recapitulatif.pdf` (`lots:recapitulatif`) ; lot non validé → 404.

- [ ] **Step 1 : Écrire les tests** — `test_fiches_du_lot_une_page_par_membre_et_mots_de_passe_valides` (pypdf : nombre de pages = nombre de membres ; chaque page contient le matricule et un mot de passe qui fonctionne pour ce compte ; GET → 405) ; `test_recapitulatif_sans_mot_de_passe` ; `test_lot_brouillon_404` ; `test_fiche_individuelle_inchangee` (les tests PDF de l'étape 2 restent verts).
- [ ] **Step 2 : Vérifier l'échec**, **Step 3 : Implémenter**, **Step 4 : Vérifier** — `DJANGO_DEBUG=True pytest -q` → tout passe ; capture du récapitulatif.
- [ ] **Step 5 : Commit** — `feat(lots): fiches PDF du lot et liste récapitulative`.

---

### Task 8 : Documentation et vérification finale

**Files:**
- Modify: `docs/guide-maintenance.md` (« Enregistrer par lots : le circuit région → Secrétaire national → site »), `CLAUDE.md` (application `apps/lots`, règle « aucune création avant validation »), `apps/lots/admin.py`
- Create: `docs/guide-lots-regions.md` — fiche d'une page **pour les régions** : télécharger le modèle, le remplir (colonnes, dates, paroisses, catégorie), l'envoyer au Secrétaire national ; erreurs fréquentes.

- [ ] **Step 1 : Rédiger la documentation.**
- [ ] **Step 2 : Vérifier** — `DJANGO_DEBUG=True pytest -q && ruff check . && python manage.py makemigrations --check --dry-run` → tout passe ; suite complète sur PostgreSQL.
- [ ] **Step 3 : Commit et push** — `docs(lots): guides de l'enregistrement par lots`.

---

## Hors de cette étape (rappel)

Photos d'identité des membres d'un lot (déposées ensuite par chaque membre, étape 2) ; listes et statistiques (étape 5) ; journal des actions, dont les corrections de lignes (étape 7 — en attendant, `corrigee_par` et `date_correction` sont gardés sur la ligne).
