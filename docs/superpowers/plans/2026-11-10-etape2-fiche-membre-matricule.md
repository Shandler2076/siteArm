# Étape 2 — Fiche membre, matricule, fiche PDF et photo : plan de réalisation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enregistrer un membre (par le BN) avec génération automatique et verrouillée du matricule `AAAA-RRAS-NNNN`, création de son compte, fiche d'identification PDF aux logos, espace « Ma fiche » du membre, dépôt de la photo en tenue et validation par le BN.

**Architecture:** Nouvelle application `apps/membres` : modèles `Membre`, `CompteurMatricule`, `Affectation`, `PhotoIdentite` ; services purs dans `services.py` (matricule, enregistrement, doublons) appelés par des vues minces ; PDF généré avec ReportLab ; fichiers sensibles (photo, CIP) dans un stockage **privé** servi uniquement par des vues qui contrôlent les droits. En attendant les mandats (étape 3), l'accès « BN » est porté par la permission Django `membres.gerer_membres` ; l'étape 3 la reliera aux mandats.

**Tech Stack:** Django 5.2, PostgreSQL (verrou `select_for_update`), ReportLab (PDF), Pillow (images), pypdf (tests), pytest.

**Spec:** `docs/superpowers/specs/2026-11-09-module1-fondations-design.md` — sections 3 (fiche, matricule, statuts, photo, qui modifie quoi, catégorie), 4 (parcours), 6.1 (enregistrement individuel), 8 (espaces), 9.4, 13 étape 2.

## Global Constraints

- Matricule : `AAAA-RRAS-NNNN`, ex. `2015-01AS-0157` ; `AAAA` = année d'intégration, `RR` = code de la **région d'intégration**, `AS` fixe, `NNNN` = numéro d'ordre sur 4 chiffres, **compteur distinct par (année, région)** commençant à 0001 ; pris et incrémenté **dans une seule opération verrouillée** ; définitif ; 9 999 au plus par (année, région).
- Le matricule ne contient ni la paroisse ni le nom de la région et ne change jamais (ni à la mutation, ni au changement de catégorie).
- Catégorie : `actif` (défaut), `honneur`, `sympathisant` ; libellés « Membre actif », « Membre d'honneur », « Membre sympathisant » ; case toujours présente à l'enregistrement.
- Statuts : `actif` (défaut), `sanctionne`, `exclu`, `demissionnaire`, `decede` ; libellés « Actif », « Sanctionné », « Exclu », « Démissionnaire », « Décédé ».
- Année, paroisse et région d'intégration : **non modifiables** après l'enregistrement (aucun formulaire ne les expose en modification).
- Le membre ne modifie que : téléphone, WhatsApp, email, quartier, ville, profession, personne à contacter (nom, téléphone). Tout autre champ envoyé est ignoré.
- Photo : déposée par le membre ; JPEG ou PNG ; 5 Mo au plus ; au moins 300 × 300 px ; **validée uniquement par le BN** ; tant qu'elle n'est pas acceptée, l'ancienne photo acceptée (ou rien) reste affichée.
- Photo du CIP : visible **uniquement** avec la permission `membres.voir_cip` (BN).
- Fichiers privés hors de `static/` et sans URL publique ; dossier local `prive/` ignoré par git.
- Le mot de passe provisoire n'est **jamais stocké en clair** : il n'apparaît que dans la fiche PDF générée au moment où il est créé.
- Tout texte visible en français ; pages pensées pour le téléphone (gabarit `base.html`).

## Review Focus

