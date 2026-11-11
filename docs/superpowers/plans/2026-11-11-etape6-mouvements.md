# Étape 6 — Mutations, décès, démission, réhabilitation, changement de catégorie : plan de réalisation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal :** les mouvements de la vie d'un membre passent par le site, avec les bons circuits de validation. Ces mouvements sont : la mutation demandée par la paroisse d'arrivée, avisée par le circuit et la région de départ et décidée par le BN ; le décès et la démission signalés par la paroisse puis confirmés par le BN ; la réhabilitation demandée par la paroisse et validée par le BN ; le changement de catégorie signalé par un bureau et validé par le BN. Chaque mouvement est inscrit dans un historique visible sur la fiche, au journal et dans les notifications.

**Architecture :** une nouvelle application `apps/mouvements` contient les modèles `Mutation`, `AvisMutation`, `Signalement` et `HistoriqueMembre`. Toute la logique est dans `services.py`, sous forme de fonctions transactionnelles qui verrouillent la demande et revérifient la situation au moment de la décision. Les vues ne font que vérifier les droits, toujours via le gardien des périmètres pour les bureaux et via `bn_requis` pour le BN, puis appellent ces services. Seuls deux points d'entrée modifient le statut et la catégorie : `changer_statut` et `changer_categorie`. L'étape 7 (sanctions) les réutilisera.

**Tech Stack :** Django 5.2, pytest-django, ReportLab (fiche avec identifiants pour la réhabilitation, via `apps/membres/pdf.py::fiche_identification_pdf`).

**Spec :** `docs/superpowers/specs/2026-11-09-module1-fondations-design.md` — §6.3 (mutation), §6.5 (décès), §6.5 bis (démission, réhabilitation), §3.6 (changement de catégorie), §4 et §4.1 (parcours, anciens membres), §3.3 (statuts), §9.1 (matrice des droits), §10 (notifications), §12.1 (tests des mutations).

## Global Constraints

- Tout texte visible en français ; code et noms métier en français.
- Toute vue de bureau passe par `apps/bureaux/perimetre.py` (`unite_depuis_cle`, `membres_visibles`) ; 404 hors périmètre. Pages BN : `apps/bureaux/views_bn.py::bn_requis`.
- Le parcours est **rempli automatiquement** ; personne ne le modifie à la main. Circuit et région **à la date** sont enregistrés à l'ouverture de chaque affectation.
- **Une seule demande de mutation en cours par membre.** États : *En attente d'avis → En attente du BN → Validée / Refusée* (+ *Annulée* : voir décisions).
- Le BN peut décider une mutation **même si un avis manque**.
- Décès / démission confirmés : statut « Décédé » / « Démissionnaire », **compte désactivé**, fiche conservée, matricule inchangé à vie.
- Réhabilitation : seulement **démissionnaire ou exclu**, au plus tôt **6 mois** après la démission ou l'exclusion ; pour un exclu, **référence de l'engagement écrit de bonne conduite obligatoire** ; **exclu à nouveau après une réhabilitation suivant une exclusion → plus jamais réhabilitable** (le site le dit et bloque) ; validation BN → statut « Actif », compte réactivé avec un **nouveau mot de passe provisoire**, **même matricule**.
- Catégorie : signalée par paroisse, circuit ou région (ou BN), **validée par le BN**, membre notifié, sans effet sur le matricule.
- Toute opération : historique du membre + journal (`apps/journal/services.py::journaliser`) + notifications (`apps/notifications/services.py::notifier`, `notifier_unite`).
- Tests : `DJANGO_DEBUG=True pytest -q` ; style : `ruff check .` ; TDD.

## Décisions prises dans ce plan (à valider par le mainteneur)

