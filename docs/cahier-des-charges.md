# Cahier des charges — Site de gestion des membres de l'Armée du Salut du Bénin

---

## Préambule

L'Armée du Salut du Bénin, mouvement de la Congrégation Chrétienne de l'Ordre Sacré Éternel des
Chérubins et Séraphins « Mont Sion » du Bénin, rassemble ses membres dans des unités paroissiales,
des sections de circuit et des régions, sous l'autorité du Bureau National de Commandement (BNC).

Jusqu'ici, le suivi des membres repose sur des reçus de consécration, des registres tenus localement
et des échanges entre bureaux. Il est donc difficile de connaître à tout moment l'effectif exact du
mouvement, de suivre le parcours d'un membre d'une paroisse à l'autre, de préparer les listes dont les
bureaux ont besoin, ou de garantir que les décisions du BNC (mutations, sanctions, réhabilitations)
sont appliquées partout de la même façon.

Le présent cahier des charges décrit le site internet qui répondra à ces besoins. Il fixe ce que le
site doit faire, pour qui, selon quelles règles, et dans quel ordre il est construit. Il s'appuie sur le
**règlement intérieur** du mouvement (projet reçu le 10 novembre 2026, à confirmer à son entrée en
vigueur) et sur les décisions prises au fil de la conception avec le Bureau National.

Le document est organisé en quatre parties :

1. **Le projet** : objectifs, principes, découpage en modules, acteurs.
2. **Le module 1 — Fondations** : la gestion des membres, décrite en détail.
3. **Les modules suivants** : grades et cotisations mensuelles (module 2, décrit en détail),
   puis événements, communication, médias.
4. **Réalisation et exploitation** : choix techniques, hébergement, qualité, maintenance, calendrier.

Un lexique figure en annexe.

*KOUDAKPO Thoovi Marc Aurel, mainteneur du site, pour le Bureau National de Commandement.*

---

# Partie I — Le projet

## 1. Objectifs

Le site doit permettre de :

- **connaître chaque membre** grâce à une fiche unique, identifiée par un **matricule définitif** ;
- **suivre son parcours** dans le mouvement : paroisses successives, fonctions occupées, catégorie,
  statut, sanctions éventuelles, grades et cotisations mensuelles (module 2) et participation aux activités (module 3) ;
- **donner à chaque bureau** (paroisse, circuit, région, national) une vue **à jour et limitée à son
  périmètre**, avec des listes et des statistiques en temps réel ;
- **faire circuler les décisions** selon les circuits prévus par le règlement : mutations,
  signalements, validations par le BNC, avec des notifications à chaque étape ;
- **garder la trace** de toutes les opérations sensibles dans un journal qui ne peut être ni modifié
  ni effacé ;
- **suivre les cotisations mensuelles** de chaque membre, mois par mois, à chaque niveau ;
- **protéger les données personnelles** des membres, conformément à la loi béninoise.

## 2. Principes directeurs

| Principe | Ce qu'il signifie concrètement |
|---|---|
| **En français** | Tous les textes du site, des documents et des messages sont en français. |
| **D'abord pour le téléphone** | Les pages sont pensées pour un téléphone et une connexion mobile faible ; elles restent utilisables sur ordinateur. |
| **Pas d'inscription libre** | Seul le Bureau National enregistre les membres. Personne ne peut se créer un compte. |
| **Chacun voit son périmètre, et rien de plus** | Un bureau ne voit que les membres de son unité ; un membre simple ne voit que sa propre fiche. |
| **Les décisions restent au BNC** | Mutations, décès, démissions, réhabilitations, changements de catégorie et sanctions sont validés par le Bureau National. |
| **Rien ne s'efface** | On ne supprime ni un membre, ni une paroisse, ni une sanction : on ferme, on lève, on archive. L'historique reste vrai. |
| **Tout est tracé** | Chaque opération sensible est inscrite au journal, avec son auteur, sa date et son contenu. |
| **Simple à maintenir** | Le site est conçu pour être entretenu par une seule personne, avec une documentation complète en français. |

## 3. Découpage en modules

Le site est construit en cinq modules, livrés l'un après l'autre. Chaque module suit le même
cycle : conception, cahier des charges validé, plan de réalisation, développement, essai sur le site
d'essai, puis mise en ligne.

| Ordre | Module | Contenu | État |
|---|---|---|---|
| **1** | **Fondations** | Comptes, organisation territoriale, fiche membre, matricule, parcours, fonctions et bureaux, enregistrement par lots, listes et statistiques, mutations, décès, démissions, réhabilitations, sanctions, journal, sécurité | **Réalisé** ; mise en ligne en préparation |
| **2** | **Grades et cotisations** | Grade actuel et historique, listes et statistiques par grade, éligibilité ; cotisations mensuelles (CM) mois par mois, membres à jour ou en retard | **Cahier des charges rédigé (§ 15 et 16)** ; réalisation après validation |
| 3 | Événements et présences | Activités, invitations, convocations ciblées, présences | À concevoir |
| 4 | Communication | Messages officiels, espace documents, règlement intérieur en ligne, SMS / WhatsApp | À concevoir |
| 5 | Médias | Photos et vidéos des activités | À concevoir |

## 4. Acteurs

