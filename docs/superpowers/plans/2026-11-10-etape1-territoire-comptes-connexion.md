# Étape 1 — Organisation territoriale, comptes et connexion : plan de réalisation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Poser le squelette Django du site, l'organisation territoriale (régions, circuits, paroisses) chargée depuis la liste provisoire, et la connexion sécurisée par identifiant + mot de passe avec changement obligatoire du mot de passe provisoire.

**Architecture:** Un seul projet Django (`config/`) avec des applications dans `apps/` : `organisation` (territoire) et `comptes` (modèle utilisateur personnalisé `Compte`, connexion). Pages générées par le serveur (gabarits Django), CSS écrit à la main, pensé pour le téléphone. Le territoire est géré par le BN via l'administration Django (en français) pour cette étape.

**Tech Stack:** Python 3.12+, Django 5.2 LTS, PostgreSQL (SQLite accepté en local), pytest + pytest-django, django-axes (blocage après échecs), dj-database-url, whitenoise, gunicorn, ruff, GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-11-09-module1-fondations-design.md` (sections 1, 2, 5.3, 6.7, 9.3, 11, 12, 13 étape 1). Données : `docs/donnees/regions-circuits-paroisses.md`.

## Global Constraints

- Langue du site : français (`LANGUAGE_CODE = "fr"`), fuseau `TIME_ZONE = "Africa/Porto-Novo"`, `USE_TZ = True`.
- Django **5.2 LTS** (`Django>=5.2,<5.3`) — support long, adapté à un mainteneur seul.
- Modèle utilisateur personnalisé `comptes.Compte` déclaré **dès la tâche 1**, avant toute migration (`AUTH_USER_MODEL = "comptes.Compte"`).
- Code de région : **2 chiffres**, de `01` à `99`, **jamais réattribué** ; ordre provisoire confirmé : 01 PORTO-NOVO, 02 COTONOU, 03 HOULENOU, 04 KOVEDJI, 05 WEME, 06 TORRI, 07 PLATEAU I, 08 PLATEAU II, 09 PLATEAU III, 10 TOFFIN, 11 CENTRE, 12 COLLINES, 13 NORD.
- Format de matricule (identifiant de connexion des membres, généré à l'étape 2) : `AAAA-RRAS-NNNN`, ex. `2015-01AS-0157`.
- On ne **supprime jamais** une région, un circuit ou une paroisse : on la **ferme** (`active = False`). Suppression bloquée en base (`on_delete=PROTECT`) et dans l'administration.
- Mots de passe : 8 caractères minimum, mots de passe courants refusés, mot de passe identique à l'identifiant refusé.
- Blocage temporaire après **5** échecs de connexion.
- Tout texte visible par l'utilisateur est en français.
- Secrets (clé Django, base de données) uniquement par variables d'environnement, jamais dans le dépôt.

## Review Focus

1. **Noms avec accents et caractères spéciaux** (« Sô-Tchanhoué », « Itè Anu « Vie Neuve » », apostrophes typographiques ’) : chargés et affichés à l'identique → test dans la tâche 3.
2. **Commande de chargement exécutée deux fois** : aucun doublon, aucun code modifié → test dans la tâche 3.
3. **Identifiant saisi avec espaces ou minuscules** (` 2015-01as-0157 `) : la connexion fonctionne quand même → test dans la tâche 5.
4. **Bon mot de passe pendant le blocage** : toujours refusé tant que le délai n'est pas écoulé, avec un message clair en français → test dans la tâche 7.
5. **Compte devant changer son mot de passe qui tente d'ouvrir une autre page** (y compris l'administration) : redirigé vers le changement ; la déconnexion reste possible → test dans la tâche 6.

---

## Structure des fichiers

```
manage.py
requirements.txt                 # dépendances de production
requirements-dev.txt             # + pytest, pytest-django, ruff
pyproject.toml                   # configuration pytest et ruff
Procfile                         # tâche 8
.env.exemple                     # variables d'environnement attendues
config/settings.py               # réglages (lus depuis l'environnement)
config/urls.py
config/wsgi.py
apps/__init__.py
apps/comptes/                    # Compte, connexion, mots de passe
  models.py managers.py forms.py views.py urls.py
  validators.py middleware.py admin.py
  tests/
apps/organisation/               # Region, Circuit, Paroisse
  models.py admin.py
  data/territoire_provisoire.json
  management/commands/charger_territoire.py
  tests/