1. **Deux enregistrements simultanés pour la même année et la même région** : deux matricules différents et consécutifs, jamais deux fois le même → test concurrent dans la tâche 2 (exécuté sur PostgreSQL en CI).
2. **10 000ᵉ membre d'une même année et région** : message clair en français, rien n'est créé (ni membre, ni compte, ni compteur avancé) → test dans la tâche 2 et la tâche 3.
3. **Doublon écrit autrement** (« HOUNKPÈ Jean-Marc » contre « Hounkpe  jean-marc ») : signalé comme doublon possible → test dans la tâche 3.
4. **Membre qui envoie des champs protégés** (nom, matricule, année d'intégration) dans le formulaire de ses coordonnées : ignorés → test dans la tâche 6.
5. **Fichier qui n'est pas une image renommé en `.jpg`, ou image trop grande/trop petite** : refusé avec un message en français, rien n'est enregistré ; et un membre qui tente d'ouvrir la photo d'un autre membre reçoit 404 → tests dans la tâche 7.

---

## Structure des fichiers

```
apps/membres/
  models.py          # Membre, CompteurMatricule, Affectation, PhotoIdentite, choix
  services.py        # attribuer_matricule, enregistrer_membre, doublons_possibles,
                     # generer_mot_de_passe_provisoire, cle_nom
  stockage.py        # stockage_prive (FileSystemStorage sur PRIVATE_MEDIA_ROOT)
  images.py          # verifier_et_preparer_photo
  pdf.py             # fiche_identification_pdf
  forms.py           # FormulaireEnregistrement, FormulaireCoordonnees, FormulairePhoto
  views_bn.py        # enregistrement, confirmation, fiche PDF, file des photos
  views_membre.py    # ma fiche, coordonnées, ma fiche PDF, dépôt photo
  views_fichiers.py  # service des fichiers privés (photo, CIP)
  urls.py  admin.py
  tests/
templates/membres/   # gabarits des pages ci-dessus
static/img/          # logos (déjà présents)
```

---

### Task 1 : Modèles du membre

**Files:**
- Create: `apps/membres/__init__.py`, `apps/membres/apps.py`, `apps/membres/models.py`, `apps/membres/stockage.py`, `apps/membres/migrations/__init__.py`
- Modify: `config/settings.py` (`apps.membres`, `PRIVATE_MEDIA_ROOT = BASE_DIR / "prive"`), `.gitignore` (`prive/`)
- Test: `apps/membres/tests/test_modeles.py`

**Interfaces:**
- Consumes: `organisation.Region`, `Circuit`, `Paroisse` ; `comptes.Compte`.
- Produces (`apps.membres.models`) :
  - Choix `Sexe` (`M` « Masculin », `F` « Féminin »), `SituationMatrimoniale` (`celibataire`, `marie`, `veuf`, `divorce` — « Célibataire », « Marié(e) », « Veuf / veuve », « Divorcé(e) »), `Categorie`, `Statut` (valeurs des Global Constraints).
  - `Membre` : `nom` (100), `prenoms` (150), `sexe`, `date_naissance` (null), `lieu_naissance` (blank), `situation_matrimoniale` (blank), `npi` (10 chiffres, `^\d{10}$`, blank, **unique si renseigné** via `UniqueConstraint(condition=~Q(npi=""))`), `photo_cip` (`FileField(storage=stockage_prive, upload_to="cip/", blank=True)`), `telephone` (requis, `^\+?[0-9 ]{8,20}$`), `whatsapp`, `email` (blank), `quartier`, `ville`, `profession`, `urgence_nom`, `urgence_telephone` (blank), `annee_integration` (`PositiveSmallIntegerField`, 1900 ≤ année ≤ année en cours, validé dans `clean()`), `paroisse_integration` (FK `Paroisse`, PROTECT), `region_integration` (FK `Region`, PROTECT), `matricule` (`CharField(14, unique=True)`), `categorie` (défaut `actif`), `statut` (défaut `actif`), `compte` (`OneToOneField(Compte, null=True, on_delete=PROTECT, related_name="membre")`), `date_enregistrement` (auto), `enregistre_par` (FK `Compte`, null, SET_NULL, related_name="+").
    Méthodes : `nom_complet -> str` (`"HOUNKPÈ Jean-Marc"` : nom en majuscules + prénoms), `age(aujourdhui: date | None = None) -> int | None`, `affectation_actuelle -> Affectation | None`, `photo_acceptee -> PhotoIdentite | None`. `Meta.permissions = [("gerer_membres", "Gérer les membres (Bureau national)"), ("voir_cip", "Voir la photo du CIP")]`. `delete()` lève `PermissionDenied`.
  - `CompteurMatricule` : `annee` (PositiveSmallInteger), `region` (FK Region, PROTECT), `dernier_numero` (PositiveSmallInteger, défaut 0) ; unique `(annee, region)`.
  - `Affectation` : `membre` (FK, related_name="affectations"), `paroisse` (FK PROTECT), `circuit_a_date` (FK Circuit PROTECT), `region_a_date` (FK Region PROTECT), `date_debut`, `date_fin` (null), `motif` (CharField 200) ; tri par `date_debut` ; contrainte : une seule affectation sans `date_fin` par membre (`UniqueConstraint(fields=["membre"], condition=Q(date_fin=None))`).
  - `PhotoIdentite` : `membre` (FK, related_name="photos"), `fichier` (`ImageField(storage=stockage_prive, upload_to="photos/")`), `etat` (`en_attente` « En attente », `acceptee` « Acceptée », `refusee` « Refusée »), `motif_refus` (blank), `date_depot` (auto), `date_decision` (null), `decide_par` (FK Compte, null, SET_NULL, related_name="+").

- [ ] **Step 1 : Écrire les tests**

```python
import datetime
import pytest
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError
from apps.membres.models import Affectation, Categorie, Membre, Statut

@pytest.fixture
def paroisse(db):
    from apps.organisation.models import Circuit, Paroisse, Region
    r = Region.objects.create(code="01", nom="PORTO-NOVO")
    return Paroisse.objects.create(circuit=Circuit.objects.create(region=r, nom="Davo"), nom="P1")

def _membre(paroisse, **kw):
    d = dict(nom="Hounkpè", prenoms="Jean-Marc", sexe="M", telephone="0197000000",
             annee_integration=2015, paroisse_integration=paroisse,
             region_integration=paroisse.region, matricule="2015-01AS-0001")
    d.update(kw)
    return Membre.objects.create(**d)

def test_valeurs_par_defaut(paroisse):
    m = _membre(paroisse)
    assert m.categorie == Categorie.ACTIF and m.statut == Statut.ACTIF
    assert m.get_categorie_display() == "Membre actif"

def test_nom_complet_et_age(paroisse):
    m = _membre(paroisse, date_naissance=datetime.date(2000, 11, 11))
    assert m.nom_complet == "HOUNKPÈ Jean-Marc"
    assert m.age(datetime.date(2026, 11, 10)) == 25
    assert m.age(datetime.date(2026, 11, 11)) == 26
    assert _membre(paroisse, matricule="2015-01AS-0002").age() is None

def test_npi_unique_si_renseigne(paroisse):
    _membre(paroisse, npi="", matricule="2015-01AS-0001")
    _membre(paroisse, npi="", matricule="2015-01AS-0002")
    _membre(paroisse, npi="1234567890", matricule="2015-01AS-0003")
    with pytest.raises(IntegrityError):
        _membre(paroisse, npi="1234567890", matricule="2015-01AS-0004")

@pytest.mark.parametrize("annee", [1899, datetime.date.today().year + 1])
def test_annee_integration_invalide(paroisse, annee):
    m = Membre(nom="A", prenoms="B", sexe="F", telephone="0197000000", annee_integration=annee,
               paroisse_integration=paroisse, region_integration=paroisse.region, matricule="X")
    with pytest.raises(ValidationError):
        m.full_clean()

def test_une_seule_affectation_ouverte(paroisse):
    m = _membre(paroisse)
    kw = dict(membre=m, paroisse=paroisse, circuit_a_date=paroisse.circuit,
              region_a_date=paroisse.region, date_debut=datetime.date(2015, 1, 1), motif="Intégration")
    Affectation.objects.create(**kw)
    with pytest.raises(IntegrityError):
        Affectation.objects.create(**kw)

def test_suppression_interdite(paroisse):
    with pytest.raises(PermissionDenied):
        _membre(paroisse).delete()
```

- [ ] **Step 2 : Vérifier l'échec** — Run: `DJANGO_DEBUG=True pytest apps/membres -q` → FAIL (`ModuleNotFoundError`).
- [ ] **Step 3 : Implémenter modèles, stockage privé, réglages et migration.**
- [ ] **Step 4 : Vérifier** — Run: `DJANGO_DEBUG=True pytest -q && ruff check .` → tout passe.
- [ ] **Step 5 : Commit** — `feat(membres): modèles Membre, CompteurMatricule, Affectation, PhotoIdentite`.

---

### Task 2 : Attribution verrouillée du matricule

**Files:**
- Create: `apps/membres/services.py`
- Test: `apps/membres/tests/test_matricule.py`

**Interfaces:**
- Consumes: `CompteurMatricule`, `Region` (tâche 1).
- Produces:
  - `class CapaciteMatriculeAtteinte(Exception)` — message : « Le nombre maximal de 9 999 matricules est atteint pour l'année {annee} dans la région {code}. »
  - `attribuer_matricule(annee: int, region: Region) -> str` — doit être appelée **dans** une transaction (`transaction.atomic`) ; `CompteurMatricule.objects.select_for_update().get_or_create(annee=annee, region=region)` ; incrémente `dernier_numero` ; lève `CapaciteMatriculeAtteinte` si le numéro dépasserait 9 999 (compteur inchangé) ; renvoie `f"{annee:04d}-{region.code}AS-{numero:04d}"`.
  - Pour éviter la course sur `get_or_create` du premier compteur : créer d'abord avec `get_or_create` hors verrou puis relire avec `select_for_update()` (ou attraper `IntegrityError` et relire).

- [ ] **Step 1 : Écrire les tests**

```python
import threading
import pytest
from django.db import connection, transaction
from apps.membres.models import CompteurMatricule
from apps.membres.services import CapaciteMatriculeAtteinte, attribuer_matricule
from apps.organisation.models import Region

@pytest.fixture
def region(db):
    return Region.objects.create(code="01", nom="PORTO-NOVO")

def _attribuer(annee, region):
    with transaction.atomic():
        return attribuer_matricule(annee, region)

def test_format_et_suite(region):
    assert _attribuer(2015, region) == "2015-01AS-0001"
    assert _attribuer(2015, region) == "2015-01AS-0002"

def test_compteurs_separes_par_annee_et_region(region):
    autre = Region.objects.create(code="02", nom="COTONOU")
    _attribuer(2015, region)
    assert _attribuer(2016, region) == "2016-01AS-0001"
    assert _attribuer(2015, autre) == "2015-02AS-0001"

def test_capacite_atteinte(region):
    CompteurMatricule.objects.create(annee=2015, region=region, dernier_numero=9999)
    with pytest.raises(CapaciteMatriculeAtteinte, match="9 999"):
        _attribuer(2015, region)
    assert CompteurMatricule.objects.get(annee=2015, region=region).dernier_numero == 9999

@pytest.mark.django_db(transaction=True)
def test_attributions_simultanees_sans_doublon():
    if connection.vendor != "postgresql":
        pytest.skip("Le verrou de ligne n'est vérifiable que sur PostgreSQL.")
    region = Region.objects.create(code="01", nom="PORTO-NOVO")
    resultats, erreurs = [], []
    def travail():
        try:
            resultats.append(_attribuer(2026, region))
        except Exception as e:  # noqa: BLE001
            erreurs.append(e)
        finally:
            connection.close()
    fils = [threading.Thread(target=travail) for _ in range(20)]
    for f in fils: f.start()
    for f in fils: f.join()
    assert not erreurs
    assert sorted(resultats) == [f"2026-01AS-{i:04d}" for i in range(1, 21)]
```

- [ ] **Step 2 : Vérifier l'échec** — Run: `DJANGO_DEBUG=True pytest apps/membres/tests/test_matricule.py -q` → FAIL (import).
- [ ] **Step 3 : Implémenter `attribuer_matricule`.**
- [ ] **Step 4 : Vérifier sur SQLite puis PostgreSQL** — Run: `DJANGO_DEBUG=True pytest -q` (le test concurrent est « skipped ») puis, avec un PostgreSQL local, `DATABASE_URL=postgres://… pytest apps/membres/tests/test_matricule.py -q` → 4 passed (aucun skip).
- [ ] **Step 5 : Commit** — `feat(membres): attribution verrouillée du matricule`.

---

### Task 3 : Enregistrement d'un membre, doublons et mot de passe provisoire

**Files:**
- Modify: `apps/membres/services.py`
- Test: `apps/membres/tests/test_enregistrement.py`

**Interfaces:**
- Consumes: `attribuer_matricule` (tâche 2), `Compte.objects.create_user` (étape 1), modèles (tâche 1).
- Produces:
  - `cle_nom(texte: str) -> str` — sans accents (`unicodedata` NFKD), majuscules, tirets et espaces multiples ramenés à un espace, sans espaces autour.
  - `doublons_possibles(*, nom: str, prenoms: str, date_naissance: date | None, npi: str = "") -> QuerySet[Membre]` — membres avec le même NPI (si fourni) **ou** même `cle_nom(nom)` + `cle_nom(prenoms)` + même date de naissance (si fournie) ; la comparaison des noms se fait en Python sur les membres de même date de naissance (ou même nom exact en base si pas de date) — volume faible.
  - `generer_mot_de_passe_provisoire() -> str` — 10 caractères tirés avec `secrets` de l'alphabet `ABCDEFGHJKLMNPQRSTUVWXYZabcdefghjkmnpqrstuvwxyz23456789`, contenant au moins une majuscule, une minuscule et un chiffre ; passe `validate_password`.
  - `@dataclass(frozen=True) class ResultatEnregistrement: membre: Membre; mot_de_passe: str`
  - `enregistrer_membre(*, donnees: dict, paroisse_integration: Paroisse, annee_integration: int, par: Compte, date_integration: date | None = None) -> ResultatEnregistrement` — dans **une seule** transaction : `matricule = attribuer_matricule(annee_integration, paroisse_integration.region)` ; crée le `Compte` (`identifiant=matricule`, `nom_affiche=membre.nom_complet`, `doit_changer_mot_de_passe=True`) avec le mot de passe provisoire ; crée le `Membre` (`region_integration = paroisse_integration.region`, `enregistre_par=par`) ; crée l'`Affectation` initiale (`date_debut = date_integration or date(annee_integration, 1, 1)`, `motif="Intégration"`, circuit et région de la paroisse **à cette date**). Toute erreur annule tout (aucun compteur avancé, aucun compte créé). `donnees` contient les champs d'identité, de contact, autres et `categorie`.

- [ ] **Step 1 : Écrire les tests**

```python
import datetime
import pytest
from django.contrib.auth.password_validation import validate_password
from apps.comptes.models import Compte
from apps.membres.models import CompteurMatricule, Membre
from apps.membres.services import (CapaciteMatriculeAtteinte, cle_nom, doublons_possibles,
    enregistrer_membre, generer_mot_de_passe_provisoire)

@pytest.fixture
def contexte(db):
    from apps.organisation.models import Circuit, Paroisse, Region
    r = Region.objects.create(code="03", nom="HOULENOU")
    p = Paroisse.objects.create(circuit=Circuit.objects.create(region=r, nom="Ekpe A"), nom="P1")
    bn = Compte.objects.create_superuser("tech", "MotDePasse!2026")
    return p, bn

DONNEES = dict(nom="Hounkpè", prenoms="Jean-Marc", sexe="M", telephone="0197000000",
               date_naissance=datetime.date(1990, 5, 1), categorie="honneur")

def _enregistrer(p, bn, annee=2015, **extra):
    return enregistrer_membre(donnees={**DONNEES, **extra}, paroisse_integration=p,
                              annee_integration=annee, par=bn)

def test_enregistrement_complet(contexte):
    p, bn = contexte
    res = _enregistrer(p, bn)
    m = res.membre
    assert m.matricule == "2015-03AS-0001" and m.region_integration.code == "03"
    assert m.categorie == "honneur" and m.statut == "actif"
    assert m.compte.identifiant == "2015-03AS-0001"
    assert m.compte.doit_changer_mot_de_passe and m.compte.check_password(res.mot_de_passe)
    a = m.affectation_actuelle
    assert a.paroisse == p and a.circuit_a_date == p.circuit and a.region_a_date.code == "03"
    assert a.date_debut == datetime.date(2015, 1, 1) and a.motif == "Intégration"

def test_echec_n_avance_pas_le_compteur(contexte):
    p, bn = contexte
    with pytest.raises(Exception):
        _enregistrer(p, bn, sexe="X_INVALIDE_TROP_LONG")
    assert not CompteurMatricule.objects.filter(dernier_numero__gt=0).exists()
    assert not Compte.objects.exclude(identifiant="TECH").exists()

def test_capacite_atteinte_rien_n_est_cree(contexte):
    p, bn = contexte
    CompteurMatricule.objects.create(annee=2015, region=p.region, dernier_numero=9999)
    with pytest.raises(CapaciteMatriculeAtteinte):
        _enregistrer(p, bn)
    assert Membre.objects.count() == 0

def test_cle_nom():
    assert cle_nom("  Hounkpè  Jean-Marc ") == cle_nom("HOUNKPE jean marc") == "HOUNKPE JEAN MARC"

def test_doublon_ecrit_autrement(contexte):
    p, bn = contexte
    _enregistrer(p, bn)
    assert doublons_possibles(nom="HOUNKPE", prenoms="jean  marc",
                              date_naissance=datetime.date(1990, 5, 1)).count() == 1
    assert doublons_possibles(nom="HOUNKPE", prenoms="Paul",
                              date_naissance=datetime.date(1990, 5, 1)).count() == 0

def test_doublon_par_npi(contexte):
    p, bn = contexte
    _enregistrer(p, bn, npi="1234567890")
    assert doublons_possibles(nom="Autre", prenoms="Nom", date_naissance=None,
                              npi="1234567890").count() == 1

def test_mot_de_passe_provisoire_valide():
    for _ in range(50):
        mdp = generer_mot_de_passe_provisoire()
        assert len(mdp) == 10 and not set(mdp) & set("0O1lI")
        validate_password(mdp)
```

- [ ] **Step 2 : Vérifier l'échec** — Run: `DJANGO_DEBUG=True pytest apps/membres/tests/test_enregistrement.py -q` → FAIL.
- [ ] **Step 3 : Implémenter les services** (appeler `full_clean()` sur le membre avant `save()` pour que le sexe invalide échoue dans la transaction).
- [ ] **Step 4 : Vérifier** — Run: `DJANGO_DEBUG=True pytest -q` → tout passe.
- [ ] **Step 5 : Commit** — `feat(membres): enregistrement d'un membre, doublons et mot de passe provisoire`.

---

### Task 4 : Pages du BN — enregistrer un membre

**Files:**
- Create: `apps/membres/forms.py`, `apps/membres/views_bn.py`, `apps/membres/urls.py`, `templates/membres/bn_enregistrer.html`, `templates/membres/bn_confirmation.html`, `templates/membres/bn_fiche.html`
- Modify: `config/urls.py` (`path("membres/", include("apps.membres.urls"))`), `templates/accueil.html` (lien « Enregistrer un membre » si `perms.membres.gerer_membres`), `static/css/site.css`
- Test: `apps/membres/tests/test_pages_bn.py`, `apps/membres/tests/conftest.py` (fixtures partagées `paroisse`, `bn`, `client_bn`, `admin_client_tech` — les tests ci-dessous utilisent `bn` qui connecte `client`)

**Interfaces:**
- Consumes: `enregistrer_membre`, `doublons_possibles`, `ResultatEnregistrement` (tâche 3).
- Produces:
  - `FormulaireEnregistrement(forms.ModelForm)` — champs du membre (identité, NPI, photo du CIP, contact, autres) + `annee_integration` + `paroisse_integration` (`ModelChoiceField` sur les paroisses **actives**, libellé « Paroisse — Circuit — Région ») + `categorie` (`RadioSelect`, initial `actif`, obligatoire) + champ caché `confirmer_malgre_doublon` (bool).
  - URL `membres:bn_enregistrer` → `/membres/bn/enregistrer/` (GET/POST, permission `membres.gerer_membres`, sinon 403). Si des doublons possibles existent et que `confirmer_malgre_doublon` est faux : la page se réaffiche avec l'encadré « Doublons possibles » (matricule, nom complet, date de naissance, paroisse actuelle) et un bouton « Enregistrer quand même ». Sinon : `enregistrer_membre(...)`, puis redirection vers `membres:bn_fiche` avec message « Membre enregistré : matricule {matricule} ».
  - URL `membres:bn_fiche` → `/membres/bn/<matricule>/` (permission `gerer_membres`) : récapitulatif de la fiche, bouton POST « Imprimer la fiche avec identifiants » (tâche 5).
  - Erreur `CapaciteMatriculeAtteinte` : message d'erreur en français sur la page, rien n'est créé.

- [ ] **Step 1 : Écrire les tests**

```python
import pytest
from django.contrib.auth.models import Permission
from apps.comptes.models import Compte
from apps.membres.models import Membre

URL = "/membres/bn/enregistrer/"

@pytest.fixture
def paroisse(db):
    from apps.organisation.models import Circuit, Paroisse, Region
    r = Region.objects.create(code="03", nom="HOULENOU")
    return Paroisse.objects.create(circuit=Circuit.objects.create(region=r, nom="Ekpe A"), nom="P1")

@pytest.fixture
def bn(client, db):
    c = Compte.objects.create_user("BN1", "MotDePasse!2026", doit_changer_mot_de_passe=False)
    c.user_permissions.add(Permission.objects.get(codename="gerer_membres"))
    client.force_login(c)
    return c

def _post(client, paroisse, **extra):
    d = {"nom": "Hounkpè", "prenoms": "Jean-Marc", "sexe": "M", "telephone": "0197000000",
         "date_naissance": "1990-05-01", "annee_integration": "2015",
         "paroisse_integration": paroisse.pk, "categorie": "actif"}
    d.update(extra)
    return client.post(URL, d)

def test_refuse_sans_permission(client, db):
    client.force_login(Compte.objects.create_user("X", "MotDePasse!2026", doit_changer_mot_de_passe=False))
    assert client.get(URL).status_code == 403

def test_categorie_presente_et_preselectionnee(client, bn, paroisse):
    html = client.get(URL).content.decode()
    assert 'name="categorie"' in html and "Membre d" in html and "Membre sympathisant" in html
    assert 'value="actif" checked' in html or 'value="actif"\n' in html  # case pré-cochée

def test_enregistrement_redirige_vers_la_fiche(client, bn, paroisse):
    r = _post(client, paroisse)
    assert r.status_code == 302 and r.url == "/membres/bn/2015-03AS-0001/"
    assert Membre.objects.get().enregistre_par == bn

def test_doublon_demande_confirmation(client, bn, paroisse):
    _post(client, paroisse)
    r = _post(client, paroisse, nom="HOUNKPE", prenoms="jean marc")
    assert r.status_code == 200 and "Doublons possibles" in r.content.decode()
    assert Membre.objects.count() == 1
    r = _post(client, paroisse, nom="HOUNKPE", prenoms="jean marc", confirmer_malgre_doublon="on")
    assert r.status_code == 302 and Membre.objects.count() == 2
```

- [ ] **Step 2 : Vérifier l'échec** — Run: `DJANGO_DEBUG=True pytest apps/membres/tests/test_pages_bn.py -q` → FAIL (404).
- [ ] **Step 3 : Implémenter formulaire, vues, URL, gabarits** (ajuster l'assertion « pré-cochée » à la sortie réelle du `RadioSelect` : l'input `value="actif"` porte l'attribut `checked`).
- [ ] **Step 4 : Vérifier** — Run: `DJANGO_DEBUG=True pytest -q` → tout passe.
- [ ] **Step 5 : Capture téléphone** de `/membres/bn/enregistrer/` (375 px, sans défilement horizontal) dans `docs/captures/`.
- [ ] **Step 6 : Commit** — `feat(membres): enregistrement d'un membre par le BN`.

---

### Task 5 : Fiche d'identification PDF

**Files:**
- Create: `apps/membres/pdf.py`
- Modify: `apps/membres/views_bn.py`, `apps/membres/urls.py`, `requirements.txt` (`reportlab>=4.2`, `Pillow>=10`), `requirements-dev.txt` (`pypdf>=5`)
- Test: `apps/membres/tests/test_pdf.py`

**Interfaces:**
- Consumes: `Membre` (tâche 1), `generer_mot_de_passe_provisoire` (tâche 3), logos `static/img/logo-armee-du-salut.png` et `static/img/logo-congregation.png`.
- Produces:
  - `fiche_identification_pdf(membre: Membre, mot_de_passe: str | None = None) -> bytes` — A4 portrait : en-tête avec logo de l'Armée du Salut à gauche et logo de la Congrégation à droite, titre « ARMÉE DU SALUT DU BÉNIN — FICHE D'IDENTIFICATION », devise « FOI – AMOUR – JUSTICE » ; cadre photo (photo acceptée, sinon cadre « Photo à venir ») ; tableau : matricule (en grand), nom et prénoms, sexe, date et lieu de naissance, catégorie, statut, année d'intégration, paroisse / circuit / région actuels, paroisse et région d'intégration, téléphone ; si `mot_de_passe` : encadré « Vos identifiants de connexion » (identifiant = matricule, mot de passe provisoire, adresse du site `settings.SITE_URL`, « À changer à la première connexion ») ; pied : « Généré le JJ/MM/AAAA à HH:MM ». Couleurs du site (marine `#14284B`, rouge `#B3122E`, or `#D4A017`). Police intégrée Helvetica (ReportLab gère les accents latins).
  - Réglage `SITE_URL` (variable `DJANGO_SITE_URL`, défaut `http://127.0.0.1:8000`).
  - URL `membres:bn_fiche_identifiants` → POST `/membres/bn/<matricule>/fiche-identifiants.pdf` (permission `gerer_membres`) : génère un **nouveau** mot de passe provisoire, l'enregistre (haché) sur le compte, remet `doit_changer_mot_de_passe=True`, renvoie le PDF (`Content-Disposition: attachment; filename="fiche-<matricule>.pdf"`). La page `bn_fiche` avertit : « Attention : un nouveau mot de passe provisoire remplace l'ancien. » GET → 405.
  - URL `membres:bn_fiche_pdf` → GET `/membres/bn/<matricule>/fiche.pdf` : fiche **sans** identifiants.

- [ ] **Step 1 : Écrire les tests**

```python
import io
import pytest
from pypdf import PdfReader
from apps.membres.pdf import fiche_identification_pdf

def _texte(pdf_bytes):
    return " ".join(p.extract_text() for p in PdfReader(io.BytesIO(pdf_bytes)).pages)

def test_fiche_sans_identifiants(membre_enregistre):   # fixture dans conftest.py (membre via enregistrer_membre)
    pdf = fiche_identification_pdf(membre_enregistre.membre)
    assert pdf.startswith(b"%PDF")
    t = _texte(pdf)
    assert "2015-03AS-0001" in t and "HOUNKPÈ Jean-Marc" in t and "FICHE D'IDENTIFICATION" in t
    assert "Mot de passe" not in t

def test_fiche_avec_identifiants(membre_enregistre):
    t = _texte(fiche_identification_pdf(membre_enregistre.membre, mot_de_passe="Ab3defGh7k"))
    assert "Ab3defGh7k" in t and "première connexion" in t

def test_impression_avec_identifiants_change_le_mot_de_passe(client_bn, membre_enregistre):
    m = membre_enregistre.membre
    url = f"/membres/bn/{m.matricule}/fiche-identifiants.pdf"
    assert client_bn.get(url).status_code == 405
    r = client_bn.post(url)
    assert r.status_code == 200 and r["Content-Type"] == "application/pdf"
    m.compte.refresh_from_db()
    assert not m.compte.check_password(membre_enregistre.mot_de_passe)
    assert m.compte.doit_changer_mot_de_passe
    mdp = [w for w in _texte(r.content).split() if len(w) == 10 and m.compte.check_password(w)]
    assert len(mdp) == 1
```

- [ ] **Step 2 : Ajouter au `conftest.py`** la fixture `membre_enregistre` (résultat de `enregistrer_membre` : « Hounkpè Jean-Marc », paroisse de la fixture, année 2015 → matricule `2015-03AS-0001`), réutilisée par les tâches 5 à 8.
- [ ] **Step 3 : Vérifier l'échec** — Run: `DJANGO_DEBUG=True pytest apps/membres/tests/test_pdf.py -q` → FAIL.
- [ ] **Step 4 : Implémenter `pdf.py`, les vues et le réglage.**
- [ ] **Step 5 : Vérifier** — Run: `DJANGO_DEBUG=True pytest -q` → tout passe. Ouvrir un PDF généré et en faire une capture (`docs/captures/fiche-identification.png`) pour contrôle visuel.
- [ ] **Step 6 : Commit** — `feat(membres): fiche d'identification PDF aux logos`.

---

### Task 6 : Espace membre — « Ma fiche »

**Files:**
- Create: `apps/membres/views_membre.py`, `templates/membres/ma_fiche.html`, `templates/membres/mes_coordonnees.html`
- Modify: `apps/membres/forms.py` (`FormulaireCoordonnees`), `apps/membres/urls.py`, `templates/accueil.html` (liens vers « Ma fiche »)
- Test: `apps/membres/tests/test_espace_membre.py` (la fixture `client_membre` ci-dessous va dans `conftest.py`, elle sert aussi à la tâche 7)

**Interfaces:**
- Consumes: `Membre`, `fiche_identification_pdf` (tâche 5).
- Produces:
  - Fonction `membre_de(request) -> Membre` (404 si le compte n'a pas de membre, ex. compte technique).
  - URL `membres:ma_fiche` → `/membres/ma-fiche/` : identité, matricule, catégorie, statut, intégration, affectation actuelle, **parcours** (toutes les affectations, de la plus ancienne à la plus récente : période, paroisse, circuit et région à la date, motif), photo acceptée ou photo en attente (« En attente de validation »).
  - `FormulaireCoordonnees(ModelForm)` — **uniquement** `telephone, whatsapp, email, quartier, ville, profession, urgence_nom, urgence_telephone`.
  - URL `membres:mes_coordonnees` → `/membres/ma-fiche/coordonnees/` (GET/POST) → message « Vos coordonnées ont été mises à jour. ».
  - URL `membres:ma_fiche_pdf` → `/membres/ma-fiche/fiche.pdf` (sans identifiants).
  - L'accueil d'un membre affiche « Ma fiche » ; il n'existe **aucune** URL permettant à un membre d'ouvrir la fiche d'un autre (les URL `bn/…` exigent `gerer_membres`).

- [ ] **Step 1 : Écrire les tests**

```python
import pytest

@pytest.fixture
def client_membre(client, membre_enregistre):
    c = membre_enregistre.membre.compte
    c.doit_changer_mot_de_passe = False; c.save()
    client.force_login(c)
    return client

def test_ma_fiche_affiche_parcours(client_membre, membre_enregistre):
    html = client_membre.get("/membres/ma-fiche/").content.decode()
    assert "2015-03AS-0001" in html and "Intégration" in html and "Ekpe A" in html

def test_modifier_coordonnees_ignore_les_champs_proteges(client_membre, membre_enregistre):
    r = client_membre.post("/membres/ma-fiche/coordonnees/", {
        "telephone": "0161000000", "ville": "Porto-Novo",
        "nom": "PIRATE", "matricule": "2099-99AS-9999", "annee_integration": "2000"})
    assert r.status_code == 302
    m = membre_enregistre.membre; m.refresh_from_db()
    assert m.telephone == "0161000000" and m.ville == "Porto-Novo"
    assert m.nom == "Hounkpè" and m.matricule == "2015-03AS-0001" and m.annee_integration == 2015

def test_membre_n_accede_pas_aux_pages_bn(client_membre, membre_enregistre):
    assert client_membre.get("/membres/bn/2015-03AS-0001/").status_code == 403

def test_compte_sans_membre_404(client, db):
    from apps.comptes.models import Compte
    client.force_login(Compte.objects.create_superuser("tech", "MotDePasse!2026"))
    assert client.get("/membres/ma-fiche/").status_code == 404

def test_ma_fiche_pdf(client_membre):
    r = client_membre.get("/membres/ma-fiche/fiche.pdf")
    assert r.status_code == 200 and r.content.startswith(b"%PDF")
```

- [ ] **Step 2 : Vérifier l'échec** — Run: `DJANGO_DEBUG=True pytest apps/membres/tests/test_espace_membre.py -q` → FAIL.
- [ ] **Step 3 : Implémenter vues, formulaire et gabarits.**
- [ ] **Step 4 : Vérifier** — Run: `DJANGO_DEBUG=True pytest -q` → tout passe ; capture téléphone de « Ma fiche ».
- [ ] **Step 5 : Commit** — `feat(membres): espace membre, ma fiche et mes coordonnées`.

---

### Task 7 : Photo d'identité — dépôt, stockage privé, validation par le BN

**Files:**
- Create: `apps/membres/images.py`, `apps/membres/views_fichiers.py`, `templates/membres/ma_photo.html`, `templates/membres/bn_photos.html`
- Modify: `apps/membres/forms.py` (`FormulairePhoto`), `apps/membres/views_membre.py`, `apps/membres/views_bn.py`, `apps/membres/urls.py`, `apps/membres/pdf.py` (photo acceptée dans la fiche)
- Test: `apps/membres/tests/test_photo.py`

**Interfaces:**
- Consumes: `PhotoIdentite`, `stockage_prive` (tâche 1), `membre_de` (tâche 6), `fiche_identification_pdf` (tâche 5).
- Produces:
  - `class PhotoInvalide(ValueError)` ; `verifier_et_preparer_photo(fichier) -> ContentFile` — ouvre avec Pillow (`Image.verify()` puis réouverture) ; refuse si format ≠ JPEG/PNG (« Format refusé : envoyez une photo JPEG ou PNG. »), taille > 5 Mo (« La photo dépasse 5 Mo. »), dimensions < 300 × 300 (« La photo est trop petite (300 × 300 pixels minimum). ») ; corrige l'orientation EXIF, réduit à 800 px de côté maximum, réencode en JPEG qualité 85 **sans métadonnées**.
  - URL `membres:ma_photo` → `/membres/ma-fiche/photo/` (GET/POST) : affiche les exigences (« photo en tenue de l'Armée du Salut, visage dégagé, fond uni ») ; un dépôt crée une `PhotoIdentite(etat="en_attente")` ; un nouveau dépôt remplace une photo encore en attente du même membre.
  - URL `membres:photo` → `/membres/photos/<int:pk>/` : sert le fichier si l'utilisateur est le membre propriétaire **ou** a `gerer_membres` ; sinon **404** (on ne révèle pas l'existence). `Cache-Control: private, no-store`.
  - URL `membres:cip` → `/membres/<matricule>/cip/` : sert la photo du CIP **uniquement** avec `membres.voir_cip`, sinon 404.
  - URL `membres:bn_photos` → `/membres/bn/photos/` (permission `gerer_membres`) : file des photos en attente (photo, nom complet, matricule, ancienne photo acceptée s'il y en a) ; POST `accepter` ou `refuser` (motif obligatoire, « Indiquez le motif du refus. ») → `etat`, `date_decision`, `decide_par`. Accepter une photo passe les éventuelles autres photos acceptées du membre à l'état « remplacée » : ajouter l'état `remplacee` (« Remplacée ») au choix de la tâche 1.
  - `Membre.photo_acceptee` renvoie la plus récente photo `acceptee`.

- [ ] **Step 1 : Écrire les tests**

```python
import io
import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image
from apps.membres.models import PhotoIdentite

def _image(l=600, h=800, fmt="JPEG"):
    b = io.BytesIO(); Image.new("RGB", (l, h), (20, 40, 75)).save(b, fmt); return b.getvalue()

@pytest.fixture(autouse=True)
def prive(settings, tmp_path):
    settings.PRIVATE_MEDIA_ROOT = tmp_path  # le stockage privé doit lire ce réglage à l'usage

def test_depot_puis_validation_bn(client_membre, client_bn, membre_enregistre):
    r = client_membre.post("/membres/ma-fiche/photo/",
                           {"fichier": SimpleUploadedFile("p.jpg", _image(), "image/jpeg")})
    assert r.status_code == 302
    photo = PhotoIdentite.objects.get()
    assert photo.etat == "en_attente" and membre_enregistre.membre.photo_acceptee is None
    client_bn.post("/membres/bn/photos/", {"photo": photo.pk, "decision": "accepter"})
    photo.refresh_from_db()
    assert photo.etat == "acceptee" and membre_enregistre.membre.photo_acceptee == photo

def test_refus_exige_un_motif(client_membre, client_bn):
    client_membre.post("/membres/ma-fiche/photo/", {"fichier": SimpleUploadedFile("p.jpg", _image(), "image/jpeg")})
    p = PhotoIdentite.objects.get()
    r = client_bn.post("/membres/bn/photos/", {"photo": p.pk, "decision": "refuser", "motif": ""})
    assert "Indiquez le motif du refus." in r.content.decode()
    p.refresh_from_db(); assert p.etat == "en_attente"

@pytest.mark.parametrize("contenu,message", [
    (b"ceci n'est pas une image", "JPEG ou PNG"),
    (_image(200, 200), "trop petite"),
])
def test_photo_refusee(client_membre, contenu, message):
    r = client_membre.post("/membres/ma-fiche/photo/", {"fichier": SimpleUploadedFile("p.jpg", contenu, "image/jpeg")})
    assert message in r.content.decode() and PhotoIdentite.objects.count() == 0

def test_photo_d_un_autre_membre_404(client, client_membre, membre_enregistre, paroisse, bn):
    from apps.membres.services import enregistrer_membre
    client_membre.post("/membres/ma-fiche/photo/", {"fichier": SimpleUploadedFile("p.jpg", _image(), "image/jpeg")})
    pk = PhotoIdentite.objects.get().pk
    autre = enregistrer_membre(donnees={"nom": "Autre", "prenoms": "Personne", "sexe": "F",
        "telephone": "0197111111", "categorie": "actif"}, paroisse_integration=paroisse,
        annee_integration=2016, par=bn).membre
    autre.compte.doit_changer_mot_de_passe = False; autre.compte.save()
    client.force_login(autre.compte)
    assert client.get(f"/membres/photos/{pk}/").status_code == 404

def test_cip_reserve_au_bn(client_membre, membre_enregistre):
    assert client_membre.get(f"/membres/{membre_enregistre.membre.matricule}/cip/").status_code == 404

def test_metadonnees_supprimees_et_redimensionnee(client_membre):
    client_membre.post("/membres/ma-fiche/photo/", {"fichier": SimpleUploadedFile("p.jpg", _image(2000, 3000), "image/jpeg")})
    with PhotoIdentite.objects.get().fichier.open("rb") as f:
        im = Image.open(f); assert max(im.size) == 800 and not im.info.get("exif")
```

- [ ] **Step 2 : Vérifier l'échec** — Run: `DJANGO_DEBUG=True pytest apps/membres/tests/test_photo.py -q` → FAIL.
- [ ] **Step 3 : Implémenter** (le `stockage_prive` doit résoudre `settings.PRIVATE_MEDIA_ROOT` à l'usage — sous-classe de `FileSystemStorage` avec `location` en propriété — pour que le test puisse le rediriger ; migration pour l'état `remplacee`).
- [ ] **Step 4 : Vérifier** — Run: `DJANGO_DEBUG=True pytest -q && ruff check .` → tout passe ; la fiche PDF d'un membre à photo acceptée montre la photo (capture).
- [ ] **Step 5 : Commit** — `feat(membres): photo d'identité, stockage privé et validation par le BN`.

---

### Task 8 : Administration, documentation et vérification finale

**Files:**
- Create: `apps/membres/admin.py`
- Modify: `docs/guide-maintenance.md`, `CLAUDE.md`, `.env.exemple` (`DJANGO_SITE_URL`)
- Test: `apps/membres/tests/test_admin.py`

**Interfaces:**
- Produces:
  - Administration `Membre` en **lecture seule** pour `matricule`, `annee_integration`, `paroisse_integration`, `region_integration` ; pas de suppression ; pas d'ajout (l'enregistrement passe **uniquement** par `/membres/bn/enregistrer/`, qui garantit le matricule) ; recherche par matricule, nom, prénoms ; filtres catégorie, statut, région d'intégration. `CompteurMatricule` : lecture seule. `Affectation`, `PhotoIdentite` : lecture seule.
  - Guide de maintenance : « Donner à un compte les droits du BN (permissions *Gérer les membres* et *Voir la photo du CIP*) en attendant les mandats de l'étape 3 », « Où sont les fichiers privés (`prive/`) et pourquoi ils ne sont pas sur GitHub », « Variable `DJANGO_SITE_URL` ».

- [ ] **Step 1 : Écrire les tests**

```python
def test_admin_membre_sans_ajout_ni_suppression(admin_client_tech, membre_enregistre):
    m = membre_enregistre.membre
    assert admin_client_tech.get("/gestion/membres/membre/add/").status_code == 403
    assert admin_client_tech.get(f"/gestion/membres/membre/{m.pk}/delete/").status_code == 403
    html = admin_client_tech.get(f"/gestion/membres/membre/{m.pk}/change/").content.decode()
    assert 'name="matricule"' not in html and 'name="annee_integration"' not in html
```

(`admin_client_tech` : fixture du `conftest.py`, superutilisateur connecté.)

- [ ] **Step 2 : Vérifier l'échec**, **Step 3 : Implémenter**, **Step 4 : Vérifier** — Run: `DJANGO_DEBUG=True pytest -q && ruff check . && python manage.py makemigrations --check --dry-run` → tout passe ; puis la suite complète sur PostgreSQL local (le test concurrent ne doit pas être « skipped »).
- [ ] **Step 5 : Commit et push** — `chore(membres): administration et documentation de l'étape 2`.

---

## Hors de cette étape (rappel)

Notifications aux bureaux et gardien des périmètres (étape 3 : les bureaux de paroisse, circuit, région verront leurs membres) ; enregistrement par lots Excel (étape 4) ; listes et statistiques (étape 5) ; mutations, décès, démission, réhabilitation, changement de catégorie (étape 6) ; sanctions, journal, double vérification BN, correction exceptionnelle des données d'intégration (étape 7) ; stockage objet des fichiers privés chez l'hébergeur (mise en ligne).