1. **Mandats d'un membre muté :** à la validation, ses mandats en cours dans les unités qu'il **quitte** sont clos automatiquement : paroisse si elle change, circuit s'il change, région si elle change. Les mandats nationaux ne sont pas touchés. Le BN est prévenu sur la page de décision et dans la notification.
2. **Décès et démission confirmés :** tous les mandats en cours du membre sont clos à la date de confirmation. Une mutation en cours est **annulée**, et les bureaux concernés en sont avertis.
3. **Recherche par matricule pour une demande de mutation :** la paroisse d'arrivée saisit le matricule. Le site affiche alors seulement le nom, les prénoms et la paroisse actuelle, pour confirmation, et rien d'autre de la fiche. Seul un membre au statut Actif ou Sanctionné peut être muté.
4. **Avis :** le circuit et la région de départ donnent chacun **un** avis, qui ne se modifie pas. La demande passe « En attente du BN » quand les deux avis sont donnés. Si la mutation reste dans le même circuit ou la même région, l'avis de ce circuit ou de cette région est quand même demandé.
5. **Délai de 6 mois :** il est compté en mois calendaires depuis la **date de la démission ou de l'exclusion** inscrite dans l'historique. Si le site ne connaît pas cette date (statut posé avant l'étape 6), la demande est bloquée avec le message « Date de démission ou d'exclusion inconnue : le BN doit la régulariser. »
6. **Revérification au moment de la décision :** le BN ne peut confirmer que si la situation n'a pas changé depuis la demande (statut, affectation actuelle, délai). Sinon le site affiche un message clair et ne modifie rien.
7. **Le BN peut lui-même** demander une mutation, signaler un décès ou une démission, demander une réhabilitation ou signaler un changement de catégorie depuis son espace national. La demande suit alors le même circuit de validation.

## Review Focus

1. **Double décision** (double clic, deux membres du BN en même temps) : la seconde décision est refusée (« Cette demande a déjà été traitée. ») et rien n'est appliqué deux fois (une seule affectation ouverte, un seul historique). Test : Tâche 2 `test_decision_deux_fois`, Tâche 3 `test_confirmer_deux_fois`.
2. **Situation changée entre la demande et la décision** (décès confirmé pendant une mutation en cours, autre affectation entre-temps) : le BN ne peut pas valider la mutation, et le message indique pourquoi. Test : Tâche 2 `test_validation_situation_changee`, Tâche 3 `test_deces_annule_mutation`.
3. **Demandes impossibles** : paroisse d'arrivée identique à la paroisse actuelle ou fermée, membre décédé, démissionnaire ou exclu, deuxième demande en cours, date de décès dans le futur ou antérieure à la naissance, catégorie identique à l'actuelle → message, rien n'est créé. Tests : Tâche 2 `test_demandes_refusees`, Tâche 3 `test_signalements_refuses`.
4. **URL modifiées à la main** : avis donné par un circuit qui n'est pas celui de départ, signalement sur un membre hors périmètre, décision BN par un non-BN → 404 ou 403, rien n'est créé. Tests : Tâche 4 `test_avis_mauvais_circuit_404`, Tâche 5 `test_signaler_hors_perimetre_404`, Tâche 6 `test_decisions_reservees_au_bn`.
5. **Borne exacte des 6 mois** : démission le 31/08 → réhabilitation possible à partir du 28/02 (29/02 les années bissextiles), pas la veille. Test : Tâche 3 `test_delai_six_mois_bornes`.

---

## Structure des fichiers

| Fichier | Rôle |
|---|---|
| `apps/mouvements/models.py` | `HistoriqueMembre`, `Mutation`, `AvisMutation`, `Signalement` |
| `apps/mouvements/statuts.py` | `changer_statut`, `changer_categorie`, `clore_mandats`, `ajouter_mois` |
| `apps/mouvements/services.py` | mutations : `demander_mutation`, `donner_avis`, `decider_mutation` ; signalements : `signaler`, `decider_signalement`, `blocage_rehabilitation` ; exception `MouvementRefuse` |
| `apps/mouvements/forms.py` | formulaires de demande, d'avis, de signalement et de décision |
| `apps/mouvements/views.py` | pages des bureaux (demandes, nouvelle mutation, détail et avis, signalements) |
| `apps/mouvements/views_bn.py` | pages du BN (décisions à prendre, décider une mutation, décider un signalement) |
| `apps/mouvements/urls.py` | `app_name = "mouvements"`, inclus sous `bureau/` **avant** `apps.bureaux.urls` |
| `templates/mouvements/*.html` | gabarits |
| `templates/bureaux/_entete_unite.html`, `templates/bureaux/fiche_membre.html`, `templates/membres/ma_fiche.html`, `templates/membres/bn_fiche.html`, `templates/accueil.html` | onglet « Demandes », boutons de signalement, bloc « Historique », lien « Décisions à prendre » |
| `apps/journal/models.py` | nouvelles constantes d'action |

---

### Tâche 1 : Modèles et changements de statut / catégorie

**Files :** Create `apps/mouvements/{__init__,apps,models,statuts,admin}.py`, migration `0001`, `apps/mouvements/tests/{__init__,conftest}.py` (réimporte les fixtures de `apps/bureaux/tests/conftest.py`), `apps/mouvements/tests/test_statuts.py` ; Modify `config/settings.py` (`apps.mouvements`), `apps/journal/models.py`.

**Interfaces :**
- Produces : `HistoriqueMembre(membre FK related_name="historique", date DateTimeField auto_now_add, type CharField choices TypeHistorique{STATUT="statut","Statut"; CATEGORIE="categorie","Catégorie"}, ancien CharField(20), nouveau CharField(20), date_effet DateField, motif CharField(200), reference CharField(120, blank), par FK Compte null SET_NULL)` ; `ordering = ["-date_effet", "-pk"]` ; propriété `libelle -> str`, ex. « Statut : Actif → Décédé » (libellés des choices).
- Produces : `TypeSignalement(TextChoices)` : `DECES="deces","Décès"`, `DEMISSION="demission","Démission"`, `REHABILITATION="rehabilitation","Réhabilitation"`, `CATEGORIE="categorie","Changement de catégorie"` ; `EtatDemande(TextChoices)` : `AVIS="avis","En attente d'avis"`, `BN="bn","En attente du BN"`, `VALIDEE="validee","Validée"`, `REFUSEE="refusee","Refusée"`, `ANNULEE="annulee","Annulée"`.
- Produces : `Mutation(membre FK related_name="mutations", paroisse_depart FK Paroisse, paroisse_arrivee FK Paroisse, etat (EtatDemande, défaut AVIS), motif CharField(300, blank), demandee_par FK Compte, date_demande auto_now_add, decidee_par FK null, date_decision DateTimeField null, commentaire_decision CharField(300, blank))` ; contrainte unique conditionnelle `membre` quand `etat in (avis, bn)` (« une_mutation_en_cours ») ; propriété `en_cours -> bool`.
- Produces : `AvisMutation(mutation FK related_name="avis", niveau CharField choices circuit/region, favorable BooleanField, commentaire CharField(300, blank), par FK Compte, date auto_now_add)` ; unique (`mutation`, `niveau`).
- Produces : `Signalement(membre FK related_name="signalements", type TypeSignalement, etat EtatDemande — seulement BN/VALIDEE/REFUSEE/ANNULEE, défaut BN, date_effet DateField null, reference CharField(120, blank), nouvelle_categorie CharField(20, blank, choices Categorie), commentaire CharField(300, blank), unite CharField(40) — clé de l'unité qui signale, demande_par FK Compte, date_demande auto_now_add, decide_par FK null, date_decision null, motif_refus CharField(300, blank))` ; unique conditionnelle (`membre`, `type`) quand `etat = bn` (« un_signalement_en_cours_par_type »).
- Produces (`statuts.py`) : `ajouter_mois(jour: date, mois: int) -> date` (fin de mois ramenée au dernier jour valide) ; `clore_mandats(membre, jour: date, unites: set | None = None) -> list[Mandat]` (mandats en cours, `date_fin = max(jour, date_debut)` ; `unites=None` = tous ; sinon seulement ceux dont `mandat.unite` est dans l'ensemble) ; `changer_statut(membre, nouveau: str, *, par, date_effet: date, motif: str, reference: str = "") -> HistoriqueMembre` (met à jour `membre.statut` ; compte `is_active = nouveau in (actif, sanctionne)` ; si nouveau ∈ {decede, demissionnaire, exclu} : `clore_mandats(membre, date_effet)` ; écrit l'historique) ; `changer_categorie(membre, nouvelle: str, *, par, date_effet, motif, reference="") -> HistoriqueMembre`.
- Produces (`apps/journal/models.py`) : `MUTATION_DEMANDEE`, `MUTATION_AVIS`, `MUTATION_DECIDEE`, `SIGNALEMENT`, `SIGNALEMENT_DECIDE` (valeurs en minuscules identiques aux noms).

- [ ] **Step 1 : tests rouges**

```python
def test_deces_desactive_compte_et_clot_mandats(monde):
    sec = monde["sec_p1"]
    h = changer_statut(sec, "decede", par=None, date_effet=date(2026, 11, 1), motif="Décès confirmé")
    sec.refresh_from_db(); sec.compte.refresh_from_db()
    assert sec.statut == "decede" and not sec.compte.is_active and sec.matricule
    assert h.libelle == "Statut : Actif → Décédé" and h.ancien == "actif"
    assert not sec.mandats.en_cours(date(2026, 11, 2)).exists()

def test_retour_actif_reactive_compte(monde): ...            # demissionnaire → actif : is_active True
def test_changer_categorie_historique(monde): ...            # « Catégorie : Membre actif → Membre d'honneur »
def test_clore_mandats_selon_unites(monde): ...               # unites={P1} ne clôt pas le mandat de circuit du chef
def test_clore_mandat_futur(monde, donner_mandat): ...       # début 2027 → date_fin = date_debut, jamais en cours
@pytest.mark.parametrize("jour, mois, attendu", [
    (date(2026, 8, 31), 6, date(2027, 2, 28)), (date(2027, 8, 31), 6, date(2028, 2, 29)),
    (date(2026, 1, 15), 6, date(2026, 7, 15))])
def test_ajouter_mois(jour, mois, attendu): ...
def test_une_seule_mutation_en_cours(monde): ...             # IntegrityError pour une 2ᵉ mutation « avis »
```

- [ ] **Step 2 :** rouge. **Step 3 :** implémenter (+ admin en lecture seule pour les quatre modèles). **Step 4 :** vert + ruff. **Step 5 :** commit `feat(mouvements): modèles, historique et changements de statut`.

---

### Tâche 2 : Mutations (services)

**Files :** Create `apps/mouvements/services.py` (partie mutations), `apps/mouvements/tests/test_mutations.py`.

**Interfaces :**
- Consumes : `Mutation`, `AvisMutation`, `clore_mandats`, `Unite`, `titulaires_gestion`, `notifier`, `notifier_unite`, `journaliser`.
- Produces : `class MouvementRefuse(Exception)` (message en français affichable).
- Produces : `demander_mutation(*, membre, paroisse_arrivee, par, motif: str = "") -> Mutation`. Refus (`MouvementRefuse`) :
  - statut ∉ {actif, sanctionne} → « Seul un membre actif ou sanctionné peut être muté. »
  - paroisse fermée → « Cette paroisse est fermée. »
  - même paroisse que l'affectation actuelle → « Le membre est déjà dans cette paroisse. »
  - pas d'affectation ouverte → « Ce membre n'a pas d'affectation actuelle. »
  - mutation déjà en cours → « Une demande de mutation est déjà en cours pour ce membre. »
  
  Effets : enregistre `paroisse_depart` (affectation actuelle) ; notifie la paroisse de départ, le circuit de départ, la région de départ et le BN ; message « Demande de mutation de {matricule} — {nom} vers {paroisse} » ; lien vers la page de la demande ; journal `MUTATION_DEMANDEE`.
- Produces : `donner_avis(*, mutation, niveau: str, favorable: bool, commentaire: str, par) -> AvisMutation`. Refus si la mutation n'est plus « avis » ou si l'avis de ce niveau existe déjà (« L'avis du circuit a déjà été donné. »). Quand les deux avis sont donnés → `etat = bn`. Notifie le BN et la paroisse d'arrivée ; journal `MUTATION_AVIS`.
- Produces : `decider_mutation(*, mutation, valider: bool, par, commentaire: str = "", jour: date | None = None) -> Mutation`. Le tout dans `transaction.atomic()`, avec `select_for_update` sur la mutation.
  - Refus si l'état ∉ {avis, bn} : « Cette demande a déjà été traitée. »
  - Si validée, revérifie que le statut est actif ou sanctionné, que l'affectation actuelle est toujours `paroisse_depart` et que la paroisse d'arrivée est ouverte ; sinon « La situation du membre a changé depuis la demande : {raison}. »
  - Validation : ferme l'affectation (`date_fin = jour`), ouvre la nouvelle (`circuit_a_date`, `region_a_date` actuels, `date_debut = jour`, `motif = f"Mutation n° {pk}"`) et appelle `clore_mandats(membre, jour, unites quittées)`.
  - Notifications à tous les bureaux de départ et d'arrivée (paroisse, circuit, région, sans doublon), au BN et au membre : « Mutation validée : … » ou « Mutation refusée : … ». Journal `MUTATION_DECIDEE` (`valider`, `commentaire`).
- Produces : `mutations_pour_unite(unite: Unite) -> QuerySet[Mutation]` : les mutations dont la paroisse de départ ou d'arrivée est dans l'unité (national : toutes), les plus récentes d'abord.

- [ ] **Step 1 : tests rouges** (fixture `monde` : m1 en P1/Ekpe A/HOULENOU, m4 en P4/Dangbo A/WEME)

```python
def test_demande_notifie_depart_et_bn(monde, compte_technique): ...   # notifications sec_p1 (P1), chef (Ekpe A) ; journal
def test_demandes_refusees(monde): ...      # même paroisse, paroisse fermée, membre décédé, 2ᵉ demande → MouvementRefuse, Mutation.count() inchangé
def test_avis_puis_attente_bn(monde): ...   # circuit puis région → etat "bn" ; 2ᵉ avis circuit → MouvementRefuse
def test_validation_met_a_jour_parcours(monde):
    mut = demander_mutation(membre=m1, paroisse_arrivee=P4, par=tech)
    decider_mutation(mutation=mut, valider=True, par=tech, jour=date(2026, 11, 11))
    ancienne, nouvelle = m1.affectations.order_by("date_debut", "pk")
    assert ancienne.date_fin == date(2026, 11, 11) and nouvelle.date_fin is None
    assert (nouvelle.paroisse, nouvelle.circuit_a_date, nouvelle.region_a_date) == (P4, Dangbo A, WEME)
    assert nouvelle.motif == f"Mutation n° {mut.pk}"
    assert m1 in membres_visibles(Unite("paroisse", P4)) and m1 not in membres_visibles(Unite("paroisse", P1))
    assert anciens_membres(Unite("paroisse", P1)).filter(membre=m1).exists()
    assert anciens_membres(Unite("region", HOULENOU)).filter(membre=m1).exists()
def test_validation_sans_avis_possible(monde): ...                  # le BN décide alors que l'état est encore « avis »
def test_refus_aucun_changement(monde): ...                         # affectations inchangées, etat refusee, membre notifié
def test_mandats_clos_dans_unites_quittees(monde): ...              # sec_p1 muté de P1 vers P2 : mandat P1 clos ; chef (circuit Ekpe A) muté de P2 vers P1 : mandat de circuit conservé
def test_decision_deux_fois(monde): ...                             # 2ᵉ decider_mutation → « déjà été traitée », une seule affectation ouverte
def test_validation_situation_changee(monde): ...                   # statut passé à « decede » après la demande → MouvementRefuse, rien ne change
```

- [ ] **Step 2 :** rouge. **Step 3 :** implémenter. **Step 4 :** vert + ruff. **Step 5 :** commit `feat(mouvements): demandes, avis et décisions de mutation`.

---

### Tâche 3 : Signalements (décès, démission, réhabilitation, catégorie)

**Files :** Modify `apps/mouvements/services.py` ; Create `apps/mouvements/tests/test_signalements.py`.

**Interfaces :**
- Consumes : `changer_statut`, `changer_categorie`, `ajouter_mois`, `HistoriqueMembre`, `generer_mot_de_passe_provisoire`, `fiche_identification_pdf`.
- Produces : `blocage_rehabilitation(membre, jour: date) -> str | None`. Renvoie le message qui bloque la demande, ou `None` si elle est possible :
  - statut ∉ {demissionnaire, exclu} → « Seul un membre démissionnaire ou exclu peut être réhabilité. » ;
  - exclu et déjà réhabilité après une exclusion (un `HistoriqueMembre` statut `exclu → actif` existe) → « Ce membre, déjà réhabilité après une exclusion puis exclu à nouveau, ne peut plus être réhabilité (règlement intérieur, art. 172). » ;
  - date de la démission ou de l'exclusion inconnue (pas d'historique vers le statut actuel) → message de la décision 5 ;
  - `jour < ajouter_mois(date_effet, 6)` → « Réhabilitation possible à partir du JJ/MM/AAAA (6 mois après la démission ou l'exclusion). ».
- Produces : `signaler(*, membre, type: str, par, unite: str, date_effet: date | None = None, reference: str = "", nouvelle_categorie: str = "", commentaire: str = "", jour: date | None = None) -> Signalement`. Règles, avec refus par `MouvementRefuse` :
  - décès et démission : statut actif ou sanctionné ; `date_effet` obligatoire, pas dans le futur, pas avant la date de naissance ;
  - réhabilitation : `blocage_rehabilitation(...)` est `None` ; `reference` obligatoire si le membre est exclu (« La référence de l'engagement écrit de bonne conduite est obligatoire pour un membre exclu. ») ;
  - catégorie : `nouvelle_categorie` différente de la catégorie actuelle ;
  - un signalement du même type déjà en attente → « Un signalement de ce type est déjà en attente. ».
  
  Effets : notifie le BN (« {type} signalé pour {matricule} — {nom} ») ; journal `SIGNALEMENT`.
- Produces : `@dataclass Decision(signalement: Signalement, pdf: bytes | None)` et `decider_signalement(*, signalement, confirmer: bool, par, motif_refus: str = "", jour: date | None = None) -> Decision`. Le tout est atomique avec `select_for_update`, refusé si l'état ≠ bn (« Cette demande a déjà été traitée. »), et les règles de `signaler` sont revérifiées à `jour`. Si confirmé :
  - **décès** : `changer_statut(decede, date_effet)` ; les mutations en cours passent « annulee » (commentaire « Annulée : décès confirmé ») ;
  - **démission** : `changer_statut(demissionnaire, date_effet)` ; les mutations en cours sont annulées de même ;
  - **réhabilitation** : `changer_statut(actif, date_effet=jour, reference=…)` ; nouveau mot de passe provisoire avec `doit_changer_mot_de_passe = True` ; `pdf = fiche_identification_pdf(membre, mot_de_passe)` (construit avant d'écrire) ;
  - **catégorie** : `changer_categorie(nouvelle_categorie, date_effet=jour)`.
  
  Notifications : l'unité qui a signalé, les bureaux de la paroisse, du circuit et de la région actuels du membre, et le membre lui-même s'il a un compte actif (catégorie, réhabilitation). Journal `SIGNALEMENT_DECIDE`.

- [ ] **Step 1 : tests rouges**

```python
def test_deces_signale_puis_confirme(monde): ...    # statut decede, compte inactif, historique date_effet = date signalée, bureaux P1/Ekpe A/HOULENOU notifiés
def test_demission_confirmee(monde): ...            # demissionnaire, compte inactif, matricule inchangé
def test_signalements_refuses(monde): ...           # décès futur, avant la naissance, membre déjà décédé, catégorie identique, doublon en attente
def test_deces_annule_mutation(monde): ...          # mutation « avis » → « annulee » à la confirmation du décès
@pytest.mark.parametrize("jour, possible", [(date(2027, 2, 27), False), (date(2027, 2, 28), True)])
def test_delai_six_mois_bornes(monde, jour, possible): ...  # démission confirmée avec date_effet 2026-08-31
def test_rehabilitation_valide(monde): ...          # statut actif, compte actif, doit_changer True, même matricule, pdf commence par b"%PDF", ancien mot de passe refusé
def test_rehabilitation_exclu_exige_engagement(monde): ...   # exclu via changer_statut(exclu, date_effet=2025-01-01) ; sans référence → refus ; avec → ok
def test_exclu_deux_fois_bloque(monde): ...         # exclu → réhabilité → exclu → message art. 172
def test_date_inconnue_bloque(monde): ...           # statut mis à « demissionnaire » directement en base → message décision 5
def test_categorie_validee(monde): ...              # categorie honneur, historique, membre notifié
def test_confirmer_deux_fois(monde): ...            # 2ᵉ decider_signalement → « déjà été traitée », un seul historique
def test_refus_signalement(monde): ...              # etat refusee, motif_refus, statut inchangé, unité signalante notifiée
```

- [ ] **Step 2 :** rouge. **Step 3 :** implémenter. **Step 4 :** vert + ruff. **Step 5 :** commit `feat(mouvements): décès, démission, réhabilitation et catégorie`.

---

### Tâche 4 : Pages des bureaux — demandes, mutations et avis

**Files :** Create `apps/mouvements/{forms,views,urls}.py`, `templates/mouvements/demandes.html`, `nouvelle_mutation.html`, `mutation.html`, `apps/mouvements/tests/test_pages_mutations.py` ; Modify `config/urls.py`, `templates/bureaux/_entete_unite.html` (onglet « Demandes »).

**Interfaces :**
- Consumes : services de la Tâche 2, `unite_depuis_cle`, `membres_visibles`.
- Produces : URLs (`mouvements:…`) :
  - `demandes` → `/bureau/<cle>/demandes/` : les mutations de `mutations_pour_unite(unite)` (en cours d'abord) et les signalements dont `unite == cle` ;
  - `nouvelle_mutation` → `/bureau/<cle>/mutations/nouvelle/`, réservée au niveau paroisse (paroisse d'arrivée = l'unité) et au niveau national (choix de la paroisse d'arrivée parmi les paroisses ouvertes) ; sinon 404. Déroulement en deux temps : (1) matricule → (2) écran de confirmation montrant seulement « {nom complet} — {paroisse actuelle} » + motif → POST `confirmer=1` ; matricule inconnu → « Aucun membre avec ce matricule. » ;
  - `mutation` → `/bureau/<cle>/mutations/<pk>/` : visible si la paroisse de départ ou d'arrivée est dans le périmètre de l'unité, sinon 404. Affiche l'état, le membre (nom, matricule, départ → arrivée), les avis et la décision. Le formulaire d'avis n'apparaît que pour le circuit de départ (niveau circuit, objet = circuit de la paroisse de départ) ou la région de départ, tant que leur avis manque ;
  - `avis` → POST `/bureau/<cle>/mutations/<pk>/avis/` : `favorable` (radio Favorable / Défavorable), `commentaire` ; 404 si l'unité n'est ni le circuit ni la région de départ ; `MouvementRefuse` → message d'erreur.
- Produces : `mouvements:mutation_aiguillage` → `/bureau/mutations/<pk>/`, lien commun de toutes les notifications de mutation. Il redirige vers la page BN si le compte a `membres.gerer_membres`. Sinon il redirige vers la page de la mutation dans la première unité gérée du compte qui la voit ; à défaut, 404.

- [ ] **Step 1 : tests rouges**

```python
def test_onglet_demandes(client, monde): ...                     # lien /bureau/paroisse-<P1>/demandes/ sur la page Membres
def test_paroisse_demande_mutation_en_deux_temps(client, monde): # sec de P4 (créé dans le test) : étape 1 montre « Adjovi Test — P1 » ; étape 2 crée la mutation, redirige vers sa page
def test_nouvelle_mutation_reservee(client, monde): ...           # chef (circuit) → 404 ; membre simple → 404
def test_matricule_inconnu(client, monde): ...                    # message, aucune mutation
def test_avis_circuit(client, monde): ...                         # chef d'Ekpe A donne un avis défavorable sur m1 (P1 → P4) ; page affiche « Défavorable »
def test_avis_mauvais_circuit_404(client, monde): ...             # bureau d'Ekpe B → 404 ; rien créé
def test_mutation_hors_perimetre_404(client, monde): ...          # paroisse P3 (ni départ ni arrivée) → 404
def test_aiguillage_notification(client, monde): ...              # /bureau/mutations/<pk>/ redirige sec_p1 vers /bureau/paroisse-<P1>/mutations/<pk>/
```

- [ ] **Step 2 :** rouge. **Step 3 :** implémenter. **Step 4 :** vert + ruff. **Step 5 :** commit `feat(mouvements): pages des bureaux pour les mutations`.

---

### Tâche 5 : Pages des bureaux — signalements depuis la fiche

**Files :** Create `templates/mouvements/signaler.html`, `apps/mouvements/tests/test_pages_signalements.py` ; Modify `apps/mouvements/{forms,views,urls}.py`, `templates/bureaux/fiche_membre.html`.

**Interfaces :**
- Produces : `mouvements:signaler` → `/bureau/<cle>/membres/<matricule>/signaler/<type>/` (GET formulaire, POST création). Le membre est cherché dans `membres_visibles(unite)` (sinon 404) et le type doit être autorisé pour le niveau (sinon 404) :
  - décès, démission, réhabilitation : niveau paroisse ou national ;
  - catégorie : paroisse, circuit, région ou national.
  
  Champs selon le type :
  - décès : « Date du décès » ;
  - démission : « Date de la démission », « Référence de la lettre (facultatif) » ;
  - réhabilitation : « Référence de l'engagement écrit de bonne conduite », requise si le membre est exclu ;
  - catégorie : « Nouvelle catégorie » (choix sans la catégorie actuelle).
  
  Tous les types ont aussi « Commentaire ». Après le POST : redirection vers la fiche avec le message « Signalement transmis au Bureau national. ».
- La fiche bureau affiche les boutons des actions permises au niveau et au statut. Pour la réhabilitation, le bouton est remplacé par le message de `blocage_rehabilitation` quand elle est impossible. Elle affiche aussi le bandeau « En attente du BN : … » s'il existe un signalement en attente.

- [ ] **Step 1 : tests rouges**

```python
def test_boutons_selon_niveau(client, monde): ...         # sec_p1 : Décès, Démission, Catégorie ; chef (circuit) : seulement Catégorie
def test_signaler_deces(client, monde): ...               # POST date → Signalement en attente, message, bandeau sur la fiche
def test_signaler_hors_perimetre_404(client, monde): ...  # sec_p1 sur m2 (P2) → 404 ; chef sur deces → 404
def test_rehabilitation_bloquee_affiche_raison(client, monde): ...  # démissionnaire depuis 1 mois → texte « Réhabilitation possible à partir du »
def test_erreurs_formulaire(client, monde): ...           # date future → message, rien créé
```

- [ ] **Step 2 :** rouge. **Step 3 :** implémenter. **Step 4 :** vert + ruff. **Step 5 :** commit `feat(mouvements): signalements depuis la fiche du membre`.

---

### Tâche 6 : Pages du BN — décisions

**Files :** Create `apps/mouvements/views_bn.py`, `templates/mouvements/bn_decisions.html`, `bn_mutation.html`, `bn_signalement.html`, `apps/mouvements/tests/test_pages_bn.py` ; Modify `apps/mouvements/urls.py`, `templates/accueil.html` (lien « Décisions à prendre (N) »).

**Interfaces :**
- Consumes : `bn_requis`, `decider_mutation`, `decider_signalement`.
- Produces :
  - `mouvements:bn_decisions` → `/bureau/bn/decisions/` : mutations « avis » ou « bn » et signalements « bn », les plus anciens d'abord.
  - `mouvements:bn_mutation` → `/bureau/bn/mutations/<pk>/` : membre, départ → arrivée, avis donnés (ou « Avis du circuit : pas encore donné »), mandats en cours qui seront clos, boutons « Valider la mutation » / « Refuser » avec commentaire.
  - `mouvements:bn_signalement` → `/bureau/bn/signalements/<pk>/` : détails, boutons « Confirmer » / « Refuser » avec motif obligatoire pour le refus. Une réhabilitation confirmée renvoie directement la **fiche PDF avec les identifiants** (`attachment; filename="fiche-{matricule}.pdf"`, `no-store`).
  - Les deux pages de décision : `MouvementRefuse` → message d'erreur sur la page, rien n'est modifié.

- [ ] **Step 1 : tests rouges**

```python
def test_decisions_reservees_au_bn(client, monde): ...      # sec_p1 → 403 sur les trois pages
def test_liste_decisions(client_technique, monde): ...       # une mutation et un signalement en attente apparaissent
def test_valider_mutation_page(client_technique, monde): ... # POST valider → 302, affectation changée, message « Mutation validée. »
def test_refus_signalement_motif_obligatoire(client_technique, monde): ...
def test_rehabilitation_renvoie_pdf(client_technique, monde): ...  # Content-Type application/pdf
def test_decision_refusee_affiche_message(client_technique, monde): ...  # mutation devenue impossible → 200 + message, rien changé
def test_lien_accueil(client_technique): ...                 # « Décisions à prendre » sur l'accueil
```

- [ ] **Step 2 :** rouge. **Step 3 :** implémenter. **Step 4 :** vert + ruff. **Step 5 :** commit `feat(mouvements): décisions du Bureau national`.

---

### Tâche 7 : Historique sur les fiches, documentation, captures

**Files :** Create `templates/mouvements/_historique.html`, `apps/mouvements/tests/test_historique.py` ; Modify `templates/bureaux/fiche_membre.html`, `templates/membres/ma_fiche.html`, `templates/membres/bn_fiche.html`, `docs/guide-maintenance.md` (§18 Mouvements : circuits de validation, règles de la réhabilitation, régulariser une date inconnue via l'administration technique), `CLAUDE.md` (points techniques : `apps/mouvements`, `changer_statut` seul point d'entrée des statuts), `docs/captures/` (demande de mutation, décision BN).

**Interfaces :**
- Produces : bloc « Historique » (date d'effet, libellé, motif, référence) sur les trois fiches ; « Aucun événement. » si vide. Fiche d'un membre décédé : « Décédé le JJ/MM/AAAA » sous le statut.

- [ ] **Step 1 : tests rouges**

```python
def test_historique_visible_partout(client, client_technique, monde): ...  # après un changement de catégorie : fiche bureau, fiche BN, ma fiche
def test_deces_affiche_date(client_technique, monde): ...                  # « Décédé le 01/11/2026 »
def test_historique_pas_chez_un_autre_membre(client, monde): ...           # membre simple → /membres/bn/<matricule>/ toujours 403
```

- [ ] **Step 2 :** rouge. **Step 3 :** implémenter + docs + captures. **Step 4 :** suite complète en arrière-plan (`DJANGO_DEBUG=True pytest -q`) + `ruff check .`. **Step 5 :** commit `feat(mouvements): historique sur les fiches ; docs`.

---

## Fin d'étape

- Relecture finale indépendante de toute la branche, puis une passe de corrections (test rouge → vert pour chaque correction).
- Push puis Pull Request vers `main` (option 2).
