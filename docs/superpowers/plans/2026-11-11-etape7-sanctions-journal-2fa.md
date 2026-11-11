# Étape 7 — Sanctions, journal, double vérification BN, correction exceptionnelle : plan de réalisation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal :** l'étape 7 apporte quatre choses :
- le BNC inscrit les sanctions, qui changent le statut automatiquement, avec un retour automatique à « Actif » à la date de fin ;
- le journal est non modifiable, complété et consultable par le BN ;
- la double vérification par code à 6 chiffres est obligatoire pour les comptes ayant un mandat national ;
- le BN peut corriger exceptionnellement les données d'intégration, avec un nouveau matricule si l'année ou la région change.

**Architecture :**
- Les sanctions vont dans `apps/mouvements`, à côté des autres changements de statut. Elles passent par `changer_statut`, qui reste le seul point d'entrée des statuts.
- Le journal (`apps/journal`) est verrouillé au niveau du modèle : pas de modification, pas de suppression. Une page BN filtrable permet de le consulter, et des appels à `journaliser` sont ajoutés aux points sensibles.
- La double vérification va dans une nouvelle application `apps/securite`. Elle comprend un TOTP RFC 6238 implémenté avec `hmac` (sans dépendance) et un intergiciel qui bloque toutes les pages tant que le code n'est pas vérifié. Le QR code est produit par `segno`, une bibliothèque Python pure.
- La correction exceptionnelle est un service de `apps/membres` qui réutilise `attribuer_matricule`.

**Spec :** `docs/superpowers/specs/2026-11-09-module1-fondations-design.md` — §6.4 (sanctions), §9.3 (double vérification), §9.4 (journal), §3.5 (correction exceptionnelle), §9.1 (droits), §10 (notifications).

## Global Constraints

- Tout texte visible en français ; TDD ; `ruff check .` ; secrets uniquement en variables d'environnement.
- **Seul le BNC** inscrit une sanction (`has_perm("membres.gerer_membres")`).
- Types de sanction (RI art. 154, 156, 162) : avertissement verbal, avertissement écrit, amende, blâme écrit, suspension temporaire de service (**15 jours au plus**), retrait temporaire de responsabilités, exclusion temporaire, exclusion définitive, autre (préciser).
- Degré de la faute : 1ᵉʳ, 2ᵉ ou 3ᵉ (RI art. 152).
- Statut : **Sanctionné** pour une suspension ou un retrait temporaire ; **Exclu** pour une exclusion ; avertissements, amende, blâme et « autre » sans changement de statut. Temporaire → retour automatique à « Actif » à la date de fin ; la sanction reste dans l'historique.
- Visibilité des sanctions : le membre, les bureaux de sa paroisse, de son circuit et de sa région, le BN.
- Journal **non modifiable et non effaçable**, consultable par le BN uniquement.
- Double vérification **obligatoire pour les comptes ayant un mandat national** (et le compte technique).

## Décisions prises dans ce plan

1. **Fin automatique des sanctions** : une commande quotidienne `fin_des_sanctions` (même principe que `alertes_echeances`) remet « Actif » à la date de fin, avec le motif « Fin de la sanction ». Elle ne le fait que si aucune autre sanction en cours ne justifie encore le statut. Une exclusion définitive n'a pas de date de fin.
2. **Statut le plus grave** : un membre exclu reste exclu même si une suspension lui est ajoutée. Une exclusion annule les mutations en cours (comme un décès).
3. **Pas de sanction** pour un membre décédé, démissionnaire, ou déjà exclu définitivement.
4. **Une sanction ne se supprime pas.** Une erreur se corrige par une nouvelle décision : le BN peut **lever** une sanction en cours, avec un motif ; c'est inscrit dans l'historique et au journal.
5. **Journal complété** : connexions réussies et échouées ; consultation des fiches (espace bureau et BN) ; réinitialisations de mot de passe ; décisions sur les photos ; enregistrement individuel ; validation d'un lot ; installation d'un bureau ; modification des coordonnées (ancienne et nouvelle valeur) ; sanctions ; corrections exceptionnelles ; double vérification (activation, échecs, réinitialisation).
6. **Double vérification** :
   - **Activation** : à la première connexion, l'application d'authentification (Google Authenticator, Microsoft Authenticator…) est enregistrée par QR code ou par clé.
   - **À chaque connexion** : un code à 6 chiffres est demandé. Un même code ne sert qu'une fois. Après 5 codes faux, la session est fermée.
   - **Perte du téléphone** : un autre membre du BN ou le mainteneur lance la commande `reinitialiser_double_verification <identifiant>`, documentée dans le guide.
   - **Tests** : la double vérification est désactivée par un réglage, sauf dans ses propres tests.