| Acteur | Rôle sur le site |
|---|---|
| **Bureau National de Commandement (BNC)** | Enregistre les membres, valide les décisions, inscrit les sanctions, installe les bureaux, gère le territoire et consulte le journal. Ses comptes sont protégés par une double vérification. |
| **Bureau Régional de Coordination (BRC)** | Consulte les membres de sa région, établit listes et statistiques, donne son avis sur les mutations au départ de la région, signale les changements de catégorie. |
| **Bureau de la Section de Circuit** | Mêmes possibilités à l'échelle du circuit ; donne son avis sur les mutations au départ du circuit. |
| **Bureau de l'Unité paroissiale** | Consulte les membres de sa paroisse, demande les mutations vers sa paroisse, signale les décès, démissions et changements de catégorie, demande les réhabilitations, réinitialise les mots de passe de ses membres. |
| **Membre** | Consulte sa fiche et son parcours, met à jour ses coordonnées, dépose sa photo, reçoit les notifications qui le concernent. |
| **Mainteneur** | Installe et met à jour le site, veille aux sauvegardes, assiste le BNC pour les opérations techniques (par exemple la réinitialisation d'une double vérification). |

Dans chaque bureau, ce sont les **titulaires d'une fonction « avec droit de gérer »** qui agissent sur
le site (voir § 8). Les autres membres du bureau gardent un accès de membre simple.

---

# Partie II — Module 1 : Fondations

## 5. Organisation territoriale

### 5.1 Hiérarchie

Le mouvement est organisé en quatre niveaux :

**National → Région → Circuit → Paroisse**

Chaque circuit est rattaché à une région, chaque paroisse à un circuit.

### 5.2 Règles

- Chaque **région** reçoit un **code numérique à deux chiffres** (01, 02, 03…), attribué une fois pour
  toutes. Un code n'est **jamais réattribué**, même si la région est fermée ou divisée.
- On ne supprime jamais une région, un circuit ou une paroisse : on la **ferme**, et on peut la
  **rouvrir**. Une unité fermée reste visible dans l'historique des membres qui y sont passés.
- La liste des régions, circuits et paroisses est fournie par l'Église. La version actuelle,
  provisoire, compte **13 régions, 87 circuits et 427 paroisses**. La version définitive est attendue
  après le pèlerinage du 25 décembre 2026 ; elle sera chargée sans perte de données.

## 6. Le membre

### 6.1 La fiche

| Rubrique | Informations |
|---|---|
| Identité | Nom, prénoms, sexe, date de naissance, lieu de naissance, situation matrimoniale |
| Photo d'identité | Photo en **tenue de l'Armée du Salut**, déposée par le membre lui-même (§ 6.4) |
| Pièce d'identité | NPI et/ou photo du CIP — **la photo du CIP n'est visible que par le BNC** |
| Contact | Téléphone, numéro WhatsApp, e-mail (facultatif), quartier, ville |
| Autres | Profession, personne à contacter en cas d'urgence (nom et téléphone) |
| Intégration | Année, paroisse et région d'intégration — **non modifiables** sauf correction exceptionnelle (§ 6.7) |
| Matricule | Généré automatiquement, **définitif** (§ 6.2) |
| Affectation actuelle | Paroisse (et donc circuit et région) — modifiée uniquement par une mutation validée |
| Fonctions | Mandats en cours et passés (§ 8) |
| Catégorie | Membre actif, membre d'honneur ou membre sympathisant (RI art. 25 à 28) |
| Statut | Actif, Sanctionné, Exclu, Démissionnaire, Décédé (§ 6.3) |
| Historique | Changements de statut, de catégorie et de matricule, avec date, motif et référence |
| Sanctions | Sanctions inscrites par le BNC, en cours, terminées ou levées (§ 9.7) |
| Grade | Grade actuel et historique — **module 2** (§ 15) |
| Cotisations mensuelles | Suivies à part, hors de la fiche : état des cotisations et reçus — **module 2** (§ 16) |

Le reçu de consécration n'est pas enregistré sur la fiche : les cas de reçu perdu sont réglés hors du
site, lors de la centralisation des inscriptions.

### 6.2 Le matricule

**Format : `AAAA-RRAS-NNNN`** — exemple : **`2015-01AS-0157`**

| Partie | Signification |
|---|---|
| `AAAA` | Année d'intégration |
| `RR` | Code de la région d'intégration |
| `AS` | Lettres fixes : **Armée du Salut** |
| `NNNN` | Numéro d'ordre dans l'année et la région |

L'exemple se lit : membre intégré en **2015**, dans la région **01**, **157ᵉ** membre enregistré pour
cette année et cette région.

- Chaque couple (année, région) a son propre compteur, qui commence à 0001.
- Le numéro est attribué dans une **opération verrouillée** : deux enregistrements simultanés ne
  peuvent jamais recevoir le même matricule.
- Pour les membres intégrés les années passées, on saisit l'année réelle d'intégration ; le numéro
  d'ordre suit l'ordre d'enregistrement sur le site.
- Le matricule **ne change jamais**, ni après une mutation, ni après un changement de catégorie, ni
  après une sanction. Seule une correction exceptionnelle de l'année ou de la région d'intégration
  donne un nouveau matricule (§ 6.7).
- Le matricule sert d'**identifiant de connexion**.
- Capacité : 99 régions, 9 999 intégrations par région et par an.

### 6.3 Les statuts

| Statut | Accès au site | Comment il est attribué |
|---|---|---|
| **Actif** | Oui | Par défaut ; retour automatique à la fin d'une sanction temporaire ; réhabilitation |
| **Sanctionné** | **Oui** (espace personnel) | Suspension temporaire ou retrait temporaire de responsabilités inscrit par le BNC |
| **Exclu** | **Non** (compte désactivé) | Exclusion temporaire ou définitive inscrite par le BNC |
| **Démissionnaire** | **Non** (compte désactivé) | Démission signalée par la paroisse et confirmée par le BNC |
| **Décédé** | **Non** (compte désactivé) | Décès signalé par la paroisse et confirmé par le BNC |

La qualité de membre se perd par démission, exclusion ou décès (RI art. 167). La fiche est toujours
**conservée** et le matricule reste attribué à vie.

### 6.4 La photo d'identité

- Le **membre dépose lui-même** sa photo, en tenue de l'Armée du Salut, depuis son espace personnel.
- Le site vérifie le format (JPEG ou PNG), la taille et les dimensions minimales.
- **Seul le BNC valide** la photo : il l'accepte, ou la refuse avec un motif. Les bureaux de paroisse
  ne valident pas, pour éviter tout arrangement local.
- Tant qu'une nouvelle photo n'est pas acceptée, l'ancienne (ou un emplacement vide) reste affichée.
- Le BNC dispose d'une **file d'attente des photos à valider**.

### 6.5 Qui modifie quoi

| Informations | Qui peut les modifier |
|---|---|
| Téléphone, WhatsApp, e-mail, quartier, ville, profession, personne à contacter | Le membre lui-même, et le bureau de sa paroisse |
| Photo d'identité | Le membre (dépôt) ; validation par le BNC uniquement |
| Identité, NPI, photo du CIP | Le BNC uniquement |
| Année, paroisse et région d'intégration, matricule | Personne en temps normal ; correction exceptionnelle par le BNC (§ 6.7) |
| Affectation (paroisse actuelle) | Uniquement par une mutation validée (§ 9.3) |
| Statut et catégorie | Uniquement par les circuits de validation (§ 9) |

Toute modification est inscrite au journal, avec l'ancienne et la nouvelle valeur.

### 6.6 La catégorie

- Chaque membre a une **catégorie** : membre actif, membre d'honneur ou membre sympathisant
  (RI art. 25 à 28).
- La catégorie est **sans effet sur le matricule** : tout le monde reçoit un matricule, sans
  exception.
- À l'enregistrement, la catégorie est toujours demandée ; elle est pré-remplie sur « membre actif ».
- Le **changement de catégorie** est signalé par la paroisse, le circuit ou la région, puis validé par
  le BNC (§ 9.5).
- La catégorie sert de **filtre** dans les listes et de **critère** dans les statistiques.

### 6.7 La correction exceptionnelle

En cas d'erreur à l'enregistrement, le BNC peut corriger l'**année**, la **paroisse** ou la **région
d'intégration**, avec un **motif obligatoire** :

- si l'année ou la région change, un **nouveau matricule** est attribué ; le membre se connecte
  désormais avec ce nouveau matricule et en est **notifié** ; l'ancien matricule reste noté dans
  l'historique de la fiche ;
- si le membre n'a jamais été muté, son affectation d'intégration est corrigée en même temps ;
- la correction est inscrite au journal, avec les anciennes et nouvelles valeurs.

## 7. Le parcours

- Chaque **affectation** comprend la paroisse, ainsi que le **circuit et la région tels qu'ils
  étaient à cette date**, la date de début, la date de fin (vide pour l'affectation actuelle) et le
  motif (intégration, mutation n°…). Une réorganisation future du territoire ne réécrit donc pas le
  passé.
- Le parcours est **rempli automatiquement**, à l'intégration puis à chaque mutation validée.
  Personne ne le modifie à la main.
- Il est visible par le membre lui-même, par les bureaux de sa paroisse, de son circuit et de sa
  région actuels, et par le BNC. Il s'affiche sous forme de frise chronologique.

**Anciens membres.** Après une mutation, l'ancienne paroisse, l'ancien circuit et l'ancienne région
(s'ils changent) retrouvent le membre dans une liste « **Anciens membres** », en lecture seule, avec
seulement : nom, prénoms, matricule, dates de son passage chez eux et nouvelle affectation. Ni
coordonnées, ni suite du parcours.

## 8. Fonctions, mandats et bureaux

### 8.1 Les fonctions

Les fonctions sont celles du règlement intérieur (art. 14 à 18). Chacune a un niveau, une durée de
mandat et une mention « **droit de gérer le site** » :

| Niveau | Fonctions | Droit de gérer | Mandat |
|---|---|---|---|
| Unité paroissiale | Chef d'Unité paroissiale, Secrétaire paroissial, Trésorier paroissial | **Chef d'Unité paroissiale, Secrétaire paroissial** | 2 ans |
| Section de Circuit | Chef de Section de Circuit, Secrétaire de Circuit, Trésorier, Organisateur, Formateur de Circuit | **Chef de Section de Circuit, Secrétaire de Circuit** | 2 ans |
| Bureau Régional de Coordination | Coordinateur régional et adjoint, Secrétaire régional, Rapporteur, Trésorier, Organisateur et adjoint, Formateur, Conseiller régional | **Coordinateur régional, Secrétaire régional** | 2 ans |
| Bureau National de Commandement | Président, Vice-président, Secrétaire national et adjoint, Trésorier national et adjoint, Responsables nationaux (organisation, information, formation, relations extérieures), Conseillers (affaires spirituelles, juridique et disciplinaire) | **Président, Secrétaire national** | 4 ans |

- Les **vérificateurs** (RI art. 17) sont enregistrés comme fonction sans droit de gérer.
- Le BNC peut accorder le droit de gérer à d'autres fonctions **depuis le site**, sans intervention
  technique.

### 8.2 Les mandats

- Un **mandat** relie un membre, une fonction, une unité précise et des dates de début et de fin.
- La **date de fin prévue** est calculée d'après la durée de la fonction.
- Le site **prévient** le BNC et le bureau concerné **60 jours avant l'échéance**, puis quand un
  mandat est échu sans renouvellement. Il ne coupe jamais un mandat de lui-même : c'est l'installation
  du nouveau bureau par le BNC qui clôt les anciens mandats.
- Une même personne peut avoir **plusieurs mandats** à la fois, à tous les niveaux. Ses droits sont
  la somme des droits de ses mandats en cours.
- Seul un membre **Actif** exerce les droits de ses mandats.
- Les mandats d'un membre sont clos automatiquement en cas de décès, de démission ou d'exclusion, et
  dans les unités qu'il quitte lors d'une mutation.

### 8.3 Les comptes

- Chaque personne a **un seul compte, à son nom**. La connexion se fait par le matricule et un mot de
  passe personnel.
- Il n'existe **aucun code partagé** par bureau.
- À la fin d'un mandat, la personne redevient automatiquement membre simple et garde son espace
  personnel.

## 9. Circuits de travail

### 9.1 Enregistrement individuel (BNC)

1. Le BNC saisit la fiche : identité, contact, année, paroisse et région d'intégration, catégorie.
2. Le site **signale les doublons possibles** (même nom et même date de naissance, ou même NPI) ; le
   BNC décide de poursuivre ou non.
3. Le site attribue le **matricule**, crée le **compte** avec un mot de passe provisoire et ouvre
   l'affectation dans la paroisse d'intégration.
4. Il produit la **fiche d'identification PDF** (nom, matricule, paroisse, circuit, région,
   identifiants de connexion), à imprimer ou à transmettre par WhatsApp.
5. Les bureaux de la paroisse, du circuit et de la région sont **notifiés**.
6. À sa première connexion, le membre doit **choisir son propre mot de passe**.

### 9.2 Enregistrement par lots (fichier Excel)

1. Le site fournit un **modèle Excel officiel** par région : colonnes fixes, listes déroulantes
   (sexe, situation matrimoniale, paroisses de la région, catégorie) et consignes de saisie.
2. Chaque région remplit le modèle et l'envoie au Secrétaire national.
3. Le Secrétaire national **dépose le fichier** sur le site : un **lot** est créé.
4. **Écran de contrôle.** Le site lit le fichier **sans rien créer** et affiche chaque ligne telle
   qu'il l'a comprise, avec son état : correcte, doublon possible (avec lien vers la fiche existante)
   ou erreur (avec explication). Un résumé donne le nombre de lignes par état, par année et par
   paroisse. Le BNC peut corriger une ligne, l'écarter, trancher chaque doublon, enregistrer le lot
   en brouillon ou redéposer un fichier corrigé.
5. **Validation.** Le bouton « Valider et générer » n'est actif que lorsqu'il ne reste **ni erreur ni
   doublon non tranché**. Un récapitulatif demande une confirmation explicite.
6. Le site crée alors **en une seule fois** les matricules, les comptes, les affectations, un PDF de
   toutes les fiches d'identification, une liste récapitulative pour la région, et les
   notifications.
7. La validation est **tout ou rien** : en cas d'incident, aucun membre du lot n'est créé. Le lot et
   son fichier d'origine restent archivés.

### 9.3 Mutation

1. Le bureau de la **nouvelle paroisse** demande la mutation en saisissant le matricule du membre. Le
   site affiche seulement le nom et la paroisse actuelle, pour confirmation. Seul un membre Actif ou
   Sanctionné peut être muté.
2. L'ancienne paroisse, le circuit et la région de départ, ainsi que le BNC, sont notifiés.
3. Le **circuit de départ**, puis la **région de départ**, donnent chacun **un avis** (favorable ou
   défavorable, avec commentaire), qui ne se modifie pas.
4. Le **BNC valide ou refuse**, même si un avis manque.
5. Si la mutation est validée, automatiquement : l'ancienne affectation est close, la nouvelle est
   ouverte, le membre apparaît dans les « Anciens membres » des unités quittées, ses mandats dans ces
   unités sont clos, et tous les bureaux concernés ainsi que le membre sont notifiés.

Une seule mutation peut être en cours par membre. États : *En attente d'avis → En attente du BNC →
Validée / Refusée* (ou *Annulée* si le membre décède, démissionne ou est exclu entre-temps).

### 9.4 Décès et démission

1. Le bureau de la paroisse **signale** le décès ou la démission, avec la date (et, pour une
   démission, la référence de la lettre éventuelle).
2. Le **BNC confirme** ou refuse avec un motif.
3. À la confirmation : statut « Décédé » ou « Démissionnaire », compte désactivé, mandats clos,
   mutation en cours annulée, fiche conservée, bureaux notifiés.

### 9.5 Réhabilitation et changement de catégorie

**Réhabilitation** (RI art. 169 à 172) :

- possible pour un membre **démissionnaire ou exclu**, au plus tôt **6 mois** après la démission ou
  l'exclusion : le site affiche la date à partir de laquelle la demande devient possible ;
- demandée par la paroisse ; les conditions (redevances, amendes, cotisations, souscriptions) sont
  vérifiées **hors du site** ;
- pour un membre exclu, la référence de l'**engagement écrit de bonne conduite** est obligatoire ;
- un membre **déjà réhabilité après une exclusion, puis exclu à nouveau**, ne peut plus être
  réhabilité : le site le signale et bloque la demande ;
- à la validation par le BNC : statut « Actif », compte réactivé avec un **nouveau mot de passe
  provisoire**, **même matricule** ; le BNC télécharge directement la nouvelle fiche
  d'identification.

**Changement de catégorie** : signalé par la paroisse, le circuit ou la région, validé par le BNC ;
la fiche, l'historique et le journal sont mis à jour et le membre est notifié.

### 9.6 Revérification et décisions simultanées

Au moment où le BNC décide, le site **revérifie la situation** (statut, affectation, délais). Si elle
a changé depuis la demande, il refuse avec une explication et ne modifie rien. Deux décisions prises
en même temps sur le même membre sont traitées l'une après l'autre ; une demande déjà traitée ne
peut pas l'être une seconde fois.

### 9.7 Sanctions

**Seul le BNC inscrit une sanction sur le site.** Les procédures des autres niveaux (séances,
commissions disciplinaires, décisions locales) se déroulent hors du site et n'y ont aucun effet.

Une sanction comprend : le **degré de la faute** (1ᵉʳ, 2ᵉ ou 3ᵉ degré, RI art. 152), le **type**, la
date de début, la date de fin éventuelle, un motif résumé et la **référence de la décision**.

| Type de sanction (RI art. 154, 156, 162) | Effet sur le statut |
|---|---|
| Avertissement verbal, avertissement écrit, amende, blâme écrit, autre (à préciser) | Aucun : inscription dans l'historique |
| Suspension temporaire de service (**15 jours au plus**) | **Sanctionné** jusqu'à la date de fin |
| Retrait temporaire de responsabilités | **Sanctionné** jusqu'à la date de fin |
| Exclusion temporaire | **Exclu** jusqu'à la date de fin |
| Exclusion définitive | **Exclu**, sans date de fin |

- Le retour à « Actif » est **automatique** à la date de fin, sauf si une autre sanction en cours
  justifie encore le statut (le statut le plus grave l'emporte).
- Une exclusion désactive le compte, clôt les mandats et annule la mutation en cours.
- Une sanction **ne se supprime jamais**. En cas d'erreur, le BNC la **lève**, avec un motif.
- Les bureaux de la paroisse, du circuit et de la région, ainsi que le membre, sont notifiés.
- Les sanctions sont visibles par le membre concerné, par ses bureaux et par le BNC.

### 9.8 Changement de bureau

1. Le BNC enregistre le nouveau bureau d'une unité : pour chaque fonction, le titulaire et la date de
   début.
2. À cette date, les anciens mandats sont clos (les anciens responsables perdent l'accès à l'espace
   du bureau) et les nouveaux sont ouverts.
3. Anciens et nouveaux responsables sont notifiés.

### 9.9 Mot de passe oublié

- Le membre s'adresse au **bureau de sa paroisse**. Le Chef d'Unité paroissiale ou le Secrétaire
  paroissial imprime une nouvelle fiche avec un **mot de passe provisoire**, à changer à la connexion
  suivante. Le BNC peut aussi le faire.
- Le compte d'un membre du BNC ne peut être réinitialisé que par un autre membre du BNC, ou par le
  mainteneur selon la procédure du guide de maintenance.
- Chaque réinitialisation est inscrite au journal.

## 10. Listes et statistiques en temps réel

### 10.1 Listes

Chaque bureau peut, **à tout moment**, établir la liste des membres de son périmètre :

- **Filtres combinables** : statut (Actif par défaut), sexe, catégorie, paroisse, circuit, région
  (BNC), année d'intégration, fonction en cours, âge, grade et situation des cotisations (module 2).
- **Âge**, calculé au jour près à partir de la date de naissance : « moins de X ans », « plus de Y
  ans », « entre X et Y ans » (bornes incluses), ou « âge non renseigné ». « Plus de 40 ans » commence
  à 41 ans : les tranches ne se chevauchent pas.
- **Colonnes au choix** : matricule, nom, prénoms, sexe, âge, téléphone, WhatsApp, paroisse, circuit,
  catégorie, statut, fonctions, grade, cotisations (module 2).
- **Formats** : affichage à l'écran, **PDF** avec en-tête officiel, filtres utilisés, date et heure ;
  **Excel**.
- Le NPI et la photo du CIP n'apparaissent **jamais** dans une liste.
- Chaque téléchargement est inscrit au journal.

### 10.2 Statistiques

Chaque bureau dispose d'une page « Statistiques » limitée à son périmètre, toujours à jour :

- total ; répartition par sexe, par tranche d'âge (avec « âge non renseigné »), par catégorie, par
  statut, par grade et par situation des cotisations (module 2) ;
- répartition par unité inférieure : par région pour le BNC, par circuit pour une région, par
  paroisse pour un circuit ;
- les membres actifs sont comptés par défaut ; les autres statuts peuvent être ajoutés ;
- **chaque chiffre est cliquable** et ouvre la liste correspondante, exportable : le chiffre et le
  nombre de lignes de la liste sont toujours égaux ;
- tranches d'âge par défaut : moins de 18 ans, 18 à 40 ans, plus de 40 ans ; le BNC peut les
  **modifier depuis le site** ;
- export de la page en PDF, inscrit au journal.

## 11. Espaces du site

| Espace | Pour qui | Contenu |
|---|---|---|
| **Espace membre** | Tout membre connecté | Sa fiche, son parcours, ses fonctions, son historique, ses sanctions éventuelles, sa fiche PDF, le dépôt de sa photo, ses coordonnées, son mot de passe, ses notifications |
| **Espace bureau** | Titulaires d'un mandat de gestion (paroisse, circuit, région) | Membres du périmètre, anciens membres, demandes (mutations, signalements), listes, statistiques, réinitialisation des mots de passe (paroisse) |
| **Espace Bureau National** | Titulaires d'un mandat national de gestion | Tout ce qui précède pour tout le pays, et : enregistrement individuel et par lots, validation des photos, décisions à prendre, sanctions, corrections exceptionnelles, installation des bureaux et gestion des fonctions, tranches d'âge, journal |

Une personne qui a plusieurs mandats passe d'un espace à l'autre depuis l'accueil.

## 12. Sécurité et droits d'accès

### 12.1 Matrice des droits

| Action | Membre | Paroisse | Circuit | Région | BNC |
|---|---|---|---|---|---|
| Voir sa propre fiche | ✅ | ✅ | ✅ | ✅ | ✅ |
| Voir les fiches de son périmètre | ❌ | Sa paroisse | Son circuit | Sa région | Tous |
| Voir les anciens membres (lecture limitée) | ❌ | ✅ | ✅ | ✅ | ✅ |
| Voir les sanctions | La sienne | ✅ | ✅ | ✅ | ✅ |
| Voir la photo du CIP | ❌ | ❌ | ❌ | ❌ | ✅ |
| Listes et statistiques | ❌ | ✅ | ✅ | ✅ | ✅ |
| Demander une mutation | ❌ | ✅ (arrivée) | ❌ | ❌ | ✅ |
| Donner un avis de mutation | ❌ | ❌ | ✅ (départ) | ✅ (départ) | — |
| Signaler un décès ou une démission ; demander une réhabilitation | ❌ | ✅ | ❌ | ❌ | ✅ |
| Signaler un changement de catégorie | ❌ | ✅ | ✅ | ✅ | ✅ |
| Valider mutations, décès, démissions, réhabilitations, catégories | ❌ | ❌ | ❌ | ❌ | ✅ |
| Inscrire ou lever une sanction | ❌ | ❌ | ❌ | ❌ | ✅ |
| Valider une photo | ❌ | ❌ | ❌ | ❌ | ✅ |
| Enregistrer des membres (individuel, lot) | ❌ | ❌ | ❌ | ❌ | ✅ |
| Gérer bureaux, fonctions, territoire | ❌ | ❌ | ❌ | ❌ | ✅ |
| Réinitialiser un mot de passe | ❌ | Ses membres | ❌ | ❌ | ✅ |
| Consulter le journal | ❌ | ❌ | ❌ | ❌ | ✅ |
| Voir le grade et les cotisations | Les siens | Sa paroisse | Son circuit | Sa région | Tous |
| Enregistrer un versement de cotisation | ❌ | ✅ | ❌ | ❌ | ❌ |
| Valider ou refuser un versement de cotisation | ❌ | ❌ | ✅ | ❌ | ❌ |
| Marquer sa part de cotisations comme reçue | ❌ | ❌ | ❌ | ✅ | ✅ |
| Attribuer ou corriger un grade | ❌ | ❌ | ❌ | ❌ | ✅ |
| Fixer le montant, le mois de départ et les pourcentages des cotisations | ❌ | ❌ | ❌ | ❌ | ✅ |

### 12.2 Le gardien des périmètres

Un **composant central unique** décide, pour chaque page et chaque action, ce que la personne
connectée a le droit de voir, en fonction de ses mandats en cours. Toutes les listes sont filtrées
à la source, dans la base de données, et jamais seulement à l'affichage. Une adresse modifiée à la
main pour atteindre un membre hors du périmètre aboutit à une page introuvable.

### 12.3 Comptes et connexion

- Mots de passe **chiffrés de manière irréversible**, de 8 caractères au moins ; les mots de passe
  trop simples (dont le matricule) sont refusés.
- **Blocage temporaire** après 5 échecs de connexion.
- **Déconnexion automatique** après inactivité, plus rapide pour les comptes de bureau (30 minutes).
- **Double vérification obligatoire** pour les comptes ayant les pouvoirs du BNC : à chaque connexion,
  un code à 6 chiffres est demandé, fourni par une application d'authentification (Google
  Authenticator, Microsoft Authenticator…) enregistrée une fois par QR code. Un code ne sert qu'une
  fois ; après 5 codes faux, la session est fermée et le compte bloqué 15 minutes. En cas de perte du
  téléphone, le mainteneur réinitialise la double vérification, après vérification de l'identité de
  la personne.
- **HTTPS** partout.

### 12.4 Le journal

Le journal est **non modifiable et non effaçable**, y compris par l'administration technique : la
base de données elle-même refuse toute modification. Il enregistre notamment :

- les connexions, réussies et échouées ;
- les consultations de fiches ;
- les modifications de coordonnées (ancienne et nouvelle valeur) ;
- les enregistrements, les lots, les installations de bureau ;
- les listes et statistiques téléchargées ;
- les mutations, signalements et décisions ;
- les sanctions et leurs levées ;
- les corrections exceptionnelles ;
- les réinitialisations de mot de passe et de double vérification ;
- les décisions sur les photos.

Le BNC le consulte depuis son espace, avec des filtres par action, auteur, texte et dates.

### 12.5 Données et sauvegardes

- La photo du CIP et les photos d'identité sont stockées dans un **espace privé** et ne sont
  transmises qu'après contrôle des droits.
- **Sauvegardes** : quotidienne automatique chez l'hébergeur ; **sauvegarde complète chiffrée** par le
  mainteneur, au moins une fois par mois et avant toute grosse mise à jour, copiée sur deux supports
  (clé USB, disque dur) rangés à deux endroits différents ; test de restauration chaque trimestre.
- Alertes de sécurité automatiques sur les composants utilisés.

### 12.6 Protection des données personnelles (APDP)

- Une page « **Protection de vos données** » explique ce qui est collecté, pourquoi, qui y a accès et
  combien de temps les données sont conservées.
- Chaque membre voit toutes ses données et peut demander une correction.
- Un document de synthèse est préparé pour la **déclaration auprès de l'Autorité de Protection des
  Données Personnelles (APDP)**. Si les données sont hébergées hors du Bénin, ce **transfert** est
  déclaré et autorisé conformément au Code du numérique (loi n° 2017-20).
- **La mise en ligne réelle n'a lieu qu'après cette déclaration.** D'ici là, le site d'essai ne
  contient que des **données fictives**.

## 13. Notifications

- Notifications **internes au site** (cloche et liste), avec lien vers l'élément concerné et état lu /
  non lu ; envoi par **e-mail** lorsque le destinataire a une adresse.
- Événements notifiés :
  - nouveau membre dans le périmètre ;
  - demande, avis, décision ou annulation d'une mutation ;
  - signalement et décision (décès, démission, réhabilitation, catégorie) ;
  - sanction inscrite, levée ou terminée ;
  - début et fin de mandat, échéance prochaine ;
  - photo acceptée ou refusée ;
  - lot validé ;
  - réinitialisation de mot de passe ;
  - changement de matricule.
  - attribution, promotion ou correction d'un grade (module 2) ;
  - versement de cotisation enregistré, validé, refusé ou annulé ; part marquée comme reçue (module 2).
- SMS et WhatsApp : étudiés au module 4, selon leur coût.

## 14. Interface

- Conçue **d'abord pour le téléphone**, utilisable sur ordinateur.
- Pages légères, adaptées à une connexion mobile faible.
- Design sobre et professionnel, aux couleurs du mouvement (**bleu marine, jaune or, rouge**) et avec
  ses logos (Armée du Salut ; Congrégation).
- Fiches et listes PDF avec **en-tête officiel**, date et heure de génération.
- Le site pourra être ajouté à l'écran d'accueil du téléphone comme une application.

---

# Partie III — Les modules suivants

Le **module 2** (grades et cotisations mensuelles) est décrit ci-dessous en détail : il sera réalisé
dès sa validation. Les modules 3 à 5 feront chacun l'objet d'un cahier des charges détaillé avant leur
réalisation ; les éléments ci-dessous en fixent dès maintenant le contenu attendu.

## 15. Module 2 — Les grades

### 15.1 Les douze grades

Tout nouveau membre porte d'abord l'appellation de **Camarade** (décision du BNC du 12 novembre 2026).
Il devient **Soldat de 3ᵉ classe** à sa première consécration (art. 80). Viennent ensuite les douze
grades du règlement intérieur (chapitre X, art. 77 et 86), du moins élevé au plus élevé :

| N° | Grade | Épaulettes / attributs | Corde | Accès |
|---:|---|---|---|---|
| 1 | Soldat de 3ᵉ classe | 2 barrettes | Blanche | Première consécration (art. 80) |
| 2 | Soldat de 2ᵉ classe | 3 barrettes | Verte | Test, après 3 ans |
| 3 | Soldat de 1ʳᵉ classe | 1 étoile | Chocolat | Test, après 3 ans |
| 4 | Sous-Capitaine | 2 étoiles | Bleue | Test, après 3 ans |
| 5 | Capitaine | 3 étoiles | Jaune | Test, après 4 ans |
| 6 | Senior Capitaine | 3 étoiles, 3 croix, 1 épée | Bleue et jaune | Test, après 5 ans |
| 7 | Commandant | 4 étoiles, 1 croix, 1 épée | Jaune | Nomination |
| 8 | Sous-Supérieur | 4 étoiles, 3 croix, 1 épée | Multicolore | Nomination |
| 9 | Supérieur Délégué | 4 étoiles, Saint-Michel | Multicolore | Nomination |
| 10 | Supérieur Général Délégué | Moïse, 1 épée | Multicolore | Nomination |
| 11 | Supérieur Général | Jésus, Moïse, 1 épée | Multicolore | Nomination |
| 12 | Supérieur Suprême Spirituel | Jésus, Moïse, couronne | Multicolore | Nomination |

Les durées sont des **minimums** (art. 78) : l'ancienneté seule ne donne pas droit au grade. Le BNC
peut accorder une **promotion exceptionnelle** (art. 84). La correspondance avec les grades de l'Église
(art. 81) est un niveau de référence, **jamais une attribution automatique**. La qualité de membre
d'honneur n'est pas un grade (art. 87).

### 15.2 Sur la fiche du membre

- **Grade actuel**, affiché sur la fiche, dans l'espace du membre et sur la **fiche PDF**.
- **Le grade précède toujours le nom**, dans l'ordre **grade, prénoms, NOM** : par exemple
  « **Capitaine Marc Aurel KOUDAKPO** ». C'est ainsi que le membre est nommé partout sur le site : fiche,
  fiche PDF, accueil (« Bienvenue, Capitaine Marc Aurel KOUDAKPO »), menu, listes, notifications,
  décisions. Les **fonctions** suivent, à leur place habituelle, une par ligne (par exemple
  « Secrétaire national — Bureau national »).
- **Historique des grades** : grade, date d'effet, mode d'accès (première consécration, test,
  nomination, promotion exceptionnelle, régularisation), référence de la décision du BNC.
- Le membre voit son propre grade et son historique ; un bureau voit ceux des membres de son
  périmètre ; un membre simple ne voit jamais le grade d'un autre membre.

### 15.3 Qui enregistre les grades

- **Le BNC seul** attribue un grade (art. 76 : le BNC arrête et publie les décisions d'avancement).
- **À l'enregistrement** d'un nouveau membre : **Camarade** par défaut. Le BNC enregistre ensuite sa
  première consécration (Soldat de 3ᵉ classe), seule ou en série pour toute une consécration. Pour les membres déjà
  gradés (**régularisation**, art. 83), le BNC choisit le grade et sa date, sur le formulaire individuel
  ou dans une **colonne « Grade »** du fichier Excel des lots.
- **Promotion** : sur la fiche d'un membre, ou **en série** après la proclamation des résultats d'un
  test (cocher les promus dans une liste, indiquer la date et la référence de la décision).
- Le site **refuse** une promotion qui ne respecte pas la durée minimale de l'article 78, sauf si le
  BNC la déclare **promotion exceptionnelle** (art. 84), avec un motif.
- Un grade ne s'efface pas : une erreur se corrige par une **correction** du BNC, avec motif, qui reste
  dans l'historique.
- Chaque attribution, promotion ou correction est **inscrite au journal** et **notifiée** au membre et
  au bureau de sa paroisse.

### 15.4 Listes

- Nouvelle colonne **Grade** et nouveau filtre **Grade** : un ou plusieurs grades, ou « à partir de »
  un grade (par exemple : à partir de Capitaine).
- Le filtre grade se **combine** avec tous les autres : âge, sexe, statut, catégorie, région, circuit,
  paroisse, fonction, année d'intégration. Exemples :
  - les Capitaines de plus de 40 ans de la région de Cotonou ;
  - les Senior Capitaines de moins de 50 ans du circuit de Davo ;
  - les Soldats de 3ᵉ classe intégrés en 2024 dans une paroisse donnée.
- Exports PDF et Excel, comme les autres listes.

### 15.5 Statistiques

- **Répartition par grade** (Camarade, les douze grades, « grade non renseigné »), dans le périmètre du
  bureau : par exemple le nombre de Capitaines, de Senior Capitaines, de Soldats de 3ᵉ classe.
- **Tableau croisé grade × tranche d'âge** et **grade × sexe**.
- **Tableau croisé grade × unité inférieure** : par région pour le BNC, par circuit pour une région, par
  paroisse pour un circuit.
- Ces tableaux suivent les filtres de la page : on peut, par exemple, n'afficher que les membres d'une
  région ou d'une tranche d'âge.
- Comme partout, **chaque chiffre ouvre la liste correspondante** (mêmes filtres) : le chiffre et le
  nombre de lignes de la liste sont toujours égaux.

### 15.6 Éligibilité

- Liste des **membres éligibles** au grade suivant : grade actuel, ancienneté dans ce grade, durée
  minimale atteinte (art. 78), statut Actif. Les **Camarades** y figurent tous : c'est la liste de la
  prochaine consécration (le règlement ne fixe pas de durée avant la première consécration).
- Filtrable et exportable comme les autres listes ; sert à préparer les tests organisés par le BNC dans
  les régions (art. 75).
- Les autres conditions (tenue, assiduité, cotisations, conduite, art. 73) restent appréciées par les
  bureaux ; la **situation des cotisations** (§ 16) est affichée à côté de chaque nom pour aider.

### 15.7 Site d'essai

Les membres fictifs du site d'essai sont **recréés avec des grades de toutes sortes**, répartis de
façon vraisemblable selon l'âge et l'ancienneté (beaucoup de Soldats, moins de Capitaines, quelques
Commandants et Supérieurs), avec leur historique de grades, afin d'essayer listes et statistiques
croisées.

### 15.8 Décisions (11 novembre 2026)

0. **Grade par défaut : Camarade** (et non Soldat de 3ᵉ classe), jusqu'à la première consécration
   (décision du 12 novembre 2026).
1. **Les membres déjà gradés sont enregistrés directement avec leur grade** (régularisation,
   art. 83), sur le formulaire individuel comme dans le fichier Excel des lots.
2. **La tenue n'est pas suivie** sur le site.
3. **Sanction et grade : on applique le règlement intérieur.** Les sanctions qu'il prévoit
   (art. 154 à 157 : avertissements, amende, blâme, suspension, retrait de responsabilités,
   exclusion) **ne comportent pas de rétrogradation** : une sanction ne change donc pas le grade. Si
   le règlement intérieur venait à prévoir une rétrogradation, le site serait adapté.

## 16. Module 2 — Les cotisations mensuelles (CM)

### 16.1 Le principe

Le règlement intérieur oblige tout membre à s'acquitter régulièrement de ses cotisations mensuelles
(art. 10 f). À ce jour, la cotisation est de **100 F CFA par mois**, soit **1 200 F CFA par an**.

Le site retrace, **pour chaque membre et pour chaque mois**, si la cotisation est payée ou non, **à
compter du mois de mise en service du site**. Il n'enregistre pas l'argent lui-même : il enregistre les
**versements déclarés** par le bureau qui les reçoit.

### 16.2 Réglages (BNC)

- **Montant mensuel** : 100 F CFA, modifiable par le BNC avec une **date d'effet** ; les mois déjà
  passés gardent leur ancien montant.
- **Mois de départ** : le premier mois suivi par le site (mois de la mise en service réelle). Avant ce
  mois, rien n'est dû sur le site.
- Toute modification est inscrite au journal.

### 16.3 Ce qui est dû

- Un membre doit la cotisation de chaque mois **à partir du mois de départ**, ou de son mois
  d'enregistrement s'il est arrivé plus tard, **jusqu'au mois en cours**.
- La cotisation concerne **tous les membres** : membres actifs, d'honneur et sympathisants, membres
  sanctionnés pendant leur sanction, et mineurs. Toute exception future sera décidée par le BNC et
  ajoutée au site.
- Rien n'est dû pour les mois pendant lesquels la personne n'est plus membre (**exclue,
  démissionnaire ou décédée**).
- Un membre est **à jour** quand tous les mois dus jusqu'au mois en cours sont payés. Sinon, il est
  **en retard** de N mois, soit N × 100 F CFA.
- Un membre peut **payer d'avance** les mois suivants de l'année.

### 16.4 Enregistrer un versement

- C'est le **bureau de la paroisse** du membre qui enregistre les versements (titulaire d'une fonction
  avec droit de gérer, en principe le Trésorier paroissial).
- Chaque versement saisi par la paroisse est ensuite **validé par le bureau du circuit**. Tant qu'il
  n'est pas validé, il apparaît « **en attente de validation** » et le mois n'est pas encore compté
  comme payé. Le circuit peut aussi **refuser** un versement, avec un motif ; la paroisse est alors
  notifiée.
- Le bureau saisit : le membre, le **montant versé** et la **date** ; le site range automatiquement le
  montant sur les **mois non payés les plus anciens** (200 F = deux mois). Il peut aussi cocher
  directement les mois payés.
- **Saisie rapide pour toute la paroisse** : une grille des membres et des mois de l'année, où l'on
  coche les mois payés lors de la collecte.
- Un versement ne se supprime pas : une erreur s'**annule** (avec motif), et l'annulation reste visible.
  Versements, validations, refus et annulations sont inscrits au journal.

### 16.4 bis Répartition entre le circuit, la région et le national

- À la validation par le circuit, le site calcule la **part de chaque niveau** : la part du **circuit**,
  celle de la **région** et celle du **national**, selon des **pourcentages fixés par le BNC** (avec
  date d'effet).
- Chaque bureau voit, pour son périmètre et pour chaque mois, le **montant validé** et **sa part**.
- La **région** puis le **national** marquent la part qui leur revient comme **reçue** lorsqu'ils la
  perçoivent ; le site affiche ainsi, à chaque niveau, les parts **reçues** et **en attente**.

### 16.5 Ce que chacun voit

| Qui | Ce qu'il voit |
|---|---|
| **Membre** | **Ses seules** cotisations : mois payés de l'année, total versé, à jour ou non. Jamais celles d'un autre membre. |
| **Bureau de paroisse** | Les cotisations de chaque membre de sa paroisse, mois par mois ; la grille de saisie ; les versements en attente de validation. |
| **Bureau de circuit** | Les cotisations des membres de son circuit ; la **validation** des versements de ses paroisses ; sa part ; listes et statistiques. |
| **Bureau de région** | Les cotisations des membres de sa région, en lecture ; sa part (reçue ou en attente) ; listes et statistiques. |
| **BNC** | Tout le pays ; sa part ; réglages (montant, mois de départ, pourcentages) ; corrections. |

### 16.6 Tableau de bord, listes et statistiques

- **Tableau de bord** de chaque bureau : pour l'année et le mois en cours, nombre de membres **à jour**
  et **en retard**, montant validé, montant **en attente de validation**, montant restant dû, et
  **part du niveau** (reçue ou en attente) ; pour le circuit, les versements **à valider**.
- **Cotisations d'un membre** (écran à part, hors de la fiche) : grille des 12 mois de l'année (payé /
  en attente / non payé / non dû), total de l'année et depuis le début, en F CFA.
- **Listes** : nouveaux filtres « à jour », « en retard », « en retard d'au moins N mois », combinables
  avec tous les autres (grade, âge, unité…) ; colonnes « mois payés », « total versé », « reste dû ».
- **Statistiques** : membres à jour / en retard, montants versés et restant dus, par unité inférieure,
  par grade, par tranche d'âge ; chaque chiffre ouvre la liste correspondante.
- Exports PDF et Excel, inscrits au journal.

### 16.7 Documents PDF : état des cotisations et reçu

Les cotisations **ne figurent pas sur la fiche du membre** : elles font l'objet de documents à part.

- **« État des cotisations mensuelles »** d'un membre, avec l'en-tête officiel : grade, prénoms, NOM et
  matricule ; grille des 12 mois de l'année (payé, en attente de validation, non payé, non dû) ;
  **total versé en F CFA** (année en cours et depuis le mois de départ) ; mention **« À jour au [mois
  en cours] »** ou **« En retard de N mois (X F CFA) »**. Il peut être produit par le bureau de la
  paroisse, du circuit, de la région ou par le BNC, et par le membre pour lui-même.
- **Reçu de versement** : un petit document PDF par versement, produit une fois le versement validé
  par le circuit : numéro de reçu, date, membre (grade, prénoms, NOM, matricule), montant, mois
  couverts, paroisse qui a encaissé, validation du circuit.
- **État des cotisations d'une unité** (paroisse, circuit, région, pays) : liste des membres avec mois
  payés, total versé et reste dû, en PDF et en Excel.

### 16.8 Site d'essai

Les membres fictifs reçoivent des **cotisations fictives** variées (à jour, en retard d'un mois, de
plusieurs mois, payées d'avance) pour essayer le tableau de bord, les listes et les statistiques.

### 16.9 Décisions (11 novembre 2026) et points restant à confirmer

Décisions :

1. La cotisation concerne **tous les membres** (actifs, d'honneur, sympathisants, sanctionnés,
   mineurs) ; toute modification sera ajoutée plus tard.
2. La **paroisse** saisit les versements ; le **circuit** les valide ; le circuit, la région et le
   national perçoivent chacun leur **pourcentage**.
3. Un **reçu PDF** est produit pour chaque versement, et un document **« État des cotisations
   mensuelles »** à part ; rien sur la fiche du membre.

Restent à confirmer par le BNC :

1. Les **pourcentages** du circuit, de la région et du national sur les 100 F, et ce que garde la
   paroisse (le cas échéant).
2. Le reçu est-il remis **dès la saisie** par la paroisse, ou **seulement après la validation** du
   circuit ? (Proposé : après la validation.)
3. Un **délai** de validation par le circuit (par exemple 30 jours), avec rappel automatique ?

Ces données nouvelles (grade, versements) seront ajoutées à la page « Protection de vos données » et
au dossier APDP.

## 17. Module 3 — Événements et présences

- Création des activités (cultes, rassemblements, formations, tests de grade, pèlerinages) par les
  bureaux, selon leur périmètre.
- **Invitations et convocations ciblées**, à partir des filtres des listes (par exemple : tous les
  Secrétaires paroissiaux d'une région).
- Enregistrement des **présences** et historique de participation de chaque membre, consultable sur
  sa fiche.
- Statistiques de participation par unité.
- **Tests de grade** : inscription des candidats éligibles (§ 15.6) et saisie des résultats.

## 18. Module 4 — Communication

- **Messages officiels** du BNC aux membres, par périmètre.
- **Espace documents commun** : circulaires, modèles, comptes rendus.
- **Règlement intérieur en ligne**, consultable par tous les membres.
- Étude de l'envoi de **SMS et de messages WhatsApp**, selon les coûts.

## 19. Module 5 — Médias

- Photos et vidéos des activités, rattachées aux événements du module 3.
- Vidéos publiées sur la chaîne YouTube de l'Église et intégrées au site, pour des raisons de coût et
  de qualité sur le réseau mobile.

---

# Partie IV — Réalisation et exploitation

## 20. Choix techniques

| Élément | Choix | Raison |
|---|---|---|
| Type de site | Site sur mesure | Les règles propres au mouvement (matricule, mutations, périmètres, sanctions) ne peuvent pas être respectées proprement avec un outil générique. |
| Langage | **Python, avec Django** | Langage connu du mainteneur ; administration et sécurité intégrées. |
| Base de données | **PostgreSQL** | Fiable ; verrouillage nécessaire aux compteurs de matricule et aux décisions simultanées. |
| Affichage | Pages préparées par le serveur | Léger pour les téléphones et les connexions faibles. |
| Documents | PDF officiels et fichiers Excel produits par le site | Impression et partage par WhatsApp. |
| Code source | Dépôt GitHub `siteArm` | Historique complet, tests automatiques, retour en arrière possible. |
| Nom de domaine | **.bj** | Choix de l'Église. |

## 21. Hébergement

Un comparatif chiffré a été établi le 11 novembre 2026 (document séparé). Il porte sur trois
hébergeurs gérés français (Scalingo, Clever Cloud, alwaysdata) et sur un serveur à administrer
soi-même.

- **Recommandation** : **alwaysdata**, pack 10 Go, pour environ **69 000 FCFA par an**, domaine et site
  d'essai compris. Données en France, sauvegardes et tâches quotidiennes incluses, sécurité du
  système assurée par l'hébergeur.
- **Solution de rechange** : Scalingo, pour environ 298 000 FCFA par an, plus automatisée.
- Un **site d'essai** gratuit fonctionne déjà chez alwaysdata (`armeedusalut.alwaysdata.net`), avec
  des données fictives, pour que le Bureau et les responsables essaient le site avant la décision.
- Points à vérifier avant la commande : prix du jour, TVA applicable à une association établie au
  Bénin, moyen de paiement, nom de domaine `.bj` et son titulaire (l'Église), déclaration du transfert
  des données à l'APDP.

## 22. Qualité

### 22.1 Tests automatiques

Chaque fonctionnalité est accompagnée de **tests automatiques écrits avant le code**. Ils vérifient en
particulier :

- le format et l'unicité du matricule, y compris en cas d'enregistrements simultanés ;
- toutes les lignes de la matrice des droits ;
- les mutations, les signalements, les réhabilitations et leurs règles de délai ;
- les sanctions et leur fin automatique ;
- l'enregistrement par lots, avec le principe du tout ou rien ;
- les listes et statistiques : âge au jour près, chiffres égaux aux listes ;
- le journal immuable et la double vérification.

À ce jour, près de 500 tests sont exécutés automatiquement à chaque modification, sur la même base
de données que le site réel.

### 22.2 Parcours d'une modification

Toute modification passe par les mêmes étapes :

1. Les tests automatiques s'exécutent ; tout échec bloque la suite.
2. Une relecture indépendante est faite.
3. **L'accord du mainteneur** est donné.
4. La modification est essayée sur le **site d'essai**.
5. Elle est mise en ligne sur le **site réel**.

### 22.3 Surveillance

Alerte par e-mail si le site est inaccessible ; rapport détaillé des erreurs.

## 23. Documentation et maintenance

- **Guide de maintenance** : installation, mise à jour, sauvegarde et restauration, ajout d'une
  région, réinitialisation d'un compte ou d'une double vérification, tâches quotidiennes.
- **Guide d'installation du site d'essai** chez alwaysdata, pas à pas.
- **Guides pour les bureaux**, avec captures d'écran (enregistrement par lots, listes, mutations).
- **Fichier de contexte** permettant à tout assistant technique de reprendre le projet.
- **Récapitulatif du projet** : tout ce qui est fait, où se trouve chaque chose, ce qui reste à faire.
- **Sauvegarde complète et chiffrée** (code, données, photos, réglages) à copier sur une clé USB ou un
  disque dur, avec procédure de restauration sur un autre ordinateur ou un autre hébergement.
- Tâche quotidienne automatique : avertissement des échéances de mandats, début et fin des
  sanctions.

## 24. Calendrier du module 1

| Étape | Contenu | État |
|---|---|---|
| 1 | Organisation territoriale, comptes, connexion | Réalisée |
| 2 | Fiche membre, matricule, fiche PDF, photo d'identité | Réalisée |
| 3 | Fonctions, mandats, bureaux, gardien des périmètres, espaces | Réalisée |
| 4 | Enregistrement par lots (Excel) | Réalisée |
| 5 | Listes et statistiques en temps réel | Réalisée |
| 6 | Mutations, décès, démissions, réhabilitations, catégories | Réalisée |
| 7 | Sanctions, journal, double vérification, correction exceptionnelle | Réalisée |
| 8 | Mise en ligne : hébergement, site d'essai, déclaration APDP, site réel | **En cours** (site d'essai en ligne) |

Le **module 2** (grades, puis cotisations mensuelles) est réalisé ensuite, en deux étapes, et essayé
sur le site d'essai avec de nouveaux membres fictifs dotés de grades et de cotisations ; il peut être
mis en ligne en même temps que le module 1.

## 25. Éléments attendus de l'Église

| Élément | Pour | État |
|---|---|---|
| Liste des régions, circuits et paroisses | Territoire | Version provisoire reçue ; définitive après le 25 décembre 2026 |
| Fonctions des bureaux, statuts, sanctions, grades | Modules 1 et 2 | Reçus (règlement intérieur, projet) |
| Logos et couleurs | Interface | Reçus (logo de la Congrégation provisoire) |
| Caractéristiques de la photo en tenue (cadrage, fond) | Photo d'identité | **À fournir** |
| Choix de l'hébergeur et du nom de domaine `.bj` | Mise en ligne | **À décider** après les essais |
| Informations pour la déclaration APDP (responsable du traitement, contact) | Mise en ligne | **À fournir** |
| Retours des essais sur le site d'essai | Mise en ligne | En cours |
| Réponses aux points à confirmer des grades et des cotisations (§ 15.8 et 16.9) | Module 2 | Reçues le 11 novembre 2026 ; restent les **pourcentages** de répartition (§ 16.9) |

---

# Annexes

## Annexe A — Lexique

| Terme | Définition |
|---|---|
| **BNC** | Bureau National de Commandement de l'Armée du Salut. |
| **BRC** | Bureau Régional de Coordination. |
| **Unité paroissiale** | Le bureau de l'Armée du Salut au niveau d'une paroisse. |
| **Matricule** | Identifiant définitif d'un membre, au format `AAAA-RRAS-NNNN`. |
| **Affectation** | Rattachement d'un membre à une paroisse pendant une période. |
| **Mandat** | Exercice d'une fonction dans une unité, entre deux dates. |
| **Droit de gérer** | Mention d'une fonction qui donne accès à l'espace bureau de son unité. |
| **Périmètre** | Ensemble des membres qu'un bureau peut voir : sa paroisse, son circuit, sa région, ou tout le pays. |
| **Lot** | Ensemble de membres enregistrés à partir d'un fichier Excel déposé par le BNC. |
| **Signalement** | Demande transmise au BNC : décès, démission, réhabilitation ou changement de catégorie. |
| **Double vérification** | Code à 6 chiffres demandé à la connexion, en plus du mot de passe, pour les comptes du BNC. |
| **Journal** | Registre non modifiable des opérations sensibles. |
| **Grade** | Rang du membre dans l'Armée du Salut : Camarade à l'entrée, puis de Soldat de 3ᵉ classe à Supérieur Suprême Spirituel (RI art. 77). |
| **CM** | Cotisation mensuelle due par chaque membre (100 F CFA par mois à ce jour). |
| **À jour** | Se dit d'un membre qui a payé toutes les cotisations dues jusqu'au mois en cours. |
| **APDP** | Autorité de Protection des Données Personnelles du Bénin. |
| **Site d'essai** | Copie du site, avec des données fictives, où chaque nouveauté est essayée avant la mise en ligne. |

## Annexe B — Récapitulatif des statuts et de leurs causes

| Événement | Décidé par | Statut obtenu | Compte | Mandats | Mutation en cours |
|---|---|---|---|---|---|
| Suspension ou retrait temporaire | BNC | Sanctionné | Conservé | Droits suspendus | Maintenue |
| Exclusion (temporaire ou définitive) | BNC | Exclu | Désactivé | Clos | Annulée |
| Démission confirmée | BNC | Démissionnaire | Désactivé | Clos | Annulée |
| Décès confirmé | BNC | Décédé | Désactivé | Clos | Annulée |
| Fin de sanction temporaire | Automatique | Actif | Réactivé | — | — |
| Réhabilitation validée | BNC | Actif | Réactivé (nouveau mot de passe) | — | — |
| Levée d'une sanction | BNC | Selon les sanctions restantes | Selon le statut | — | — |
