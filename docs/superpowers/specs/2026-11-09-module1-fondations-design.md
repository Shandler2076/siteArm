# Cahier des charges — Module 1 : Fondations

**Projet :** Site de gestion des membres de l'Armée du Salut — Bénin
**Date :** 9 novembre 2026
**Statut :** Validé le 10 novembre 2026
**Langue du site :** français

---

## 0. Vue d'ensemble du projet

Le site complet est découpé en 5 modules, livrés dans cet ordre :

| Ordre | Module | Contenu |
|---|---|---|
| **1** | **Fondations** *(ce document)* | Comptes, rôles, organisation territoriale, fiche membre, matricule, parcours, mandats, mutations, sanctions, décès, listes, journal |
| 2 | Grades et éligibilité | Historique des grades, conditions de passage, listes d'éligibles |
| 3 | Événements et présences | Invitations, convocations ciblées, historique de participation |
| 4 | Communication | Messages officiels du BN, notifications, espace documents commun, règlement intérieur |
| 5 | Médias | Photos et vidéos des événements |

Chaque module suit le même cycle : conception → cahier des charges validé → plan → développement → test sur le site d'essai → mise en ligne.

---

## 1. Choix techniques

| Élément | Choix | Raison |
|---|---|---|
| Type de site | Site sur mesure | Règles spécifiques (matricule, mutations, périmètres, sanctions) impossibles à respecter proprement avec WordPress ou un outil sans code |
| Langage / framework | **Python / Django** | Le mainteneur connaît Python ; espace d'administration et sécurité intégrés |
| Base de données | **PostgreSQL** | Fiable, verrouillage transactionnel pour les compteurs de matricule |
| Affichage | Pages générées par le serveur (gabarits Django) + **HTMX** | Léger pour les téléphones et les connexions faibles ; tout reste en Python |
| Application mobile | **PWA** (site installable sur l'écran d'accueil) | Pas besoin du Play Store |
| Hébergement | **Hébergeur géré (PaaS)**, de préférence francophone (Scalingo ou Clever Cloud) | Sécurité du système, sauvegardes et HTTPS gérés par l'hébergeur ; adapté à un mainteneur seul |
| Photos, PDF, documents | Stockage objet privé | Peu coûteux, séparé du serveur |
| Vidéos (module 5) | Chaîne YouTube de l'église, intégrée au site | Gratuit, qualité adaptée au réseau mobile |
| Nom de domaine | **.bj** | Choix de l'église |
| Code source | Dépôt GitHub `siteArm` | Historique, tests automatiques, retour arrière possible |

Le comparatif d'hébergement chiffré sera présenté avant la mise en ligne (tarifs vérifiés à ce moment-là).

---

## 2. Organisation territoriale

### 2.1 Hiérarchie

```
National
 └── Région (code numérique 01, 02, 03…)
      └── Circuit
           └── Paroisse
```

### 2.2 Règles