7. **Correction exceptionnelle** :
   - Le BN corrige l'année, la paroisse ou la région d'intégration, avec un motif obligatoire.
   - Si l'année ou la région change : nouveau matricule, identifiant de connexion mis à jour, ancien matricule noté dans l'historique de la fiche, membre notifié.
   - Si le membre n'a jamais été muté, sa seule affectation (« Intégration ») est corrigée aussi. Sinon, le parcours n'est pas touché.

## Review Focus

1. **Sanction rétroactive ou dates incohérentes** (fin avant début, suspension de plus de 15 jours, temporaire sans date de fin) → message, rien n'est créé. Test : Tâche 2 `test_sanctions_refusees`.
2. **Fin de sanction alors qu'une autre court encore** (suspension finie pendant une exclusion) → le statut reste « Exclu ». Test : Tâche 2 `test_fin_suspension_pendant_exclusion`.
3. **Contournement de la double vérification** (accès direct à une page BN, à l'administration, à un PDF, ou à une URL de l'espace bureau) → redirection vers la page du code. Test : Tâche 4 `test_toutes_les_pages_bloquees`.
4. **Code réutilisé ou deviné** → refusé ; 5 échecs → déconnexion. Test : Tâche 4 `test_code_rejoue_refuse`, `test_cinq_echecs_deconnecte`.
5. **Journal modifié ou effacé** (même par le code ou l'administration) → impossible. Test : Tâche 1 `test_journal_immuable`.

---

### Tâche 1 : Journal immuable, page BN, événements

- Les méthodes `EntreeJournal.save()` (sur une ligne existante) et `delete()` lèvent `JournalImmuable`. Le QuerySet par défaut interdit `update()` et `delete()`.
- **Page** `/journal/` (`journal:liste`, `bn_requis`), 50 entrées par page. Filtres : action (liste déroulante), auteur (identifiant), recherche texte dans l'unité et les détails, date du / au.
- **Nouvelles actions** : `CONNEXION`, `CONNEXION_ECHOUEE` (signaux `user_logged_in` et `user_login_failed`, avec l'identifiant tenté), `CONSULTATION_FICHE` (`bureaux.fiche_membre` et `membres.bn_fiche`), `REINITIALISATION` (`reinitialiser_mot_de_passe`), `PHOTO_DECISION`, `ENREGISTREMENT`, `LOT_VALIDE`, `INSTALLATION_BUREAU`, `COORDONNEES` (champs modifiés avec `{"champ": [ancien, nouveau]}`).
- Lien « Journal » dans le bloc BN de l'accueil.
- Tests : `test_journal_immuable`, `test_page_reservee_au_bn`, `test_filtres`, `test_connexion_journalisee`, `test_consultation_fiche_journalisee`, `test_coordonnees_ancienne_nouvelle_valeur`, et un test par événement ajouté.

### Tâche 2 : Sanctions (modèle et services)

- **Modèle** `Sanction` : membre, degré (1/2/3), type (choices ci-dessus), précision (obligatoire pour « autre »), date de début, date de fin (nullable), motif, référence de la décision, par, date ; `levee_le`, `levee_par`, `motif_levee`. Propriétés `effet` (`sanctionne` / `exclu` / `None`) et `en_cours(jour)`.
- **`enregistrer_sanction(*, membre, degre, type, date_debut, date_fin, motif, reference, precision, par, jour=None) -> Sanction`**. Règles : `date_fin ≥ date_debut` ; date de fin obligatoire pour les types temporaires (suspension, retrait temporaire, exclusion temporaire) ; suspension de 15 jours au plus (bornes incluses) ; statut admissible. Effets :
  - le statut est appliqué par `changer_statut` si `date_debut ≤ jour` et que la sanction est plus grave que le statut actuel ;
  - une exclusion annule les mutations en cours ;
  - notifications : bureaux de la paroisse, du circuit et de la région, et le membre s'il garde son accès ;
  - journal `SANCTION`.
- **`lever_sanction(*, sanction, motif, par, jour=None)`** et **`appliquer_sanctions(jour=None) -> tuple[int, int]`** (début des sanctions datées dans le futur, et fin des sanctions temporaires) ; commande `fin_des_sanctions`.
- Tests : `test_avertissement_sans_changement_de_statut`, `test_suspension_sanctionne_puis_fin`, `test_exclusion_definitive_desactive_et_annule_mutation`, `test_sanctions_refusees`, `test_fin_suspension_pendant_exclusion`, `test_sanction_future_appliquee_au_jour_dit`, `test_lever_sanction`, `test_fin_exclusion_temporaire_permet_rehabilitation_ulterieure`, `test_commande`.

### Tâche 3 : Sanctions (pages)

- **BN** : `/membres/bn/<matricule>/sanction/` (formulaire), lien « Inscrire une sanction » sur la fiche BN, et bouton « Lever » sur chaque sanction en cours (formulaire avec motif).
- **Bloc « Sanctions »** (type, degré, dates, motif, référence, état en cours / terminée / levée) sur la fiche du bureau, la fiche BN et « Ma fiche ».
- Tests : `test_sanction_reservee_au_bn`, `test_formulaire_sanction`, `test_sanctions_visibles_membre_bureaux_bn`, `test_lever_depuis_la_fiche`.

### Tâche 4 : Double vérification

- `apps/securite/totp.py` : `code_totp(secret_base32, instant) -> str`, `verifier(secret, code, instant, dernier_pas) -> int | None` (fenêtre ±1 pas, renvoie le pas accepté), `nouveau_secret() -> str`, `uri_provisioning(secret, identifiant) -> str`.
- **Modèle** `DoubleVerification(compte OneToOne, secret, active, date_activation, dernier_pas)`.
- **Intergiciel** `DoubleVerificationObligatoire`, placé après `ChangementMotDePasseObligatoire`. Si le réglage `DOUBLE_VERIFICATION_BN` est vrai et que `est_bn(user)` l'est aussi, il redirige vers `/securite/code/` (ou `/securite/activer/` si elle n'est pas encore activée) tant que la session n'a pas `double_verification_ok`. Seuls restent accessibles : ces pages, la déconnexion, le changement de mot de passe et `/static/`.
- **Pages** :
  - activation : QR SVG `segno` + clé + saisie d'un code de confirmation ;
  - code : 6 chiffres ; 5 échecs → déconnexion et message ;
  - les deux pages sont journalisées.
- Commande `reinitialiser_double_verification <identifiant>`. Fixture autouse racine `conftest.py` qui met `DOUBLE_VERIFICATION_BN = False` ; les tests de `apps/securite` le remettent à `True`.
- Tests :
  - vecteur RFC 6238 (secret « 12345678901234567890 », t = 59 → « 287082 ») ;
  - `test_activation`, `test_code_correct_ouvre_la_session`, `test_code_rejoue_refuse`, `test_cinq_echecs_deconnecte`, `test_toutes_les_pages_bloquees`, `test_membre_simple_non_concerne`, `test_commande_reinitialisation`.

### Tâche 5 : Correction exceptionnelle des données d'intégration

- `apps/membres/services.py::corriger_integration(*, membre, annee, paroisse, motif, par) -> Membre`. Elle est atomique. Si l'année ou la région change, elle appelle `attribuer_matricule` et met à jour `compte.identifiant`, l'historique (type `matricule`) et le membre notifié. Elle corrige la seule affectation si le membre n'a jamais été muté. Elle journalise `CORRECTION_INTEGRATION` avec les anciennes et nouvelles valeurs.
- Page BN `/membres/bn/<matricule>/corriger/`, avec motif obligatoire et confirmation.
- Tests : `test_correction_paroisse_meme_region_garde_matricule`, `test_correction_region_nouveau_matricule`, `test_connexion_avec_nouveau_matricule`, `test_motif_obligatoire`, `test_parcours_non_touche_si_mute`, `test_page_reservee_au_bn`.

### Tâche 6 : Documentation et captures

- `docs/guide-maintenance.md` §19 : sanctions, commande quotidienne, double vérification (perte du téléphone), journal, correction exceptionnelle. Ajouter `fin_des_sanctions` à la tâche quotidienne (§14).
- `CLAUDE.md` mis à jour. Captures : page du journal, formulaire de sanction, page du code.
- Suite complète, relecture finale indépendante, corrections, Pull Request.