templates/base.html
templates/accueil.html
templates/comptes/connexion.html
templates/comptes/changer_mot_de_passe.html
static/css/site.css
.github/workflows/tests.yml
CLAUDE.md                        # contexte pour les assistants IA
docs/guide-maintenance.md
```

---

### Task 1 : Squelette du projet, modèle `Compte` minimal, tests et intégration continue

**Files:**
- Create: `manage.py`, `config/__init__.py`, `config/settings.py`, `config/urls.py`, `config/wsgi.py`, `apps/__init__.py`, `apps/comptes/__init__.py`, `apps/comptes/apps.py`, `apps/comptes/models.py`, `apps/comptes/managers.py`, `apps/comptes/admin.py`, `apps/comptes/migrations/__init__.py`, `requirements.txt`, `requirements-dev.txt`, `pyproject.toml`, `.env.exemple`, `.gitignore`, `.github/workflows/tests.yml`
- Test: `apps/comptes/tests/test_projet.py`, `apps/comptes/tests/test_compte.py`

**Interfaces:**
- Produces:
  - `apps.comptes.models.Compte(AbstractBaseUser, PermissionsMixin)` — champs : `identifiant: CharField(max_length=20, unique=True)`, `nom_affiche: CharField(max_length=150, blank=True)`, `doit_changer_mot_de_passe: BooleanField(default=True)`, `is_active: BooleanField(default=True)`, `is_staff: BooleanField(default=False)`, `date_creation: DateTimeField(auto_now_add=True)` ; `USERNAME_FIELD = "identifiant"` ; `verbose_name = "compte"`.
  - `apps.comptes.managers.CompteManager` — `create_user(identifiant: str, password: str | None = None, **extra) -> Compte` (identifiant normalisé : `strip().upper()`), `create_superuser(identifiant, password, **extra) -> Compte` (`is_staff=True`, `is_superuser=True`, `doit_changer_mot_de_passe=False`).
  - `apps.comptes.models.normaliser_identifiant(valeur: str) -> str` — `valeur.strip().upper()`.
  - Réglages lus depuis l'environnement : `SECRET_KEY` (`DJANGO_SECRET_KEY`), `DEBUG` (`DJANGO_DEBUG`, défaut `False`), `ALLOWED_HOSTS` (`DJANGO_ALLOWED_HOSTS`, liste séparée par virgules), base via `DATABASE_URL` (défaut `sqlite:///db.sqlite3`).

- [ ] **Step 1 : Écrire les tests**

```python
# apps/comptes/tests/test_projet.py
from django.conf import settings

def test_reglages_langue_et_fuseau():
    assert settings.LANGUAGE_CODE == "fr"
    assert settings.TIME_ZONE == "Africa/Porto-Novo"
    assert settings.USE_TZ is True
    assert settings.AUTH_USER_MODEL == "comptes.Compte"

# apps/comptes/tests/test_compte.py
import pytest
from apps.comptes.models import Compte

@pytest.mark.django_db
def test_create_user_normalise_identifiant_et_exige_changement():
    c = Compte.objects.create_user(" 2015-01as-0157 ", "MotDePasse!2026")
    assert c.identifiant == "2015-01AS-0157"
    assert c.doit_changer_mot_de_passe is True
    assert c.check_password("MotDePasse!2026")

@pytest.mark.django_db
def test_create_superuser():
    c = Compte.objects.create_superuser("tech", "MotDePasse!2026")
    assert c.is_staff and c.is_superuser
    assert c.doit_changer_mot_de_passe is False
```

- [ ] **Step 2 : Lancer les tests et vérifier l'échec**

Run: `pytest -q`
Expected: FAIL (projet inexistant / `ModuleNotFoundError`).

- [ ] **Step 3 : Créer le projet**

`django-admin startproject config .`, puis réglages ci-dessus. `INSTALLED_APPS` inclut `apps.comptes` (label `comptes`). `requirements.txt` : `Django>=5.2,<5.3`, `dj-database-url`, `psycopg[binary]`, `django-axes`, `whitenoise`, `gunicorn`. `requirements-dev.txt` : `-r requirements.txt`, `pytest`, `pytest-django`, `ruff`. `pyproject.toml` : `[tool.pytest.ini_options] DJANGO_SETTINGS_MODULE = "config.settings"`, `python_files = ["test_*.py"]` ; `[tool.ruff] line-length = 100`. Pour les tests, `DJANGO_SECRET_KEY` a une valeur par défaut **uniquement si `DJANGO_DEBUG` ou pytest** est actif ; en production l'absence de clé lève une erreur au démarrage. `.gitignore` : `db.sqlite3`, `.env`, `__pycache__/`, `staticfiles/`, `media/`. Générer la migration initiale de `comptes`.

