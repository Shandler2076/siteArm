# Étape 3 — Fonctions, mandats, bureaux et gardien des périmètres : plan de réalisation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Donner les droits de gestion par **mandat** (fonction + unité + dates) au lieu des autorisations provisoires, faire voir à chaque bureau **uniquement** les membres de son périmètre, permettre au BNC d'installer les bureaux, à la paroisse de réinitialiser les mots de passe de ses membres, et prévenir chacun par des **notifications** (nouveau membre, début et fin de mandat, échéances).

**Architecture:** Nouvelle application `apps/bureaux` (modèles `Fonction`, `Mandat` ; module `perimetre.py` = le **gardien des périmètres**, seul endroit qui décide qui voit quoi ; vues de l'espace bureau et de la gestion des bureaux par le BNC). Nouvelle application `apps/notifications` (modèle `Notification`, services `notifier`/`notifier_unite`). Un backend d'autorisation `MandatBackend` traduit un mandat national de gestion en permissions `membres.gerer_membres` et `membres.voir_cip`, ce qui garde les pages BNC de l'étape 2 inchangées.

**Tech Stack:** Django 5.2, PostgreSQL, pytest.

**Spec:** `docs/superpowers/specs/2026-11-09-module1-fondations-design.md` — sections 5 (fonctions, mandats, comptes), 6.1 étape 5 (notification nouveau membre), 6.6 (changement de bureau), 6.7 (mot de passe oublié), 8 (espaces), 9.1 (matrice des droits), 9.2 (gardien), 9.3 (déconnexion 30 min), 10 (notifications), 4.1 (anciens membres), 13 étape 3.

## Global Constraints

- **Niveaux** : `paroisse` (« Unité paroissiale »), `circuit` (« Section de Circuit »), `region` (« Bureau Régional de Coordination »), `national` (« Bureau National de Commandement »).
- **Fonctions** (chargées par migration de données, RI art. 14 à 18), avec droit de gérer au démarrage et durée de mandat :
  - Paroisse (2 ans) : **Chef d'Unité paroissiale**, **Secrétaire paroissial** (gèrent) ; Trésorier paroissial.
  - Circuit (2 ans) : **Chef de Section de Circuit**, **Secrétaire de Circuit** (gèrent) ; Trésorier de Circuit, Organisateur de Circuit, Formateur de Circuit, Vérificateur de Circuit (hors bureau).
  - Région (2 ans) : **Coordinateur régional**, **Secrétaire régional** (gèrent) ; Coordinateur régional adjoint, Rapporteur régional, Trésorier régional, Organisateur régional, Organisateur régional adjoint, Formateur régional, Conseiller régional, Vérificateur régional (hors bureau).
  - National (4 ans) : **Président**, **Secrétaire national** (gèrent) ; Vice-président, Secrétaire national adjoint, Trésorier national, Trésorier national adjoint, Responsable national à l'organisation (affaires sociales), Responsable national adjoint à l'organisation (information et propagande), Responsable national chargé de la formation, Responsable national adjoint chargé de la formation, Responsable national chargé des relations extérieures, Conseiller aux affaires spirituelles, Conseiller juridique et disciplinaire.
- **Mandat en cours** à la date J : `date_debut <= J` et (`date_fin` vide ou `date_fin > J`). Un mandat ne donne des droits de gestion que si sa fonction a `droit_gerer=True` **et** que le titulaire a le statut **Actif** (un membre sanctionné, exclu, démissionnaire ou décédé perd les droits de bureau).
- Une personne peut avoir **plusieurs mandats** en même temps, à tous les niveaux ; ses droits sont la somme de ses mandats en cours.
- **Périmètre** d'une unité = membres dont l'**affectation actuelle** est dans une paroisse de l'unité, selon le **rattachement actuel** de la paroisse (paroisse → circuit → région). National = tous les membres.
- **Accès hors périmètre** : 404 (on ne révèle pas l'existence d'un membre). Un membre simple ne voit jamais un autre membre.
- **Anciens membres** (spec 4.1) : uniquement nom, prénoms, matricule, dates du passage dans l'unité, nouvelle affectation ; jamais les coordonnées ni la suite du parcours.
- **Réinitialisation de mot de passe** : bureau de **paroisse** (pour ses membres) et BNC. Interdite sur un compte qui détient un mandat de gestion, sauf par le BNC ; un compte du BNC n'est réinitialisable que par un autre membre du BNC (ou le compte technique).
- **Déconnexion après 30 minutes** d'inactivité pour un compte qui a au moins un mandat de gestion en cours (2 heures sinon).
- **Échéances** : alerte **60 jours** avant la date de fin prévue, puis alerte « mandat échu non renouvelé » ; un mandat échu n'est **jamais** coupé automatiquement.
- Clé d'unité dans les adresses : `paroisse-<id>`, `circuit-<id>`, `region-<id>`, `national`.
- Tout texte visible en français ; pages pensées pour le téléphone.

## Review Focus

1. **Bornes des dates de mandat** : un mandat qui finit aujourd'hui ne donne plus de droits aujourd'hui ; un mandat qui commence demain n'en donne pas encore → test dans la tâche 2.
2. **Réorganisation du territoire** : une paroisse rattachée à un autre circuit passe dans le périmètre du nouveau circuit (et sort de l'ancien) sans autre action → test dans la tâche 2.
3. **Adresse d'une unité non gérée tapée à la main** (`/bureau/circuit-99/membres/`) ou fiche d'un membre hors périmètre : 404, même pour quelqu'un qui gère une autre unité → test dans la tâche 6.
4. **Titulaire sanctionné** : un secrétaire de paroisse dont le statut passe à « Sanctionné » perd immédiatement l'espace bureau → test dans la tâche 2.
5. **Réinitialisation détournée** : un secrétaire de paroisse tente de réinitialiser le mot de passe d'un membre de sa paroisse qui est Coordinateur régional → refus 403, mot de passe inchangé → test dans la tâche 7.

---

## Structure des fichiers

```
apps/bureaux/
  models.py          # Niveau, Fonction, Mandat
  migrations/0002_fonctions_reglement.py   # données : fonctions du règlement intérieur
  perimetre.py       # Unite, unites_gerees, est_bn, membres_visibles, peut_voir_membre,
                     # anciens_membres, unite_depuis_cle, titulaires_gestion
  backends.py        # MandatBackend (permissions BNC issues des mandats)
  middleware.py      # DureeSessionBureau
  services.py        # installer_bureau, reinitialiser_mot_de_passe, alertes_echeances
  forms.py  views.py  views_bn.py  urls.py  admin.py
  management/commands/verifier_echeances_mandats.py
  tests/
apps/notifications/
  models.py  services.py  views.py  urls.py  context_processors.py  tests/
templates/bureaux/  templates/notifications/
```

---

### Task 1 : Fonctions et mandats

**Files:**
- Create: `apps/bureaux/{__init__,apps,models,admin}.py`, `apps/bureaux/migrations/0001_initial.py` (générée), `apps/bureaux/migrations/0002_fonctions_reglement.py`
- Modify: `config/settings.py` (`apps.bureaux`)
- Test: `apps/bureaux/tests/test_modeles.py`, `apps/bureaux/tests/conftest.py`

**Interfaces:**
- Consumes: `organisation.Paroisse/Circuit/Region`, `membres.Membre`, `comptes.Compte`.
- Produces (`apps.bureaux.models`) :
  - `Niveau(TextChoices)` : `PAROISSE="paroisse"`, `CIRCUIT="circuit"`, `REGION="region"`, `NATIONAL="national"` (libellés des Global Constraints).
  - `Fonction` : `nom` (150), `niveau`, `droit_gerer` (bool), `duree_mandat_annees` (PositiveSmallInteger), `membre_du_bureau` (bool, défaut True ; False pour les vérificateurs), `ordre` (PositiveSmallInteger) ; unique `(niveau, nom)` ; tri `(niveau, ordre)`.
  - `Mandat` : `membre` (FK Membre, PROTECT, related_name="mandats"), `fonction` (FK PROTECT), `paroisse` / `circuit` / `region` (FK nullables, PROTECT), `date_debut`, `date_fin_prevue`, `date_fin` (null), `alerte_echeance_le` (DateField null), `alerte_echu_le` (DateField null), `installe_par` (FK Compte null SET_NULL).
    - `clean()` : l'unité renseignée correspond au niveau de la fonction (exactement `paroisse` pour une fonction de paroisse, etc. ; aucune pour le national) ; `date_fin` > `date_debut` si renseignée. Message : « L'unité ne correspond pas au niveau de la fonction. »
    - `save()` : si `date_fin_prevue` est vide, `date_debut` + `duree_mandat_annees` ans (29 février → 28 février).
    - `est_en_cours(jour: date | None = None) -> bool` ; manager `Mandat.objects.en_cours(jour=None)` ; `unite` (propriété) → l'objet Paroisse/Circuit/Region ou `None` pour le national.
- `conftest.py` : fixtures `territoire` (région 03 « HOULENOU » → circuits « Ekpe A », « Ekpe B » → paroisses « P1 », « P2 » dans Ekpe A, « P3 » dans Ekpe B ; région 05 « WEME » → circuit « Dangbo A » → paroisse « P4 »), `nouveau_membre(paroisse, nom)` (fabrique via `enregistrer_membre`, compte avec `doit_changer_mot_de_passe=False`), `donner_mandat(membre, nom_fonction, unite=None, debut=None, fin=None)`.

- [ ] **Step 1 : Écrire les tests**

```python
import datetime
import pytest
from django.core.exceptions import ValidationError
from apps.bureaux.models import Fonction, Mandat, Niveau

def test_fonctions_du_reglement_chargees(db):
    gerent = set(Fonction.objects.filter(droit_gerer=True).values_list("nom", flat=True))
    assert gerent == {"Chef d'Unité paroissiale", "Secrétaire paroissial", "Chef de Section de Circuit",
                      "Secrétaire de Circuit", "Coordinateur régional", "Secrétaire régional",
                      "Président", "Secrétaire national"}
    assert Fonction.objects.filter(niveau=Niveau.NATIONAL).count() == 13
    assert Fonction.objects.filter(niveau=Niveau.REGION, membre_du_bureau=True).count() == 9
    assert Fonction.objects.get(nom="Président").duree_mandat_annees == 4
    assert Fonction.objects.get(nom="Vérificateur de Circuit").droit_gerer is False

def test_date_fin_prevue_calculee(territoire, nouveau_membre, donner_mandat):
    m = nouveau_membre(territoire["P1"], "Adjovi")
    mandat = donner_mandat(m, "Secrétaire paroissial", territoire["P1"], debut=datetime.date(2024, 2, 29))
    assert mandat.date_fin_prevue == datetime.date(2026, 2, 28)

def test_unite_doit_correspondre_au_niveau(territoire, nouveau_membre):
    m = nouveau_membre(territoire["P1"], "Adjovi")
    f = Fonction.objects.get(nom="Secrétaire paroissial")
    with pytest.raises(ValidationError, match="niveau de la fonction"):
        Mandat(membre=m, fonction=f, circuit=territoire["Ekpe A"], date_debut=datetime.date(2026, 1, 1)).full_clean()

@pytest.mark.parametrize("debut,fin,attendu", [
    (datetime.date(2026, 1, 1), None, True),
    (datetime.date(2026, 11, 11), None, False),          # commence demain
    (datetime.date(2026, 1, 1), datetime.date(2026, 11, 10), False),  # finit aujourd'hui
    (datetime.date(2026, 1, 1), datetime.date(2026, 11, 11), True),
])
def test_est_en_cours(territoire, nouveau_membre, donner_mandat, debut, fin, attendu):
    m = nouveau_membre(territoire["P1"], "Adjovi")
    mandat = donner_mandat(m, "Secrétaire paroissial", territoire["P1"], debut=debut, fin=fin)
    assert mandat.est_en_cours(datetime.date(2026, 11, 10)) is attendu
```

- [ ] **Step 2 : Vérifier l'échec** — Run: `DJANGO_DEBUG=True pytest apps/bureaux -q` → FAIL (`ModuleNotFoundError`).
- [ ] **Step 3 : Implémenter modèles, migration de données (fonctions des Global Constraints, `ordre` = ordre de la liste), administration** (Fonction : modifiable par le compte technique ; Mandat : liste filtrable par niveau, fonction, en cours).
- [ ] **Step 4 : Vérifier** — Run: `DJANGO_DEBUG=True pytest -q && ruff check .` → tout passe.
- [ ] **Step 5 : Commit** — `feat(bureaux): fonctions du règlement intérieur et mandats`.

---

### Task 2 : Le gardien des périmètres

**Files:**
- Create: `apps/bureaux/perimetre.py`
- Test: `apps/bureaux/tests/test_perimetre.py` (la fixture `monde` ci-dessous va dans `conftest.py` : elle sert aussi aux tâches 6 à 9)

**Interfaces:**
- Consumes: `Mandat`, `Niveau` (tâche 1), `Membre`, `Affectation`, `Statut`.
- Produces (`apps.bureaux.perimetre`) :
  - `@dataclass(frozen=True) class Unite: niveau: str; objet: Paroisse | Circuit | Region | None` ; propriétés `cle -> str` (`"paroisse-12"`, …, `"national"`) et `libelle -> str` (« Paroisse P1 », « Circuit Ekpe A », « Région HOULENOU », « Bureau National de Commandement »).
  - `unites_gerees(compte, jour: date | None = None) -> list[Unite]` — unités des mandats en cours dont la fonction a `droit_gerer` et dont le titulaire est `Actif` ; sans doublon ; triées national, régions, circuits, paroisses. Liste vide pour un compte sans membre.
  - `est_bn(compte, jour=None) -> bool` — un mandat national de gestion en cours (le superutilisateur technique compte comme BN).
  - `unite_depuis_cle(compte, cle: str) -> Unite` — lève `Http404` si la clé est mal formée **ou** si l'unité n'est pas dans `unites_gerees(compte)` (le BN peut ouvrir n'importe quelle unité existante).
  - `membres_visibles(unite: Unite) -> QuerySet[Membre]` — membres dont l'affectation **ouverte** est dans le périmètre (rattachement actuel des paroisses) ; national : tous.
  - `peut_voir_membre(compte, membre) -> bool` — lui-même, ou membre dans le périmètre d'une de ses unités gérées.
  - `anciens_membres(unite: Unite) -> QuerySet[Affectation]` — affectations **clôturées** dans l'unité (selon `paroisse` / `circuit_a_date` / `region_a_date`) dont le membre n'est plus dans le périmètre ; `select_related` du membre.
  - `titulaires_gestion(unite: Unite, jour=None) -> QuerySet[Compte]` — comptes des titulaires des mandats de gestion en cours de cette unité (sert aux notifications).

- [ ] **Step 1 : Écrire les tests**

```python
import datetime
import pytest
from django.http import Http404
from apps.bureaux import perimetre as P

AUJ = datetime.date(2026, 11, 10)

@pytest.fixture
def monde(territoire, nouveau_membre, donner_mandat):
    t = territoire
    m1, m2, m3, m4 = (nouveau_membre(t[p], n) for p, n in
                      [("P1", "Adjovi"), ("P2", "Bio"), ("P3", "Chabi"), ("P4", "Dossou")])
    sec_p1 = nouveau_membre(t["P1"], "Secretaire")
    donner_mandat(sec_p1, "Secrétaire paroissial", t["P1"], debut=datetime.date(2025, 1, 1))
    chef_ekpe_a = nouveau_membre(t["P2"], "Chef")
    donner_mandat(chef_ekpe_a, "Chef de Section de Circuit", t["Ekpe A"], debut=datetime.date(2025, 1, 1))
    tresorier = nouveau_membre(t["P1"], "Tresorier")
    donner_mandat(tresorier, "Trésorier paroissial", t["P1"], debut=datetime.date(2025, 1, 1))
    return dict(t, m1=m1, m2=m2, m3=m3, m4=m4, sec_p1=sec_p1, chef=chef_ekpe_a, tresorier=tresorier)

def _matricules(qs): return {m.nom for m in qs}

def test_perimetres(monde):
    p1 = P.Unite("paroisse", monde["P1"]); ca = P.Unite("circuit", monde["Ekpe A"])
    reg = P.Unite("region", monde["HOULENOU"]); nat = P.Unite("national", None)
    assert _matricules(P.membres_visibles(p1)) == {"Adjovi", "Secretaire", "Tresorier"}
    assert _matricules(P.membres_visibles(ca)) == {"Adjovi", "Bio", "Secretaire", "Chef", "Tresorier"}
    assert "Chabi" in _matricules(P.membres_visibles(reg)) and "Dossou" not in _matricules(P.membres_visibles(reg))
    assert P.membres_visibles(nat).count() == 7

def test_seules_les_fonctions_de_gestion_comptent(monde):
    assert [u.cle for u in P.unites_gerees(monde["sec_p1"].compte, AUJ)] == [f"paroisse-{monde['P1'].pk}"]
    assert P.unites_gerees(monde["tresorier"].compte, AUJ) == []
    assert P.unites_gerees(monde["m1"].compte, AUJ) == []

def test_bornes_des_dates(monde, donner_mandat):
    m = monde["m3"]
    donner_mandat(m, "Secrétaire paroissial", monde["P3"], debut=datetime.date(2026, 11, 11))
    assert P.unites_gerees(m.compte, AUJ) == []
    donner_mandat(monde["m4"], "Secrétaire paroissial", monde["P4"], debut=datetime.date(2024, 1, 1), fin=AUJ)
    assert P.unites_gerees(monde["m4"].compte, AUJ) == []

def test_titulaire_sanctionne_perd_ses_droits(monde):
    sec = monde["sec_p1"]; sec.statut = "sanctionne"; sec.save()
    assert P.unites_gerees(sec.compte, AUJ) == []

def test_reorganisation_du_territoire(monde):
    p2 = monde["P2"]; p2.circuit = monde["Ekpe B"]; p2.save()
    ca = P.Unite("circuit", monde["Ekpe A"]); cb = P.Unite("circuit", monde["Ekpe B"])
    assert "Bio" not in _matricules(P.membres_visibles(ca)) and "Bio" in _matricules(P.membres_visibles(cb))

def test_plusieurs_mandats_s_additionnent(monde, donner_mandat):
    sec = monde["sec_p1"]
    donner_mandat(sec, "Coordinateur régional", monde["WEME"], debut=datetime.date(2025, 1, 1))
    assert {u.niveau for u in P.unites_gerees(sec.compte, AUJ)} == {"paroisse", "region"}
    assert P.peut_voir_membre(sec.compte, monde["m4"]) and P.peut_voir_membre(sec.compte, monde["m1"])
    assert not P.peut_voir_membre(sec.compte, monde["m3"])

def test_membre_simple_ne_voit_que_lui(monde):
    assert P.peut_voir_membre(monde["m1"].compte, monde["m1"])
    assert not P.peut_voir_membre(monde["m1"].compte, monde["m2"])

def test_unite_depuis_cle(monde):
    c = monde["sec_p1"].compte
    assert P.unite_depuis_cle(c, f"paroisse-{monde['P1'].pk}").objet == monde["P1"]
    for cle in [f"paroisse-{monde['P2'].pk}", f"circuit-{monde['Ekpe A'].pk}", "national", "paroisse-x", "nimporte"]:
        with pytest.raises(Http404):
            P.unite_depuis_cle(c, cle)

def test_anciens_membres(monde):
    from apps.membres.models import Affectation
    m1 = monde["m1"]; a = m1.affectation_actuelle
    a.date_fin = AUJ; a.save()
    Affectation.objects.create(membre=m1, paroisse=monde["P4"], circuit_a_date=monde["Dangbo A"],
                               region_a_date=monde["WEME"], date_debut=AUJ, motif="Mutation")
    anciens = P.anciens_membres(P.Unite("paroisse", monde["P1"]))
    assert [x.membre.nom for x in anciens] == ["Adjovi"]
    assert "Adjovi" not in _matricules(P.membres_visibles(P.Unite("paroisse", monde["P1"])))
```

- [ ] **Step 2 : Vérifier l'échec** — Run: `DJANGO_DEBUG=True pytest apps/bureaux/tests/test_perimetre.py -q` → FAIL.
- [ ] **Step 3 : Implémenter `perimetre.py`** (filtres en base de données uniquement : `affectations__date_fin__isnull=True` + `affectations__paroisse__circuit__region=…` etc., `.distinct()`).
- [ ] **Step 4 : Vérifier** — Run: `DJANGO_DEBUG=True pytest -q` → tout passe.
- [ ] **Step 5 : Commit** — `feat(bureaux): gardien des périmètres`.

---

### Task 3 : Droits du BNC par mandat et déconnexion de 30 minutes

**Files:**
- Create: `apps/bureaux/backends.py`, `apps/bureaux/middleware.py`
- Modify: `config/settings.py` (`AUTHENTICATION_BACKENDS` : ajouter `apps.bureaux.backends.MandatBackend` après le backend d'identifiant ; `MIDDLEWARE` : `apps.bureaux.middleware.DureeSessionBureau` après `AuthenticationMiddleware`)
- Test: `apps/bureaux/tests/test_droits.py`

**Interfaces:**
- Consumes: `est_bn`, `unites_gerees` (tâche 2).
- Produces:
  - `MandatBackend` — `authenticate()` renvoie toujours `None` ; `get_all_permissions(user, obj=None) -> set[str]` = `{"membres.gerer_membres", "membres.voir_cip"}` si `est_bn(user)`, sinon `set()` ; `has_perm(user, perm, obj=None)` en conséquence ; compte inactif → aucun droit. Résultat mémorisé sur l'objet `user` pour la durée de la requête (`user._permissions_mandat`).
  - `DureeSessionBureau` — si l'utilisateur connecté a au moins une unité gérée : `request.session.set_expiry(1800)` ; sinon ne touche à rien (2 h, réglage global).

- [ ] **Step 1 : Écrire les tests**

```python
import datetime
import pytest

@pytest.fixture
def secretaire_national(territoire, nouveau_membre, donner_mandat):
    m = nouveau_membre(territoire["P1"], "Natio")
    donner_mandat(m, "Secrétaire national", None, debut=datetime.date(2025, 1, 1))
    return m

def test_mandat_national_donne_les_pages_bnc(client, secretaire_national):
    client.force_login(secretaire_national.compte)
    assert client.get("/membres/bn/enregistrer/").status_code == 200
    assert secretaire_national.compte.has_perm("membres.voir_cip")

def test_mandat_de_paroisse_ne_donne_pas_les_pages_bnc(client, territoire, nouveau_membre, donner_mandat):
    m = nouveau_membre(territoire["P1"], "Sec")
    donner_mandat(m, "Secrétaire paroissial", territoire["P1"], debut=datetime.date(2025, 1, 1))
    client.force_login(m.compte)
    assert client.get("/membres/bn/enregistrer/").status_code == 403

def test_fin_du_mandat_national_retire_les_droits(client, secretaire_national):
    mandat = secretaire_national.mandats.get(); mandat.date_fin = datetime.date.today(); mandat.save()
    client.force_login(secretaire_national.compte)
    assert client.get("/membres/bn/enregistrer/").status_code == 403

def test_session_bureau_30_minutes(client, secretaire_national):
    client.force_login(secretaire_national.compte)
    client.get("/")
    assert client.session.get_expiry_age() == 1800

def test_session_membre_2_heures(client, territoire, nouveau_membre):
    client.force_login(nouveau_membre(territoire["P1"], "Simple").compte)
    client.get("/")
    assert client.session.get_expiry_age() == 7200
```

- [ ] **Step 2 : Vérifier l'échec**, **Step 3 : Implémenter**, **Step 4 : Vérifier** — Run: `DJANGO_DEBUG=True pytest -q` → tout passe (les tests de l'étape 2 qui donnent les permissions à la main restent valables : le `ModelBackend` continue de les lire).
- [ ] **Step 5 : Commit** — `feat(bureaux): droits du BNC issus des mandats, session de 30 minutes pour les bureaux`.

---

### Task 4 : Notifications

**Files:**
- Create: `apps/notifications/{__init__,apps,models,services,views,urls,context_processors,admin}.py`, `templates/notifications/liste.html`
- Modify: `config/settings.py` (app, context processor `apps.notifications.context_processors.notifications`, `EMAIL_BACKEND` console en DEBUG, `DEFAULT_FROM_EMAIL` depuis `DJANGO_DEFAULT_FROM_EMAIL`), `config/urls.py` (`notifications/`), `templates/base.html` (cloche avec le nombre non lu), `apps/membres/services.py` (notifier les bureaux à l'enregistrement)
- Test: `apps/notifications/tests/test_notifications.py`

**Interfaces:**
- Consumes: `titulaires_gestion`, `Unite` (tâche 2).
- Produces:
  - `Notification` : `destinataire` (FK Compte, CASCADE, related_name="notifications"), `message` (300), `lien` (200, blank), `lue` (bool), `date` (auto) ; tri `-date`.
  - `notifier(comptes: Iterable[Compte], message: str, lien: str = "") -> int` — une notification par compte distinct et actif ; envoie aussi un email si le compte est rattaché à un membre ayant un email (`send_mail`, `fail_silently=True`, sujet « Armée du Salut — notification ») ; renvoie le nombre de notifications créées.
  - `notifier_unite(unite: Unite, message: str, lien: str = "") -> int` — `notifier(titulaires_gestion(unite), …)`.
  - Page `/notifications/` : liste (les plus récentes d'abord), lien de chaque notification ; ouvrir la page **marque tout comme lu**. Le contexte expose `notifications_non_lues` (entier).
  - Dans `enregistrer_membre` (après validation de la transaction, `transaction.on_commit`) : `notifier_unite` sur la paroisse, le circuit et la région de la paroisse d'intégration avec le message « Nouveau membre dans votre périmètre : {matricule} — {nom_complet} ».

- [ ] **Step 1 : Écrire les tests**

```python
import datetime
from django.core import mail
from apps.notifications.models import Notification
from apps.notifications.services import notifier

def test_notifier_sans_doublon_et_email(territoire, nouveau_membre):
    m = nouveau_membre(territoire["P1"], "Mail"); m.email = "m@exemple.bj"; m.save()
    assert notifier([m.compte, m.compte], "Bonjour", "/x/") == 1
    assert mail.outbox[0].to == ["m@exemple.bj"] and "Bonjour" in mail.outbox[0].body

def test_nouveau_membre_notifie_les_trois_bureaux(territoire, nouveau_membre, donner_mandat, django_capture_on_commit_callbacks):
    t = territoire; d = datetime.date(2025, 1, 1)
    sp = nouveau_membre(t["P1"], "SecP"); donner_mandat(sp, "Secrétaire paroissial", t["P1"], debut=d)
    sc = nouveau_membre(t["P1"], "SecC"); donner_mandat(sc, "Secrétaire de Circuit", t["Ekpe A"], debut=d)
    sr = nouveau_membre(t["P1"], "SecR"); donner_mandat(sr, "Secrétaire régional", t["HOULENOU"], debut=d)
    autre = nouveau_membre(t["P4"], "SecW"); donner_mandat(autre, "Secrétaire paroissial", t["P4"], debut=d)
    with django_capture_on_commit_callbacks(execute=True):
        nouveau = nouveau_membre(t["P1"], "Nouveau")
    for titulaire in (sp, sc, sr):
        assert Notification.objects.filter(destinataire=titulaire.compte,
                                           message__contains=nouveau.matricule).exists()
    assert not Notification.objects.filter(destinataire=autre.compte).exists()

def test_page_marque_comme_lu(client, territoire, nouveau_membre):
    m = nouveau_membre(territoire["P1"], "Lecteur")
    notifier([m.compte], "Message A")
    client.force_login(m.compte)
    assert "1" in client.get("/").content.decode()  # badge
    assert "Message A" in client.get("/notifications/").content.decode()
    assert not Notification.objects.filter(lue=False).exists()
```

- [ ] **Step 2 : Vérifier l'échec**, **Step 3 : Implémenter**, **Step 4 : Vérifier** — Run: `DJANGO_DEBUG=True pytest -q` → tout passe.
- [ ] **Step 5 : Commit** — `feat(notifications): notifications internes et par email, nouveau membre`.

---

### Task 5 : Installation des bureaux et fonctions par le BNC

**Files:**
- Create: `apps/bureaux/services.py`, `apps/bureaux/forms.py`, `apps/bureaux/views_bn.py`, `apps/bureaux/urls.py`, `templates/bureaux/bn_installer.html`, `templates/bureaux/bn_fonctions.html`
- Modify: `config/urls.py` (`bureau/`), `templates/accueil.html` (liens BNC)
- Test: `apps/bureaux/tests/test_installation.py`

**Interfaces:**
- Consumes: modèles (tâche 1), `est_bn`, `Unite` (tâche 2), `notifier` (tâche 4).
- Produces:
  - `class InstallationRefusee(ValueError)`.
  - `installer_bureau(*, unite: Unite, titulaires: dict[Fonction, Membre], date_debut: date, par: Compte) -> list[Mandat]` — dans une transaction : chaque titulaire doit avoir le statut **Actif** (sinon `InstallationRefusee("… n'est pas un membre actif.")`) ; chaque fonction doit être du niveau de l'unité ; **clôt tous les mandats en cours de l'unité** (`date_fin = date_debut`) ; crée les nouveaux mandats (`installe_par=par`, `date_fin_prevue` automatique) ; après validation : notifie les anciens titulaires (« Votre mandat de {fonction} ({unité}) a pris fin le {date}. ») et les nouveaux (« Vous êtes installé(e) {fonction} ({unité}) à compter du {date}. »).
  - Page `/bureau/bn/installer/` (BN uniquement, sinon 403) : étape 1 choisir le niveau et l'unité (listes des unités **actives**) ; étape 2 une ligne par fonction **du bureau** de ce niveau (+ vérificateurs pour circuit et région) avec un champ « matricule » (facultatif), et la date de début ; erreurs en français (« Matricule inconnu : … ») ; succès → message « Bureau installé : N mandat(s). » et récapitulatif.
  - Page `/bureau/bn/fonctions/` (BN) : tableau des fonctions par niveau avec case « droit de gérer » modifiable (POST) — c'est ainsi que le BNC accorde le droit à d'autres fonctions sans toucher au code.

- [ ] **Step 1 : Écrire les tests**

```python
import datetime
import pytest
from apps.bureaux.models import Fonction, Mandat
from apps.bureaux.perimetre import Unite, unites_gerees
from apps.bureaux.services import InstallationRefusee, installer_bureau

def test_installer_clot_l_ancien_bureau(territoire, nouveau_membre, donner_mandat, compte_technique):
    t = territoire; p1 = Unite("paroisse", t["P1"])
    ancien = nouveau_membre(t["P1"], "Ancien")
    donner_mandat(ancien, "Secrétaire paroissial", t["P1"], debut=datetime.date(2024, 1, 1))
    nouveau = nouveau_membre(t["P1"], "Nouveau")
    installer_bureau(unite=p1, titulaires={Fonction.objects.get(nom="Secrétaire paroissial"): nouveau},
                     date_debut=datetime.date(2026, 11, 10), par=compte_technique)
    assert unites_gerees(ancien.compte, datetime.date(2026, 11, 10)) == []
    assert [u.objet for u in unites_gerees(nouveau.compte, datetime.date(2026, 11, 10))] == [t["P1"]]
    assert Mandat.objects.get(membre=ancien).date_fin == datetime.date(2026, 11, 10)

def test_titulaire_non_actif_refuse(territoire, nouveau_membre, compte_technique):
    m = nouveau_membre(territoire["P1"], "Exclu"); m.statut = "exclu"; m.save()
    with pytest.raises(InstallationRefusee, match="pas un membre actif"):
        installer_bureau(unite=Unite("paroisse", territoire["P1"]),
                         titulaires={Fonction.objects.get(nom="Secrétaire paroissial"): m},
                         date_debut=datetime.date(2026, 11, 10), par=compte_technique)
    assert not Mandat.objects.exists()

def test_page_installer_reservee_au_bn(client, territoire, nouveau_membre):
    client.force_login(nouveau_membre(territoire["P1"], "X").compte)
    assert client.get("/bureau/bn/installer/").status_code == 403

def test_page_installer_par_matricule(client_technique, territoire, nouveau_membre):
    m = nouveau_membre(territoire["P1"], "Chef")
    f = Fonction.objects.get(nom="Chef d'Unité paroissiale")
    r = client_technique.post("/bureau/bn/installer/", {
        "niveau": "paroisse", "unite": territoire["P1"].pk, "date_debut": "2026-11-10",
        f"fonction_{f.pk}": m.matricule})
    assert r.status_code == 302 and Mandat.objects.filter(membre=m, fonction=f).exists()
    r = client_technique.post("/bureau/bn/installer/", {
        "niveau": "paroisse", "unite": territoire["P1"].pk, "date_debut": "2026-11-10",
        f"fonction_{f.pk}": "2099-99AS-9999"})
    assert "Matricule inconnu" in r.content.decode()

def test_accorder_le_droit_de_gerer(client_technique, territoire, nouveau_membre, donner_mandat):
    f = Fonction.objects.get(nom="Trésorier paroissial")
    client_technique.post("/bureau/bn/fonctions/", {"fonction": f.pk, "droit_gerer": "on"})
    f.refresh_from_db(); assert f.droit_gerer
```

(fixtures `compte_technique` et `client_technique` ajoutées au `conftest.py` : superutilisateur « tech ».)

- [ ] **Step 2 : Vérifier l'échec**, **Step 3 : Implémenter**, **Step 4 : Vérifier** — Run: `DJANGO_DEBUG=True pytest -q` → tout passe ; capture téléphone de l'étape 2 du formulaire d'installation.
- [ ] **Step 5 : Commit** — `feat(bureaux): installation des bureaux et droits des fonctions par le BNC`.

---

### Task 6 : Espace bureau

**Files:**
- Create: `apps/bureaux/views.py`, `templates/bureaux/{choisir_unite,membres,fiche_membre,anciens}.html`
- Modify: `apps/bureaux/urls.py`, `templates/accueil.html` (lien « Espace bureau » si au moins une unité gérée)
- Test: `apps/bureaux/tests/test_espace_bureau.py`

**Interfaces:**
- Consumes: `unites_gerees`, `unite_depuis_cle`, `membres_visibles`, `anciens_membres` (tâche 2).
- Produces:
  - `/bureau/` : liste des unités gérées (libellé + lien) ; une seule → redirection directe ; aucune → 403.
  - `/bureau/<cle>/membres/` : membres du périmètre (matricule, nom complet, paroisse actuelle, statut, téléphone), recherche `q` sur matricule/nom/prénoms, 50 par page.
  - `/bureau/<cle>/membres/<matricule>/` : fiche en lecture (identité sans photo du CIP, coordonnées, catégorie, statut, parcours complet, mandats) ; 404 si le membre n'est pas dans le périmètre de cette unité.
  - `/bureau/<cle>/anciens/` : anciens membres avec **uniquement** nom, prénoms, matricule, période dans l'unité, nouvelle affectation (paroisse actuelle).

- [ ] **Step 1 : Écrire les tests** (fixture `monde` du `conftest.py`, tâche 2)

```python
def _client(client, membre):
    client.force_login(membre.compte); return client

def test_espace_bureau_liste_son_perimetre(client, monde):
    c = _client(client, monde["sec_p1"])
    r = c.get("/bureau/", follow=True)
    html = r.content.decode()
    assert "Adjovi".upper() in html.upper() and "Bio".upper() not in html.upper()

def test_unite_non_geree_404(client, monde):
    c = _client(client, monde["sec_p1"])
    assert c.get(f"/bureau/circuit-{monde['Ekpe A'].pk}/membres/").status_code == 404
    assert c.get("/bureau/national/membres/").status_code == 404

def test_fiche_hors_perimetre_404(client, monde):
    c = _client(client, monde["sec_p1"])
    cle = f"paroisse-{monde['P1'].pk}"
    assert c.get(f"/bureau/{cle}/membres/{monde['m1'].matricule}/").status_code == 200
    assert c.get(f"/bureau/{cle}/membres/{monde['m3'].matricule}/").status_code == 404

def test_membre_simple_sans_espace_bureau(client, monde):
    assert _client(client, monde["m1"]).get("/bureau/").status_code == 403

def test_anciens_membres_sans_coordonnees(client, monde):
    from apps.membres.models import Affectation
    import datetime
    m1 = monde["m1"]; m1.telephone = "0199887766"; m1.save()
    a = m1.affectation_actuelle; a.date_fin = datetime.date(2026, 11, 10); a.save()
    Affectation.objects.create(membre=m1, paroisse=monde["P4"], circuit_a_date=monde["Dangbo A"],
                               region_a_date=monde["WEME"], date_debut=datetime.date(2026, 11, 10), motif="Mutation")
    html = _client(client, monde["sec_p1"]).get(f"/bureau/paroisse-{monde['P1'].pk}/anciens/").content.decode()
    assert m1.matricule in html and "P4" in html and "0199887766" not in html

def test_recherche(client, monde):
    html = _client(client, monde["chef"]).get(f"/bureau/circuit-{monde['Ekpe A'].pk}/membres/?q=bio").content.decode()
    assert "BIO" in html and "ADJOVI" not in html
```

- [ ] **Step 2 : Vérifier l'échec**, **Step 3 : Implémenter**, **Step 4 : Vérifier** — Run: `DJANGO_DEBUG=True pytest -q` → tout passe ; capture téléphone de la liste des membres.
- [ ] **Step 5 : Commit** — `feat(bureaux): espace bureau, membres du périmètre et anciens membres`.

---

### Task 7 : Réinitialisation du mot de passe par la paroisse

**Files:**
- Modify: `apps/bureaux/services.py` (`reinitialiser_mot_de_passe`), `apps/bureaux/views.py`, `apps/bureaux/urls.py`, `templates/bureaux/fiche_membre.html`, `apps/membres/views_bn.py` (utilise le service — supprime la règle locale de l'étape 2)
- Test: `apps/bureaux/tests/test_reinitialisation.py`

**Interfaces:**
- Consumes: `est_bn`, `unites_gerees`, `peut_voir_membre` (tâche 2), `generer_mot_de_passe_provisoire`, `fiche_identification_pdf` (étape 2).
- Produces:
  - `reinitialiser_mot_de_passe(*, cible: Membre, par: Compte) -> bytes` — renvoie le PDF de la fiche **avec** le nouveau mot de passe provisoire ; règles : autorisé au BN pour tout membre, sauf si la cible a des droits que l'acteur n'a pas (logique de l'étape 2 conservée) ; autorisé au titulaire d'un mandat de gestion **de paroisse** pour les membres de cette paroisse **qui n'ont aucun mandat de gestion en cours** ; sinon `PermissionDenied`. Le PDF est construit **avant** d'enregistrer le nouveau mot de passe ; `doit_changer_mot_de_passe=True` ; notifie la cible « Votre mot de passe a été réinitialisé par {acteur}. ».
  - POST `/bureau/<cle>/membres/<matricule>/reinitialiser/` (bouton visible seulement pour une unité de niveau paroisse) → PDF en pièce jointe ; GET → 405.

- [ ] **Step 1 : Écrire les tests**

```python
import datetime

def _post(client, membre_acteur, cle, cible):
    client.force_login(membre_acteur.compte)
    return client.post(f"/bureau/{cle}/membres/{cible.matricule}/reinitialiser/")

def test_paroisse_reinitialise_son_membre(client, monde):
    r = _post(client, monde["sec_p1"], f"paroisse-{monde['P1'].pk}", monde["m1"])
    assert r.status_code == 200 and r["Content-Type"] == "application/pdf"
    monde["m1"].compte.refresh_from_db(); assert monde["m1"].compte.doit_changer_mot_de_passe

def test_circuit_ne_reinitialise_pas(client, monde):
    assert _post(client, monde["chef"], f"circuit-{monde['Ekpe A'].pk}", monde["m1"]).status_code == 403

def test_refus_sur_un_titulaire_de_mandat(client, monde, donner_mandat):
    cible = monde["m1"]
    donner_mandat(cible, "Coordinateur régional", monde["HOULENOU"], debut=datetime.date(2025, 1, 1))
    ancien_hash = cible.compte.password
    r = _post(client, monde["sec_p1"], f"paroisse-{monde['P1'].pk}", cible)
    cible.compte.refresh_from_db()
    assert r.status_code == 403 and cible.compte.password == ancien_hash

def test_get_interdit(client, monde):
    client.force_login(monde["sec_p1"].compte)
    url = f"/bureau/paroisse-{monde['P1'].pk}/membres/{monde['m1'].matricule}/reinitialiser/"
    assert client.get(url).status_code == 405
```

- [ ] **Step 2 : Vérifier l'échec**, **Step 3 : Implémenter**, **Step 4 : Vérifier** — Run: `DJANGO_DEBUG=True pytest -q` → tout passe (y compris `test_reinitialisation_refusee_si_droits_superieurs` de l'étape 2).
- [ ] **Step 5 : Commit** — `feat(bureaux): réinitialisation des mots de passe par le bureau de paroisse`.

---

### Task 8 : Échéances des mandats

**Files:**
- Create: `apps/bureaux/management/__init__.py`, `apps/bureaux/management/commands/__init__.py`, `apps/bureaux/management/commands/verifier_echeances_mandats.py`, `templates/bureaux/bn_echeances.html`
- Modify: `apps/bureaux/services.py` (`alertes_echeances`), `apps/bureaux/views_bn.py`, `apps/bureaux/urls.py`
- Test: `apps/bureaux/tests/test_echeances.py`

**Interfaces:**
- Consumes: `Mandat` (tâche 1), `notifier`, `notifier_unite`, `titulaires_gestion` (tâches 2, 4).
- Produces:
  - `alertes_echeances(jour: date | None = None) -> tuple[int, int]` — pour chaque mandat en cours : si `date_fin_prevue - jour <= 60 jours` et `date_fin_prevue > jour` et `alerte_echeance_le` vide → notifie le titulaire, les gestionnaires de l'unité et les gestionnaires nationaux (« Le mandat de {fonction} ({unité}) de {nom} arrive à échéance le {date}. ») puis renseigne `alerte_echeance_le` ; si `date_fin_prevue <= jour` et `alerte_echu_le` vide → même destinataires, « Le mandat de … est échu depuis le {date} et n'a pas été renouvelé. », renseigne `alerte_echu_le`. **Ne clôt jamais** le mandat. Renvoie (nb alertes d'échéance, nb alertes d'échu).
  - Commande `python manage.py verifier_echeances_mandats` (à programmer chaque jour chez l'hébergeur) ; affiche « Échéances : X · Échus : Y ».
  - Page `/bureau/bn/echeances/` (BN) : mandats arrivant à échéance dans 60 jours et mandats échus non renouvelés, avec lien vers l'installation du bureau concerné.

- [ ] **Step 1 : Écrire les tests**

```python
import datetime
from apps.bureaux.services import alertes_echeances
from apps.notifications.models import Notification

def test_alerte_60_jours_une_seule_fois(monde):
    mandat = monde["sec_p1"].mandats.get()
    mandat.date_fin_prevue = datetime.date(2027, 1, 9); mandat.save()
    assert alertes_echeances(datetime.date(2026, 11, 9)) == (0, 0)
    assert alertes_echeances(datetime.date(2026, 11, 10)) == (1, 0)
    assert alertes_echeances(datetime.date(2026, 11, 11)) == (0, 0)
    assert Notification.objects.filter(destinataire=monde["sec_p1"].compte,
                                       message__contains="arrive à échéance").exists()

def test_mandat_echu_signale_mais_pas_coupe(monde):
    from apps.bureaux.perimetre import unites_gerees
    mandat = monde["sec_p1"].mandats.get()
    mandat.date_fin_prevue = datetime.date(2026, 11, 1); mandat.alerte_echeance_le = datetime.date(2026, 9, 2); mandat.save()
    assert alertes_echeances(datetime.date(2026, 11, 10)) == (0, 1)
    mandat.refresh_from_db()
    assert mandat.date_fin is None and unites_gerees(monde["sec_p1"].compte, datetime.date(2026, 11, 10))

def test_commande(monde, capsys):
    from django.core.management import call_command
    call_command("verifier_echeances_mandats")
    assert "Échéances" in capsys.readouterr().out
```

- [ ] **Step 2 : Vérifier l'échec**, **Step 3 : Implémenter**, **Step 4 : Vérifier** — Run: `DJANGO_DEBUG=True pytest -q` → tout passe.
- [ ] **Step 5 : Commit** — `feat(bureaux): alertes d'échéance des mandats`.

---

### Task 9 : Accueil, administration, documentation et vérification finale

**Files:**
- Modify: `templates/accueil.html` (sections « Mon espace », « Espace bureau » avec les unités gérées, « Bureau national » si BN), `apps/bureaux/admin.py`, `docs/guide-maintenance.md` (§10 remplacé : « Installer le premier BNC » avec le compte technique via `/bureau/bn/installer/`, tâche planifiée quotidienne `verifier_echeances_mandats`, variable `DJANGO_DEFAULT_FROM_EMAIL`), `CLAUDE.md` (gardien des périmètres : `apps/bureaux/perimetre.py` est le seul endroit qui décide des périmètres), `.env.exemple`
- Test: `apps/bureaux/tests/test_accueil.py`

**Interfaces:**
- Produces: l'accueil affiche, pour un compte : « Ma fiche » (s'il est membre), un lien par unité gérée (« Espace bureau — Paroisse P1 »), les liens BNC (« Enregistrer un membre », « Photos à valider », « Installer un bureau », « Fonctions et droits », « Mandats à échéance ») si `est_bn`.

- [ ] **Step 1 : Écrire les tests**

```python
import datetime

def test_accueil_selon_les_mandats(client, monde, donner_mandat):
    client.force_login(monde["sec_p1"].compte)
    html = client.get("/").content.decode()
    assert "Espace bureau — Paroisse P1" in html and "Installer un bureau" not in html
    donner_mandat(monde["sec_p1"], "Président", None, debut=datetime.date(2025, 1, 1))
    html = client.get("/").content.decode()
    assert "Installer un bureau" in html and "Mandats à échéance" in html
```

- [ ] **Step 2 : Vérifier l'échec**, **Step 3 : Implémenter**, **Step 4 : Vérifier** — Run: `DJANGO_DEBUG=True pytest -q && ruff check . && python manage.py makemigrations --check --dry-run` → tout passe ; puis la suite complète sur PostgreSQL.
- [ ] **Step 5 : Commit et push** — `chore(bureaux): accueil, administration et documentation de l'étape 3`.

---

## Hors de cette étape (rappel)

Enregistrement par lots Excel (étape 4) ; listes et statistiques (étape 5) ; mutations, décès, démission, réhabilitation, changement de catégorie (étape 6) — les « anciens membres » se rempliront avec les mutations ; sanctions, journal des actions, double vérification du BNC (étape 7).