- Chaque **région** reçoit un **code numérique à 2 chiffres**, attribué une fois pour toutes. Un code n'est **jamais réattribué**, même si la région est fermée ou divisée.
- Chaque circuit est rattaché à une région ; chaque paroisse à un circuit.
- On ne supprime jamais une région, un circuit ou une paroisse : on la **ferme** (l'historique reste intact).
- La liste initiale des régions, circuits et paroisses est fournie par l'église et chargée au démarrage (version provisoire : `docs/donnees/regions-circuits-paroisses.md`, 13 régions, 87 circuits, 427 paroisses ; version définitive attendue après le 25 décembre).

---

## 3. Le membre

### 3.1 Fiche membre

| Rubrique | Champs | Remarques |
|---|---|---|
| Identité | Nom, prénoms, sexe, date de naissance, lieu de naissance, situation matrimoniale | |
| Photo d'identité | Photo en **tenue de l'Armée du Salut** | Déposée **par le membre lui-même** (voir 3.4) |
| Pièce d'identité | NPI et/ou photo du CIP | **Photo du CIP visible par le BN uniquement** |
| Contact | Téléphone, numéro WhatsApp, email (facultatif), quartier, ville | |
| Autres | Profession actuelle, personne à contacter en cas d'urgence (nom + téléphone) | |
| Intégration | Année d'intégration, paroisse d'intégration, région d'intégration | **Non modifiables** (sauf correction exceptionnelle, voir 3.5) |
| Matricule | `AAAA-RRAS-NNNN` (ex. `2015-01AS-0157`) | Généré automatiquement, définitif |
| Affectation actuelle | Paroisse (→ circuit → région) | Mise à jour uniquement par mutation validée |
| Fonctions | Mandats en cours et passés | Voir section 5 |
| Statut | Actif, Sanctionné, Exclu, Décédé | Termes définitifs selon le règlement intérieur |
| Grade | Grade actuel et historique | **Module 2** |
| Caractéristiques du règlement intérieur | À définir | Ajoutées quand le règlement sera fourni |

Le **reçu** (présent, perdu, numéro) **n'est pas enregistré** sur la fiche. Les cas de reçu perdu sont réglés hors du site, lors de la centralisation.

### 3.2 Matricule

- **Format :** `AAAA-RRAS-NNNN` — exemple : `2015-01AS-0157`
  - `AAAA` : année d'intégration (4 chiffres)
  - `RR` : code de la région d'intégration (2 chiffres)
  - `AS` : lettres fixes signifiant **« Armée du Salut »**, toujours présentes
  - `NNNN` : numéro d'ordre (4 chiffres)
- **Lecture de l'exemple :** membre intégré en **2015**, dans la région de code **01**, **157ᵉ** membre enregistré pour cette année et cette région.
- **Compteur :** un compteur distinct **par couple (année d'intégration, région d'intégration)**, qui commence à 0001.
- **Génération :** le numéro suivant est pris et le compteur incrémenté **dans une seule opération verrouillée** en base de données. Deux enregistrements simultanés ne peuvent jamais produire le même matricule.
- **Membres des années passées :** on saisit l'année réelle d'intégration ; le numéro d'ordre suit l'ordre de saisie sur le site (il n'existe pas de registre antérieur).
- Le matricule ne contient ni la paroisse ni le nom de la région. Il **ne change jamais**, même après une mutation.
- **Capacité :** 99 régions, 9 999 intégrations par région et par an.

### 3.3 Statuts

| Statut | Accès au site | Comment il est attribué |
|---|---|---|
| Actif | Oui | Par défaut |
| Sanctionné | **Oui** (espace personnel) | Automatique à l'enregistrement d'une sanction temporaire par le BN ; retour à « Actif » automatique à la date de fin |
| Exclu | **Non** (compte désactivé) | Automatique à l'enregistrement d'une sanction d'exclusion par le BN |
| Décédé | **Non** (compte désactivé) | Signalement par la paroisse, confirmation par le BN |

### 3.4 Photo d'identité

- Le **membre dépose lui-même** sa photo depuis son espace personnel.
- Exigences : photo en **tenue de l'Armée du Salut**. Les caractéristiques précises (cadrage, fond, etc.) seront fixées par l'église et affichées sur la page de dépôt.
- Le site vérifie automatiquement le format (JPEG/PNG), la taille maximale et les dimensions minimales.
- **La photo est soumise à validation par le Bureau national uniquement**, qui l'accepte ou la refuse avec un motif (les bureaux de paroisse ne valident pas, pour éviter tout arrangement local). Tant qu'elle n'est pas acceptée, l'ancienne photo (ou un emplacement vide) reste affichée.
- La fiche d'identification PDF générée à l'enregistrement ne comporte donc pas encore de photo ; le membre et les bureaux peuvent **régénérer la fiche** une fois la photo validée.
- Le BN dispose d'une **file d'attente des photos à valider** (photo, nom, matricule, boutons Accepter / Refuser + motif).

### 3.5 Qui modifie quoi

| Informations | Qui peut modifier |
|---|---|
| Téléphone, WhatsApp, email, quartier, ville, profession, personne à contacter | Le membre lui-même, et le bureau de sa paroisse |
| Photo d'identité | Le membre (dépôt) ; validation par le BN uniquement |
| Nom, prénoms, sexe, date et lieu de naissance, situation matrimoniale, NPI, photo du CIP | BN uniquement |
| Année, paroisse et région d'intégration, matricule | Personne en temps normal. **Correction exceptionnelle par le BN** avec motif obligatoire, inscrite au journal. Si l'année ou la région change, un nouveau matricule est attribué et l'ancien reste noté sur la fiche. |

Toute modification est inscrite au journal (ancienne et nouvelle valeur).

---

## 4. Parcours (historique des affectations)

- Chaque **affectation** comprend : membre, paroisse, **circuit et région tels qu'ils étaient à cette date**, date de début, date de fin (vide = affectation actuelle), motif (intégration, mutation n°…).
- Le circuit et la région sont **enregistrés au moment de l'affectation** : une réorganisation future du territoire ne réécrit pas le passé.
- Le parcours est **rempli automatiquement** (intégration, mutation validée). Personne ne le modifie à la main.
- **Visible par :** le membre lui-même, les bureaux de sa paroisse, de son circuit et de sa région **actuels**, et le BN.
- Affichage sous forme de frise chronologique sur la fiche.

### 4.1 Anciens membres

Après le départ d'un membre (mutation validée), l'ancienne paroisse, l'ancien circuit et l'ancienne région (s'ils changent) le retrouvent dans une liste **« Anciens membres »**, en lecture seule, avec uniquement : nom, prénoms, matricule, dates de son passage chez eux, nouvelle affectation. **Pas de coordonnées personnelles, pas la suite du parcours.**

---

## 5. Fonctions, mandats et bureaux

### 5.1 Fonctions

- Une **fonction** a : un nom (Président, Vice-président, Secrétaire, Secrétaire adjoint…), un niveau (paroisse, circuit, région, national), et une case **« droit de gérer le site »**.
- **Au démarrage**, seules les fonctions **Président** et **Secrétaire** ont le droit de gérer, à chaque niveau.
- Le BN peut accorder ce droit à d'autres fonctions plus tard, **depuis le site, sans modifier le code**.
- La liste des fonctions de chaque niveau est fournie par l'église.

### 5.2 Mandats

- Un **mandat** relie : un membre, une fonction, une unité précise (telle paroisse, tel circuit, telle région, ou le national), une date de début, une date de fin.
- **Une même personne peut avoir plusieurs mandats en même temps, à tous les niveaux, jusqu'au Bureau national.**
- Les droits d'une personne sont **la somme des droits de ses mandats en cours**.
- Les mandats passés restent dans l'historique de la fiche.

### 5.3 Comptes personnels

- Chaque personne a **un seul compte**, à son nom, avec connexion par **matricule + mot de passe**.
- **Aucun code d'accès partagé** par bureau. Les droits de bureau découlent des mandats en cours.
- Quand un mandat se termine, la personne redevient automatiquement membre simple et garde son espace personnel.

---

## 6. Circuits de travail

### 6.1 Enregistrement individuel d'un membre (par le BN)

1. Le Secrétaire national (ou toute personne du BN autorisée) saisit la fiche : identité, contact, année + paroisse + région d'intégration.
2. Le site **détecte les doublons possibles** (même nom + même date de naissance, ou même NPI) et affiche un avertissement ; le secrétaire décide de poursuivre ou non.
3. Le site génère le **matricule**, crée le **compte** avec un **mot de passe provisoire** et ouvre l'**affectation** dans la paroisse d'intégration.
4. Le site génère la **fiche d'identification PDF** (nom, matricule, paroisse, circuit, région, identifiants de connexion), à imprimer ou envoyer par WhatsApp.
5. Les bureaux de la paroisse, du circuit et de la région sont **notifiés**.
6. À la **première connexion**, le membre doit **changer son mot de passe**.

### 6.2 Enregistrement par lots (fichier Excel)

1. Le site fournit un **modèle Excel officiel** à télécharger : colonnes fixes, listes déroulantes (sexe, situation matrimoniale, paroisses), consignes de saisie (format de date…).
2. Chaque **région** remplit le modèle avec ses nouveaux membres et **l'envoie au Secrétaire national** (hors site).
3. Le **Secrétaire national dépose le fichier** sur le site, en indiquant la région concernée → création d'un **lot**.
4. **Écran de contrôle du lot (aperçu avant génération).** Le site lit le fichier **sans rien créer** et affiche un tableau de toutes les lignes, **telles que le site les a comprises** (nom, prénoms, sexe, date de naissance, paroisse, année d'intégration…), avec pour chaque ligne un état :
   - ✅ **correcte** ;
   - ⚠️ **doublon possible** (avec un membre existant ou au sein du fichier), avec lien vers la fiche existante pour comparer ;
   - ❌ **erreur** (champ obligatoire vide, date invalide, paroisse inconnue ou hors de la région…), avec explication.
   Un résumé indique : nombre de lignes, répartition par année d'intégration et par paroisse, nombre de lignes correctes / à vérifier / en erreur.
   Sur cet écran, le BN peut :
   - **corriger directement une ligne** (petites erreurs de saisie), la correction étant inscrite au journal ;
   - **écarter une ligne** (elle ne sera pas créée) ;
   - trancher chaque doublon possible (**garder** ou **écarter**) ;
   - **enregistrer le lot en brouillon** et y revenir plus tard ;
   - ou **redéposer un fichier corrigé** par la région.
   Le lot est sauvegardé tel quel tant qu'il n'est pas validé : **aucun matricule, aucun compte n'existe à ce stade.**
5. **Confirmation finale.** Le bouton « Valider et générer » n'est actif que lorsqu'il ne reste **aucune erreur ni aucun doublon non tranché**. Un écran récapitulatif s'affiche (« 47 membres vont être créés pour la région 03 : 30 en 2026, 17 en 2015… ») et demande une confirmation explicite. Le BN **valide le lot**.
6. Le site génère **en une seule fois** : les matricules, les comptes avec mots de passe provisoires, les affectations, **un PDF regroupant toutes les fiches d'identification**, une **liste récapitulative** (nom → matricule) pour la région, et les notifications aux bureaux concernés.
7. Le lot et son fichier d'origine restent archivés (consultables par le BN).

La validation d'un lot est **tout ou rien** : si une erreur technique survient pendant la génération, aucun matricule du lot n'est attribué.

### 6.3 Mutation

1. Le bureau de la **nouvelle paroisse** crée une **demande de mutation** (matricule du membre).
2. Notifications : ancienne paroisse, circuit de départ, région de départ, BN.
3. Le **circuit de départ** donne son avis (favorable / défavorable + commentaire).
4. La **région de départ** donne son avis (favorable / défavorable + commentaire).
5. Le **BN valide ou refuse** (il peut décider même si un avis manque).
6. Si validée, automatiquement : clôture de l'ancienne affectation, ouverture de la nouvelle, passage dans les « Anciens membres » des anciennes unités concernées, notifications à tous les bureaux concernés et au membre.

Une seule demande de mutation en cours par membre. États : *En attente d'avis → En attente du BN → Validée / Refusée*.

### 6.4 Sanction

1. **Seul le BN** enregistre une sanction : type (selon le règlement), date de début, date de fin éventuelle, motif résumé, référence de la décision.
2. Le statut change automatiquement (Sanctionné ou Exclu).
3. Les bureaux de la paroisse, du circuit et de la région sont notifiés.
4. Sanction temporaire : retour automatique à « Actif » à la date de fin ; la sanction reste dans l'historique.
5. **Visible par** : le membre concerné, les bureaux de sa paroisse, de son circuit, de sa région, et le BN.

Les types exacts de sanctions seront repris du règlement intérieur.

### 6.5 Décès

1. Le bureau de la paroisse **signale** le décès (avec la date).
2. Le **BN confirme**.
3. Statut « Décédé », compte désactivé, fiche conservée en archives, bureaux notifiés.

### 6.6 Changement de bureau

1. Le **BN** enregistre le nouveau bureau d'une unité : pour chaque fonction, le membre et la date de début.
2. À cette date, automatiquement : clôture des anciens mandats (les anciens responsables perdent l'accès à l'espace du bureau), ouverture des nouveaux.
3. Anciens et nouveaux responsables sont notifiés.

### 6.7 Mot de passe oublié

- Le membre s'adresse au **bureau de sa paroisse**. Le Président ou le Secrétaire génère un **nouveau mot de passe provisoire** (à changer à la connexion suivante). Le BN peut aussi le faire.
- La réinitialisation d'un compte du **BN** n'est possible que par un autre membre du BN, ou par le mainteneur technique selon la procédure du guide de maintenance.
- Chaque réinitialisation est inscrite au journal.

---

## 7. Listes et statistiques en temps réel

### 7.1 Listes

- Chaque bureau (paroisse, circuit, région, BN) peut, **à tout moment**, générer la liste des membres **de son périmètre**.
- **Colonnes au choix :** matricule, nom, prénoms, sexe, **âge**, téléphone, WhatsApp, paroisse, circuit, statut, fonction(s) (et grade au module 2).
- **Filtres :** statut, sexe, paroisse, circuit, année d'intégration, fonction, **âge** (« moins de X ans », « plus de Y ans », « entre X et Y ans », calculé à la date du jour depuis la date de naissance) et **grade** (module 2). Les filtres se combinent (ex. : Capitaines de plus de 40 ans du circuit de Davo).
- **Formats :** **PDF** (en-tête officiel, date et heure de génération) et **Excel**.
- La photo du CIP n'apparaît **jamais** dans une liste.
- **Chaque génération de liste est inscrite au journal.**

### 7.2 Page « Statistiques »

- Chaque bureau (paroisse, circuit, région, BN) dispose d'une page **« Statistiques »**, limitée à **son périmètre**, toujours à jour.
- **Chiffres affichés** (membres actifs par défaut, autres statuts sélectionnables) :
  - total des membres ;
  - par **sexe** ;
  - par **tranche d'âge** : par défaut *moins de 18 ans*, *18 à 40 ans*, *plus de 40 ans* ; les tranches sont **modifiables par le BN** depuis le site ;
  - par **statut** (actif, sanctionné, exclu, décédé) ;
  - par **grade** (module 2) — par ex. nombre de Capitaines ;
  - **répartition par unité inférieure** : par région (BN), par circuit (région), par paroisse (circuit).
- **Chaque chiffre est cliquable** et ouvre la **liste correspondante** (section 7.1), avec les filtres déjà appliqués, exportable en PDF ou Excel.
- Un membre sans date de naissance est compté dans une ligne **« Âge non renseigné »**.
- Export de la page de statistiques en **PDF** (en-tête officiel, date et heure).
- Chaque export est **inscrit au journal**.

---

## 8. Espaces du site

| Espace | Pour qui | Contenu |
|---|---|---|
| **Espace membre** | Tout membre connecté | Sa fiche, son parcours, ses fonctions, ses sanctions éventuelles, sa fiche PDF, le dépôt de sa photo, la modification de ses coordonnées, le changement de mot de passe, ses notifications |
| **Espace bureau** | Titulaires d'une fonction avec droit de gérer (paroisse, circuit, région) | Membres de son périmètre, anciens membres, listes, demandes et avis de mutation, signalement de décès, réinitialisation des mots de passe (paroisse) |
| **Espace Bureau national** | Titulaires d'une fonction nationale avec droit de gérer | Tout ce qui précède pour tout le pays + enregistrement individuel et par lots (avec écran de contrôle), validation des photos, validation des mutations, sanctions, confirmation des décès, gestion des bureaux et des fonctions, gestion des régions, circuits et paroisses, journal |

Une personne avec plusieurs mandats peut **passer d'un espace à l'autre** (sélecteur d'unité).

---

## 9. Sécurité et droits d'accès

### 9.1 Matrice des droits

| Action | Membre simple | Bureau paroisse | Bureau circuit | Bureau région | BN |
|---|---|---|---|---|---|
| Voir sa propre fiche | ✅ | ✅ | ✅ | ✅ | ✅ |
| Voir les fiches de son périmètre | ❌ | Sa paroisse | Son circuit | Sa région | Tous |
| Voir les anciens membres (lecture limitée) | ❌ | ✅ | ✅ | ✅ | ✅ |
| Voir le parcours complet | Le sien | Membres actuels | Membres actuels | Membres actuels | ✅ |
| Voir les sanctions | La sienne | ✅ | ✅ | ✅ | ✅ |
| Enregistrer une sanction | ❌ | ❌ | ❌ | ❌ | ✅ |
| Voir la photo du CIP | La sienne | ❌ | ❌ | ❌ | ✅ |
| Générer des listes, consulter les statistiques | ❌ | ✅ | ✅ | ✅ | ✅ |
| Demander une mutation | ❌ | ✅ (arrivée) | ❌ | ❌ | ✅ |
| Donner un avis de mutation | ❌ | ❌ | ✅ (départ) | ✅ (départ) | — |
| Valider une mutation | ❌ | ❌ | ❌ | ❌ | ✅ |
| Signaler un décès | ❌ | ✅ | ❌ | ❌ | ✅ |
| Confirmer un décès | ❌ | ❌ | ❌ | ❌ | ✅ |
| Valider une photo | ❌ | ❌ | ❌ | ❌ | ✅ |
| Enregistrer des membres (individuel, lot) | ❌ | ❌ | ❌ | ❌ | ✅ |
| Gérer bureaux, fonctions, territoire | ❌ | ❌ | ❌ | ❌ | ✅ |
| Réinitialiser un mot de passe | ❌ | Ses membres | ❌ | ❌ | ✅ |
| Consulter le journal | ❌ | ❌ | ❌ | ❌ | ✅ |

*« Bureau » = titulaire d'un mandat en cours dont la fonction a le droit de gérer (au démarrage : Président et Secrétaire).*

### 9.2 Gardien des périmètres

- Un **composant central unique** décide, pour chaque page et chaque action, si la personne connectée y a droit, en fonction de ses **mandats en cours**.
- Toutes les vues et toutes les requêtes de données passent par lui. Les listes sont **filtrées à la source** (en base de données), jamais seulement à l'affichage.
- C'est le composant **le plus testé** du projet.

### 9.3 Comptes

- Mots de passe **hachés** (irréversibles), 8 caractères minimum, mots de passe trop simples refusés (dont le matricule).
- **Blocage temporaire** après 5 échecs de connexion.
- **Déconnexion automatique** après inactivité (plus courte pour les comptes ayant un mandat de bureau, par ex. 30 min).
- **Double vérification (code à 6 chiffres via application d'authentification) obligatoire pour les comptes ayant un mandat national.**
- **HTTPS** partout.

### 9.4 Données

- Photo du CIP et photos d'identité stockées dans un espace **privé**, servies uniquement par liens temporaires après contrôle des droits.
- **Journal** non modifiable et non effaçable : connexions, consultations de fiches, modifications (ancienne / nouvelle valeur), listes générées, réinitialisations, validations, sanctions, lots.
- **Sauvegardes** : quotidienne automatique (hébergeur) + copie hebdomadaire chiffrée chez un autre fournisseur + test de restauration trimestriel.
- **Alertes de sécurité** automatiques sur les dépendances (GitHub).

### 9.5 Protection des données personnelles (APDP)

- Page **« Protection de vos données »** : ce qui est collecté, pourquoi, qui y a accès, durée de conservation.
- Chaque membre voit toutes ses données et peut demander une correction.
- Un **document de synthèse** est préparé pour la déclaration auprès de l'APDP. **La mise en ligne réelle a lieu après cette déclaration.**

---

## 10. Notifications

- Notifications **internes au site** (cloche + liste), avec lien vers l'élément concerné, statut lu / non lu.
- Événements notifiés : nouveau membre dans le périmètre, demande / avis / décision de mutation, membre parti du périmètre, sanction, décès confirmé, début / fin de mandat, photo acceptée / refusée, lot validé.
- Envoi par **email** quand le destinataire en a un. **SMS / WhatsApp : hors module 1** (étudiés au module 4, coût à évaluer).

---

## 11. Interface

- Conçue **d'abord pour le téléphone**, utilisable sur ordinateur.
- Pages légères, fonctionnement correct sur connexion mobile faible.
- **Installable** sur l'écran d'accueil (PWA).
- Design sobre et professionnel, aux couleurs et avec le logo de l'église (fournis par l'église).
- Fiches PDF et listes PDF avec en-tête officiel.

---

## 12. Qualité, tests et maintenance

### 12.1 Tests automatiques

Écrits **avant** le code de chaque fonctionnalité. Couvrent au minimum :
- format `AAAA-RRAS-NNNN` et unicité du matricule, y compris en enregistrements simultanés ; séparation des compteurs par année et région ;
- toutes les lignes de la matrice des droits (9.1), notamment : membre simple bloqué sur la fiche d'un autre ; paroisse bloquée hors de son périmètre ; perte des droits à la fin d'un mandat ; photo du CIP refusée hors BN ;
- mutations (validée → mises à jour ; refusée → aucun changement) ;
- sanctions (changement de statut, exclu ne peut plus se connecter, expiration automatique) ;
- import par lots (aperçu sans aucune création, détection des erreurs et doublons, corrections et lignes écartées, validation bloquée tant qu'il reste des erreurs, tout ou rien) ;
- validation des photos réservée au BN ;
- listes et statistiques (périmètre respecté, calcul de l'âge au jour près, tranches d'âge aux bornes exactes, chiffres égaux au nombre de lignes de la liste ouverte, inscription au journal).

### 12.2 Parcours d'une modification

Modification → tests automatiques sur GitHub (blocage si échec) → relecture et accord du mainteneur → **site d'essai** → **vrai site**.

### 12.3 Surveillance

Alerte email si le site est inaccessible ; rapport détaillé des erreurs.

### 12.4 Documentation (en français)

- Guide de maintenance (mise à jour, restauration, ajout de région, réinitialisation d'un compte BN…).
- Guide utilisateur pour les bureaux (avec captures d'écran).
- Fichier de contexte pour les assistants IA.

---

## 13. Étapes de livraison du module 1

1. Organisation territoriale + comptes + connexion
2. Fiche membre + matricule + fiche PDF + dépôt et validation de la photo
3. Fonctions, mandats, bureaux + gardien des périmètres + espaces
4. Enregistrement par lots (Excel)
5. Listes et statistiques en temps réel (PDF / Excel) — le volet « grade » s'active avec le module 2
6. Mutations + décès
7. Sanctions + journal + double vérification BN
8. Mise en ligne réelle (après comparatif d'hébergement et déclaration APDP)

Chaque étape est testable sur le site d'essai.

---

## 14. Éléments à fournir par l'église

| Élément | Nécessaire pour |
|---|---|
| Liste des régions, circuits et paroisses avec leurs rattachements | Étape 1 |
| Liste des fonctions de chaque bureau, à chaque niveau | Étape 3 |
| Logo et couleurs officielles | Interface |
| Caractéristiques exigées pour la photo en tenue | Étape 2 |
| Termes officiels des statuts et des types de sanctions | Étape 7 |
| Règlement intérieur, liste des grades, conditions de passage | Module 2 |

---

## 15. Hors du module 1

- Grades et éligibilité (module 2)
- Événements, invitations, présences (module 3)
- Messages officiels, espace documents, règlement intérieur en ligne, SMS / WhatsApp (module 4)
- Photos et vidéos des événements (module 5)
- Inscription libre des membres : **exclue** (enregistrement uniquement par le BN)