- [ ] **Step 4 : CI GitHub Actions**

`.github/workflows/tests.yml` : sur `push` et `pull_request`, Python 3.12, service `postgres:16`, `DATABASE_URL=postgres://postgres:postgres@localhost:5432/test`, étapes : installer `requirements-dev.txt`, `ruff check .`, `python manage.py makemigrations --check --dry-run`, `pytest -q`.

- [ ] **Step 5 : Lancer les tests**

Run: `pip install -r requirements-dev.txt && ruff check . && pytest -q`
Expected: 3 passed, ruff sans erreur.

- [ ] **Step 6 : Commit**

```bash
git add -A && git commit -m "feat: squelette Django, modèle Compte et intégration continue"
```

---

### Task 2 : Modèle territorial (Région, Circuit, Paroisse)

**Files:**
- Create: `apps/organisation/__init__.py`, `apps/organisation/apps.py`, `apps/organisation/models.py`, `apps/organisation/migrations/__init__.py`
- Modify: `config/settings.py` (ajouter `apps.organisation`)
- Test: `apps/organisation/tests/test_modeles.py`

**Interfaces:**
- Produces (`apps.organisation.models`) :
  - `Region` — `code: CharField(max_length=2, unique=True, validators=[RegexValidator(r"^(0[1-9]|[1-9][0-9])$")])`, `nom: CharField(max_length=100, unique=True)`, `active: BooleanField(default=True)`, `date_creation`, `date_fermeture: DateField(null=True, blank=True)` ; tri par `code` ; `__str__` → `"01 — PORTO-NOVO"`.
  - `Circuit` — `region: ForeignKey(Region, on_delete=PROTECT, related_name="circuits")`, `nom: CharField(max_length=150)`, `active`, `date_creation`, `date_fermeture` ; contrainte unique `(region, nom)` ; `__str__` → `"Circuit de Davo"`.
  - `Paroisse` — `circuit: ForeignKey(Circuit, on_delete=PROTECT, related_name="paroisses")`, `nom: CharField(max_length=255)`, `active`, `date_creation`, `date_fermeture` ; contrainte unique `(circuit, nom)` ; propriété `region -> Region` (`self.circuit.region`) ; `__str__` → le nom.
  - Mixin commun `Fermable` avec `fermer(date: datetime.date | None = None) -> None` (met `active=False`, `date_fermeture` = date ou aujourd'hui, sauvegarde) et `rouvrir() -> None`.
  - `delete()` surchargé sur les trois modèles : lève `django.core.exceptions.PermissionDenied("On ne supprime pas : utilisez « fermer ».")`.

- [ ] **Step 1 : Écrire les tests**

```python
import datetime, pytest
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError
from apps.organisation.models import Region, Circuit, Paroisse

@pytest.fixture
def paroisse(db):
    r = Region.objects.create(code="01", nom="PORTO-NOVO")
    c = Circuit.objects.create(region=r, nom="Davo")
    return Paroisse.objects.create(circuit=c, nom="Paroisse Saint Michel de TOKPOTA DAVO")

@pytest.mark.parametrize("code", ["1", "00", "100", "AB"])
def test_code_region_invalide(db, code):
    with pytest.raises(ValidationError):
        Region(code=code, nom="X").full_clean()

def test_code_region_unique(db):
    Region.objects.create(code="01", nom="PORTO-NOVO")
    with pytest.raises(IntegrityError):
        Region.objects.create(code="01", nom="AUTRE")

def test_paroisse_connait_sa_region(paroisse):
    assert paroisse.region.code == "01"

def test_suppression_interdite(paroisse):
    for obj in (paroisse, paroisse.circuit, paroisse.circuit.region):
        with pytest.raises(PermissionDenied):
            obj.delete()

def test_fermer_et_rouvrir(paroisse):
    paroisse.fermer(datetime.date(2026, 12, 26))
    paroisse.refresh_from_db()
    assert paroisse.active is False and paroisse.date_fermeture == datetime.date(2026, 12, 26)
    paroisse.rouvrir(); paroisse.refresh_from_db()
    assert paroisse.active is True and paroisse.date_fermeture is None

def test_str(paroisse):
    assert str(paroisse.circuit.region) == "01 — PORTO-NOVO"
    assert str(paroisse.circuit) == "Circuit de Davo"
```

- [ ] **Step 2 : Vérifier l'échec** — Run: `pytest apps/organisation -q` → FAIL (`ModuleNotFoundError`).
- [ ] **Step 3 : Implémenter les modèles et la migration** (`python manage.py makemigrations organisation`).
- [ ] **Step 4 : Vérifier** — Run: `pytest -q` → tout passe.
- [ ] **Step 5 : Commit** — `git commit -am "feat(organisation): régions, circuits et paroisses (fermeture sans suppression)"` (ajouter les nouveaux fichiers).

---

### Task 3 : Données territoriales provisoires et commande `charger_territoire`

**Files:**
- Create: `apps/organisation/data/territoire_provisoire.json`, `apps/organisation/management/__init__.py`, `apps/organisation/management/commands/__init__.py`, `apps/organisation/management/commands/charger_territoire.py`
- Test: `apps/organisation/tests/test_chargement.py`

**Interfaces:**
- Consumes: `Region`, `Circuit`, `Paroisse` (tâche 2).
- Produces:
  - Fichier JSON : `{"regions": [{"code": "01", "nom": "PORTO-NOVO", "circuits": [{"nom": "Davo", "paroisses": ["Paroisse Saint Michel de TOKPOTA DAVO", ...]}, ...]}, ...]}`, généré depuis `docs/donnees/regions-circuits-paroisses.md` (13 régions, 87 circuits, 427 paroisses, noms identiques au fichier Markdown ; le circuit « Adja-Ouèrè » de la région 09 est nommé **« Adja-Ouèrè (Plateau III) »**).
  - `python manage.py charger_territoire [--fichier CHEMIN]` — par défaut le fichier provisoire. Idempotent : crée ce qui manque (`get_or_create` par `code` pour les régions, par `(region, nom)` pour les circuits, `(circuit, nom)` pour les paroisses), ne modifie **jamais** le code d'une région existante, ne supprime rien. Le tout dans une transaction (`transaction.atomic`). Affiche : `Régions : X créées, Y existantes · Circuits : … · Paroisses : …`.
  - Erreur (`CommandError`, rien n'est écrit) si une région du fichier a un code déjà utilisé par une région **de nom différent**.

- [ ] **Step 1 : Écrire les tests**

```python
import json, pytest
from django.core.management import call_command, CommandError
from apps.organisation.models import Region, Circuit, Paroisse

def test_chargement_complet(db):
    call_command("charger_territoire")
    assert Region.objects.count() == 13
    assert Circuit.objects.count() == 87
    assert Paroisse.objects.count() == 427
    assert Region.objects.get(code="13").nom == "NORD"
    assert Region.objects.get(code="09").circuits.filter(nom="Adja-Ouèrè (Plateau III)").exists()

def test_caracteres_speciaux_conserves(db):
    call_command("charger_territoire")
    assert Circuit.objects.filter(nom="Sô-Tchanhoué").exists()
    assert Paroisse.objects.filter(nom="Paroisse Itè Anu « Vie Neuve » de IKPINLE SEKANME").exists()
    assert Paroisse.objects.filter(nom__contains="d’AKPADJLAME").exists()

def test_idempotent(db):
    call_command("charger_territoire"); call_command("charger_territoire")
    assert (Region.objects.count(), Circuit.objects.count(), Paroisse.objects.count()) == (13, 87, 427)

def test_conflit_de_code_refuse_sans_rien_ecrire(db, tmp_path):
    Region.objects.create(code="01", nom="AUTRE NOM")
    f = tmp_path / "t.json"
    f.write_text(json.dumps({"regions": [{"code": "01", "nom": "PORTO-NOVO",
        "circuits": [{"nom": "Davo", "paroisses": ["P1"]}]}]}), encoding="utf-8")
    with pytest.raises(CommandError):
        call_command("charger_territoire", fichier=str(f))
    assert Circuit.objects.count() == 0
```

- [ ] **Step 2 : Vérifier l'échec** — Run: `pytest apps/organisation/tests/test_chargement.py -q` → FAIL (commande inconnue).
- [ ] **Step 3 : Générer le JSON** depuis le Markdown (script ponctuel, non conservé : titres `## NN — Région …` → région, `### Circuit de X (n paroisses)` → circuit, lignes `N. …` → paroisses ; lecture en UTF-8, `ensure_ascii=False`). Vérifier les totaux 13 / 87 / 427.
- [ ] **Step 4 : Implémenter la commande.**
- [ ] **Step 5 : Vérifier** — Run: `pytest -q` → tout passe.
- [ ] **Step 6 : Commit** — `git commit -m "feat(organisation): données provisoires et commande charger_territoire"`.

---

### Task 4 : Administration du territoire (BN)

**Files:**
- Modify: `apps/organisation/admin.py`, `config/settings.py` (titres de l'administration), `config/urls.py` (administration montée sur `/gestion/`)
- Test: `apps/organisation/tests/test_admin.py`

**Interfaces:**
- Consumes: modèles de la tâche 2, `Compte.objects.create_superuser` (tâche 1).
- Produces: administration en français à `/gestion/` (titre : « Armée du Salut — Gestion »). Pour `Region`, `Circuit`, `Paroisse` : `has_delete_permission` → `False` ; actions « Fermer la sélection » et « Rouvrir la sélection » (appellent `fermer()` / `rouvrir()`) ; recherche par nom ; filtres `active` et parent (région pour circuit, région + circuit pour paroisse) ; colonnes : code/nom/actif/nb circuits (région), nom/région/actif/nb paroisses (circuit), nom/circuit/région/actif (paroisse). `Region.code` en lecture seule une fois l'objet créé.

- [ ] **Step 1 : Écrire les tests**

```python
import pytest
from apps.organisation.models import Region

@pytest.fixture
def admin_client_bn(client, db):
    from apps.comptes.models import Compte
    client.force_login(Compte.objects.create_superuser("tech", "MotDePasse!2026"))
    return client

def test_liste_regions_accessible(admin_client_bn):
    Region.objects.create(code="01", nom="PORTO-NOVO")
    r = admin_client_bn.get("/gestion/organisation/region/")
    assert r.status_code == 200 and "PORTO-NOVO" in r.content.decode()

def test_pas_de_suppression_dans_admin(admin_client_bn):
    reg = Region.objects.create(code="01", nom="PORTO-NOVO")
    r = admin_client_bn.get(f"/gestion/organisation/region/{reg.pk}/delete/")
    assert r.status_code == 403

def test_action_fermer(admin_client_bn):
    reg = Region.objects.create(code="01", nom="PORTO-NOVO")
    admin_client_bn.post("/gestion/organisation/region/",
        {"action": "fermer_selection", "_selected_action": [reg.pk]})
    reg.refresh_from_db()
    assert reg.active is False

def test_code_non_modifiable_apres_creation(admin_client_bn):
    reg = Region.objects.create(code="01", nom="PORTO-NOVO")
    r = admin_client_bn.get(f"/gestion/organisation/region/{reg.pk}/change/")
    assert 'name="code"' not in r.content.decode()
```

- [ ] **Step 2 : Vérifier l'échec** — Run: `pytest apps/organisation/tests/test_admin.py -q` → FAIL (404).
- [ ] **Step 3 : Implémenter l'administration** (noms d'actions `fermer_selection`, `rouvrir_selection`).
- [ ] **Step 4 : Vérifier** — Run: `pytest -q` → tout passe.
- [ ] **Step 5 : Commit** — `git commit -am "feat(organisation): administration du territoire sans suppression"`.

---

### Task 5 : Connexion, déconnexion, accueil et gabarit mobile

**Files:**
- Create: `apps/comptes/forms.py`, `apps/comptes/views.py`, `apps/comptes/urls.py`, `templates/base.html`, `templates/accueil.html`, `templates/comptes/connexion.html`, `static/css/site.css`
- Modify: `config/settings.py` (`TEMPLATES.DIRS`, `STATICFILES_DIRS`, `LOGIN_URL = "connexion"`, `LOGIN_REDIRECT_URL = "accueil"`, `LOGOUT_REDIRECT_URL = "connexion"`), `config/urls.py`
- Test: `apps/comptes/tests/test_connexion.py`

**Interfaces:**
- Consumes: `Compte`, `normaliser_identifiant` (tâche 1).
- Produces:
  - URL `connexion` → `/connexion/` (`LoginView` avec `FormulaireConnexion`), `deconnexion` → `/deconnexion/` (POST uniquement), `accueil` → `/` (connexion requise).
  - `apps.comptes.forms.FormulaireConnexion(AuthenticationForm)` — libellés « Identifiant (matricule) » et « Mot de passe » ; `clean_username()` applique `normaliser_identifiant`. Message d'erreur : « Identifiant ou mot de passe incorrect. »
  - `templates/base.html` — `<html lang="fr">`, balise viewport mobile, en-tête aux couleurs (bleu marine `#14284B`, rouge `#B3122E`, or `#D4A017`), bloc `contenu`, bouton de déconnexion (formulaire POST) si connecté. Aucune ressource externe (CSS local).
  - `accueil.html` : « Bienvenue, {{ user.nom_affiche|default:user.identifiant }} ».

- [ ] **Step 1 : Écrire les tests**

```python
import pytest
from apps.comptes.models import Compte

@pytest.fixture
def compte(db):
    c = Compte.objects.create_user("2015-01AS-0157", "MotDePasse!2026")
    c.doit_changer_mot_de_passe = False; c.save()
    return c

def test_accueil_exige_connexion(client, db):
    r = client.get("/")
    assert r.status_code == 302 and r.url.startswith("/connexion/")

def test_connexion_avec_espaces_et_minuscules(client, compte):
    r = client.post("/connexion/", {"username": " 2015-01as-0157 ", "password": "MotDePasse!2026"})
    assert r.status_code == 302 and r.url == "/"

def test_mauvais_mot_de_passe_message_francais(client, compte):
    r = client.post("/connexion/", {"username": "2015-01AS-0157", "password": "faux"})
    assert "Identifiant ou mot de passe incorrect." in r.content.decode()

def test_page_connexion_mobile_et_francais(client, db):
    html = client.get("/connexion/").content.decode()
    assert 'lang="fr"' in html and 'name="viewport"' in html

def test_deconnexion_post(client, compte):
    client.force_login(compte)
    assert client.post("/deconnexion/").status_code == 302
    assert client.get("/").status_code == 302
```

- [ ] **Step 2 : Vérifier l'échec** — Run: `pytest apps/comptes/tests/test_connexion.py -q` → FAIL (404).
- [ ] **Step 3 : Implémenter formulaire, vues, URL, gabarits et CSS.**
- [ ] **Step 4 : Vérifier** — Run: `pytest -q` → tout passe.
- [ ] **Step 5 : Vérification visuelle** — `python manage.py runserver`, ouvrir `/connexion/` en largeur 375 px (outils du navigateur) : formulaire lisible, sans défilement horizontal.
- [ ] **Step 6 : Commit** — `git commit -m "feat(comptes): connexion par identifiant et gabarit mobile"`.

---

### Task 6 : Politique des mots de passe et changement obligatoire

**Files:**
- Create: `apps/comptes/validators.py`, `apps/comptes/middleware.py`, `templates/comptes/changer_mot_de_passe.html`
- Modify: `apps/comptes/views.py`, `apps/comptes/urls.py`, `config/settings.py` (`AUTH_PASSWORD_VALIDATORS`, `MIDDLEWARE`)
- Test: `apps/comptes/tests/test_mot_de_passe.py`

**Interfaces:**
- Consumes: `Compte.doit_changer_mot_de_passe` (tâche 1), vues de la tâche 5.
- Produces:
  - `AUTH_PASSWORD_VALIDATORS` : `MinimumLengthValidator` (`min_length: 8`), `CommonPasswordValidator`, `NumericPasswordValidator`, `apps.comptes.validators.DifferentDeLIdentifiantValidator`.
  - `DifferentDeLIdentifiantValidator.validate(password, user=None)` — refuse si `normaliser_identifiant(password) == user.identifiant` ; message « Le mot de passe ne doit pas être votre identifiant. »
  - URL `changer_mot_de_passe` → `/mot-de-passe/changer/` (`PasswordChangeView`) ; en cas de succès : `doit_changer_mot_de_passe = False`, message « Votre mot de passe a été changé. », redirection vers `accueil`.
  - `apps.comptes.middleware.ChangementMotDePasseObligatoire` — placé après `AuthenticationMiddleware` ; si l'utilisateur est connecté et `doit_changer_mot_de_passe` est vrai, toute requête est redirigée (302) vers `changer_mot_de_passe`, **sauf** les chemins de `changer_mot_de_passe`, `deconnexion` et `STATIC_URL`.

- [ ] **Step 1 : Écrire les tests**

```python
import pytest
from apps.comptes.models import Compte

@pytest.fixture
def nouveau(client, db):
    c = Compte.objects.create_user("2015-01AS-0157", "Provisoire!2026")
    client.force_login(c)
    return c

@pytest.mark.parametrize("chemin", ["/", "/gestion/"])
def test_redirection_tant_que_non_change(client, nouveau, chemin):
    r = client.get(chemin)
    assert r.status_code == 302 and r.url == "/mot-de-passe/changer/"

def test_deconnexion_reste_possible(client, nouveau):
    assert client.post("/deconnexion/").url == "/connexion/"

def test_refuse_identifiant_comme_mot_de_passe(client, nouveau):
    r = client.post("/mot-de-passe/changer/", {"old_password": "Provisoire!2026",
        "new_password1": "2015-01as-0157", "new_password2": "2015-01as-0157"})
    assert "ne doit pas être votre identifiant" in r.content.decode()

def test_refuse_trop_court(client, nouveau):
    r = client.post("/mot-de-passe/changer/", {"old_password": "Provisoire!2026",
        "new_password1": "Ab1!", "new_password2": "Ab1!"})
    assert r.status_code == 200
    nouveau.refresh_from_db(); assert nouveau.doit_changer_mot_de_passe is True

def test_changement_reussi_libere_le_compte(client, nouveau):
    r = client.post("/mot-de-passe/changer/", {"old_password": "Provisoire!2026",
        "new_password1": "Nouveau!Salut2026", "new_password2": "Nouveau!Salut2026"})
    assert r.status_code == 302 and r.url == "/"
    nouveau.refresh_from_db(); assert nouveau.doit_changer_mot_de_passe is False
    assert client.get("/").status_code == 200
```

- [ ] **Step 2 : Vérifier l'échec** — Run: `pytest apps/comptes/tests/test_mot_de_passe.py -q` → FAIL.
- [ ] **Step 3 : Implémenter validateur, middleware, vue et gabarit.**
- [ ] **Step 4 : Vérifier** — Run: `pytest -q` → tout passe.
- [ ] **Step 5 : Commit** — `git commit -m "feat(comptes): politique des mots de passe et changement obligatoire"`.

---

### Task 7 : Blocage après 5 échecs et expiration de session

**Files:**
- Modify: `config/settings.py`, `templates/comptes/connexion.html`
- Create: `templates/comptes/compte_bloque.html`
- Test: `apps/comptes/tests/test_securite.py`

**Interfaces:**
- Consumes: vue de connexion (tâche 5).
- Produces:
  - django-axes : `AXES_FAILURE_LIMIT = 5`, `AXES_COOLOFF_TIME = 0.25` (15 minutes), `AXES_LOCKOUT_PARAMETERS = ["username"]` (blocage par identifiant), `AXES_USERNAME_FORM_FIELD = "username"`, `AXES_LOCKOUT_TEMPLATE = "comptes/compte_bloque.html"`, `AXES_HTTP_RESPONSE_CODE = 429`, `AUTHENTICATION_BACKENDS = ["axes.backends.AxesStandaloneBackend", "django.contrib.auth.backends.ModelBackend"]`, `axes.middleware.AxesMiddleware` en dernier. Les identifiants soumis sont normalisés avant comptage (`AXES_USERNAME_CALLABLE` → fonction utilisant `normaliser_identifiant`).
  - Message de blocage : « Trop de tentatives. Votre compte est bloqué pendant 15 minutes. »
  - Session : `SESSION_COOKIE_AGE = 7200` (2 h d'inactivité), `SESSION_SAVE_EVERY_REQUEST = True`, `SESSION_EXPIRE_AT_BROWSER_CLOSE = False`. (La durée plus courte pour les bureaux arrive avec les mandats, étape 3.)
  - Cookies : `SESSION_COOKIE_HTTPONLY = True` ; `SESSION_COOKIE_SECURE` et `CSRF_COOKIE_SECURE` à `True` quand `DEBUG` est faux.

- [ ] **Step 1 : Écrire les tests**

```python
import pytest
from apps.comptes.models import Compte

@pytest.fixture
def compte(db):
    c = Compte.objects.create_user("2015-01AS-0157", "MotDePasse!2026")
    c.doit_changer_mot_de_passe = False; c.save()
    return c

def _essai(client, mdp, ident="2015-01AS-0157"):
    return client.post("/connexion/", {"username": ident, "password": mdp})

def test_bloque_apres_5_echecs_meme_avec_bon_mot_de_passe(client, compte):
    for _ in range(5):
        _essai(client, "faux")
    r = _essai(client, "MotDePasse!2026")
    assert r.status_code == 429
    assert "bloqué pendant 15 minutes" in r.content.decode()

def test_variantes_d_ecriture_comptent_ensemble(client, compte):
    for ident in ["2015-01as-0157", " 2015-01AS-0157", "2015-01AS-0157 ", "2015-01aS-0157", "2015-01As-0157"]:
        _essai(client, "faux", ident)
    assert _essai(client, "MotDePasse!2026").status_code == 429

def test_4_echecs_puis_succes(client, compte):
    for _ in range(4):
        _essai(client, "faux")
    assert _essai(client, "MotDePasse!2026").status_code == 302

def test_reglages_session(settings):
    assert settings.SESSION_COOKIE_AGE == 7200 and settings.SESSION_SAVE_EVERY_REQUEST
```

- [ ] **Step 2 : Vérifier l'échec** — Run: `pytest apps/comptes/tests/test_securite.py -q` → FAIL.
- [ ] **Step 3 : Configurer django-axes, la session et le gabarit de blocage** ; ajouter `axes` à `INSTALLED_APPS` et migrer. Dans les tests, n'utiliser que `client.force_login` (axes refuse `client.login` sans requête).
- [ ] **Step 4 : Vérifier** — Run: `pytest -q` → tout passe.
- [ ] **Step 5 : Commit** — `git commit -m "feat(comptes): blocage après 5 échecs et expiration de session"`.

---

### Task 8 : Préparation de la mise en ligne et documentation

**Files:**
- Create: `Procfile`, `CLAUDE.md`, `docs/guide-maintenance.md`
- Modify: `config/settings.py` (whitenoise, `STATIC_ROOT`, sécurité HTTPS), `README.md`
- Test: `apps/comptes/tests/test_deploiement.py`

**Interfaces:**
- Produces:
  - `Procfile` : `web: gunicorn config.wsgi --log-file -` et `postdeploy: python manage.py migrate --noinput`.
  - Réglages de production quand `DEBUG` est faux : `SECURE_SSL_REDIRECT = True`, `SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")`, `SECURE_HSTS_SECONDS = 31536000`, `SECURE_HSTS_INCLUDE_SUBDOMAINS = True`, `SECURE_CONTENT_TYPE_NOSNIFF = True`, `X_FRAME_OPTIONS = "DENY"`, `CSRF_TRUSTED_ORIGINS` depuis `DJANGO_CSRF_TRUSTED_ORIGINS`. Whitenoise (`CompressedManifestStaticFilesStorage`) pour les fichiers statiques.
  - `CLAUDE.md` : but du site, règles métier clés (matricule `AAAA-RRAS-NNNN`, pas de suppression territoriale, gardien des périmètres à venir), commandes (`pytest -q`, `ruff check .`, `python manage.py charger_territoire`), conventions (français, TDD, rien en production sans tests verts).
  - `docs/guide-maintenance.md` (français, pas à pas) : installer en local, lancer les tests, créer le compte technique (`createsuperuser`), charger le territoire, variables d'environnement (`.env.exemple`), mettre à jour le site, que faire si la CI est rouge.
  - `README.md` : présentation en 10 lignes + liens vers la spec, le plan, le guide.

- [ ] **Step 1 : Écrire le test**

```python
import os, subprocess, sys

def test_check_deploy_sans_avertissement():
    env = {**os.environ, "DJANGO_DEBUG": "False", "DJANGO_SECRET_KEY": "x" * 60,
           "DJANGO_ALLOWED_HOSTS": "exemple.bj", "DJANGO_CSRF_TRUSTED_ORIGINS": "https://exemple.bj"}
    r = subprocess.run([sys.executable, "manage.py", "check", "--deploy", "--fail-level", "WARNING"],
                       env=env, capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr

def test_secret_obligatoire_en_production():
    env = {k: v for k, v in os.environ.items() if k != "DJANGO_SECRET_KEY"}
    env.update({"DJANGO_DEBUG": "False", "DJANGO_ALLOWED_HOSTS": "exemple.bj"})
    env.pop("PYTEST_CURRENT_TEST", None)
    r = subprocess.run([sys.executable, "manage.py", "check"], env=env, capture_output=True, text=True)
    assert r.returncode != 0
```

- [ ] **Step 2 : Vérifier l'échec** — Run: `pytest apps/comptes/tests/test_deploiement.py -q` → FAIL (avertissements de sécurité).
- [ ] **Step 3 : Implémenter réglages, Procfile et documentation.** La détection « pytest actif » de la tâche 1 doit s'appuyer sur une variable que la sous-commande du test 2 n'hérite pas (ex. `"pytest" in sys.modules`), pas sur `PYTEST_CURRENT_TEST` seul.
- [ ] **Step 4 : Vérifier** — Run: `ruff check . && pytest -q && python manage.py collectstatic --noinput` (avec `DJANGO_DEBUG=False` et une clé fictive) → tout passe.
- [ ] **Step 5 : Commit et push** — `git commit -m "chore: préparation mise en ligne et documentation"` puis `git push`.

---

## Hors de cette étape (rappel)

Fiche membre, génération du matricule et fiche PDF (étape 2) ; mandats, gardien des périmètres, espaces bureau, réinitialisation des mots de passe par le bureau de paroisse et déconnexion plus rapide des bureaux (étape 3) ; double vérification BN (étape 7) ; PWA installable (avec l'interface membre, étape 2) ; choix et ouverture du compte chez l'hébergeur (décision de l'église, comparatif chiffré à fournir).
