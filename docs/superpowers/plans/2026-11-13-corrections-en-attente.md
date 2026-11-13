# Corrections et évolutions demandées par le mainteneur — compilation du 13 novembre 2026

> **Règle du mainteneur** : on compile d'abord, **on n'exécute rien** et on ne met pas à jour le site
> d'essai sans son accord explicite. La réalisation se fera en une fois, par lots, après validation.
> Chaque lot suit la méthode habituelle :
> - tests d'abord ;
> - suites SQLite et PostgreSQL vertes ;
> - relecture indépendante ;
> - PR.

## 0. État d'avancement

| Sujet | État |
|---|---|
| Menu par thèmes, repliable, rubrique active visible | **Réalisé** — PR #14, pas encore en ligne |
| Paroisse actuelle à l'inscription (individuelle et lots) | **Réalisé** — PR #14 |
| Encadré « Identifiants à remettre », bienvenue sans mot de passe | **Réalisé** — PR #14 |
| Grille des cotisations sur une ligne, boutons par année | **Réalisé** — PR #13, fusionnée |
| A. Créer un événement | **Réalisé** le 13/11 (sur ordre « lance tout ») |
| B. Convoquer des membres | **Réalisé** le 13/11 (sur ordre « lance tout ») |
| C. Notifications qui mènent à la bonne page | **Réalisé** le 13/11 (sur ordre « lance tout ») |
| D. Statistiques à paramètres | **Réalisé** le 13/11 (sur ordre « lance tout ») |
| E. Vérifier un membre hors de son périmètre | **Réalisé** le 13/11 (sur ordre « lance tout ») |
| F. Trésorerie, mobile money, cotisations spéciales, reversements | **Réalisé** le 13/11 avec une plateforme **simulée** ; plateforme réelle à choisir |
| G. Guides d'utilisation | **Rédigés** (`docs/guides/`) ; captures d'écran à ajouter |

---

## A. Créer un événement

1. **Date et heure** :
   - date au format **JJ/MM/AAAA** ;
   - **heure dans un champ séparé**, nettement décalé de la date.
2. **Date passée** : si la date et l'heure sont antérieures au moment de la saisie, le site affiche
   aussitôt « **Revérifiez votre date** ».
3. **Sections** :
   - le mot est **SECTION**, partout sur le site ;
   - c'est une **option à part**, à activer seulement si l'événement en a besoin ;
   - une fois l'option choisie, on **crée les sections à la main** : rien de pré-rempli, rien à
     cocher. Exemples : « Section Mer » (la mer), « Section Culte », « Section Fruits », ou une
     section spéciale propre à cet événement ;
   - on répartit ensuite les convoqués dans les sections.
4. **« Générer une autorisation pour les convoqués »** :
   - un vrai **bouton-option**, grand, en couleur et facile à toucher ;
   - les champs qui en dépendent (validité de l'autorisation…) s'affichent en dessous, une fois
     l'option choisie.
5. **Rôle et formule de l'autorisation** :
   - pour chaque convoqué, « **Invité(e) en tant que** » :
     - **travailleur** d'une section (on précise la section) ;
     - **superviseur** d'une section (on précise la section) ;
     - **bureau** (sans section) ;
   - la formule se choisit : « est autorisé(e) **à travailler** » ou « est autorisé(e) **à
     participer** ». « À travailler » n'est plus imposé ;
   - l'autorisation imprimée et la page de vérification du QR code affichent le rôle, la section s'il
     y en a une, et la formule.

## B. Convoquer des membres

1. **Recherche directe** par **matricule** ou par **nom**. On clique sur le membre trouvé : il
   s'ajoute coché, et on peut le décocher. Pas besoin de passer par une région ou un circuit.
2. **Moins de filtres affichés** : la page doit être plus claire. Les autres filtres restent
   possibles, mais rangés.
3. **Grade** et **Statut** : une **liste déroulante** chacun, et non plus toutes les valeurs alignées
   verticalement. « Sexe » et « Grade à partir de » gardent leur forme actuelle.
4. **Région → Circuit → Paroisse en cascade** : on ne voit que les circuits de la région choisie,
   puis que les paroisses du circuit choisi. Même règle sur la page Listes.
5. **Recherche au-dessus des longues listes à cocher** (paroisses, circuits).
6. On garde « **Tout cocher** ».

## C. Notifications qui mènent à la bonne page

- Un clic sur une notification conduit **directement à la page concernée**, sauf pour une simple
  information. Exemples :
  - convocation → « Mes événements », sur cet événement ;
  - nouveau membre → sa fiche ;
  - demande de mutation ou signalement → la demande ;
  - photo acceptée ou refusée → « Ma photo » ;
  - grade → « Ma fiche » ;
  - paiement → « Mes cotisations ».
- La notification cliquée est marquée comme **lue**.
- Le lien ne mène jamais à une page que la personne n'a pas le droit de voir.
- Constat du 13/11 : le site sait rendre une notification cliquable, mais une seule sorte sur une
  trentaine porte un lien aujourd'hui.

## D. Statistiques à paramètres

1. **Un niveau par bureau** : statistiques nationales (BN), régionales, de circuit et de paroisse,
   chacune limitée à son périmètre. Ces pages existent déjà ; le nouveau menu les range sous « Listes
   et statistiques ». À vérifier avec un compte de chaque niveau.
2. Les grands tableaux croisés, illisibles sur téléphone, sont remplacés par un **générateur à
   paramètres**. On coche les paramètres à prendre en compte :
   - tout ;
   - sexe ;
   - tranche d'âge (**âge de début** et **âge de fin**) ;
   - catégorie, région, circuit, paroisse, grade, statut…
3. Pour chaque paramètre, on **choisit la ou les valeurs**, et le site **croise** les choix. Exemple :
   Région WEME + Grade Capitaine → les Capitaines de la région WEME.
4. **Présentation en sous-cases dépliables** : « Par grade » se déplie en grades, « Par région » en
   régions, etc. Pas de défilement horizontal.
5. **Colonnes de la liste produite** :
   - toujours : **matricule, nom, prénoms, sexe, téléphone** ;
   - les autres colonnes seulement si leur paramètre a été choisi. Par exemple, l'âge seulement si
     la tranche d'âge est choisie, et la paroisse seulement si la paroisse est choisie ;
   - on clique sur le matricule pour voir la fiche.
6. **Règle conservée** : chaque chiffre ouvre la liste des membres qu'il compte.
7. **Recherche** au-dessus des longues listes à cocher.

## E. Vérifier un membre hors de son périmètre

- **Qui** : seulement le **Chef** et le **Secrétaire** de chaque bureau (paroisse, circuit, région).
- **Comment** : par le **matricule exact**. Pas de recherche par nom.
- **Ce qu'on voit** :
  - photo validée, grade, prénoms et NOM, matricule ;
  - statut et catégorie ;
  - paroisse, circuit et région actuels ;
  - coordonnées de **sa paroisse**.
- **Ce qu'on ne voit pas** : son téléphone, son adresse, et jamais le NPI ni la photo du CIP.
- **Motif obligatoire** avant d'afficher la carte. Le motif, l'auteur, le bureau et la date sont
  inscrits au **journal** du BN.
- **Protection des données** : nouvelle finalité à ajouter à la page « Protection de vos données »
  et au dossier APDP.

## F. Trésorerie, mobile money, cotisations spéciales, reversements

### F.1 Principe
- **Un seul numéro mobile money**, au nom du Bureau national, par une plateforme de paiement
  (FedaPay, KkiaPay, CinetPay… à comparer). Elle accepte MTN MoMo, Moov Money et Celtiis.
- Le paiement **part toujours du site**, jamais d'un transfert libre : le site sait ainsi exactement
  pour qui et pour quoi chaque paiement est fait.
- **Frais de la plateforme : à la charge du BN.**
- Essais d'abord en **mode test**, sans argent réel. Le compte de la plateforme, les pièces de
  l'association et le responsable désigné seront discutés plus tard.

### F.2 Cotisations mensuelles : chemin unique
1. Le membre paie lui-même par mobile money depuis le site ;
2. ou il remet ses espèces au **Trésorier de sa paroisse**. Celui-ci coche sur le site les membres
   et les mois, puis paie le tout par mobile money au numéro du BN ;
3. la plateforme confirme et les mois sont **marqués payés automatiquement**. **Personne ne
   valide**, ni le circuit ni la région ;
4. **chaque mois**, le BN **reverse** les parts au numéro du Trésorier de chaque unité : paroisse
   30 %, circuit 20 %, région 20 %. Le BN garde 30 %.

- Plus aucune espèce ne circule entre la paroisse et le circuit.
- Le fonctionnement actuel (saisie par la paroisse, validation par le circuit) reste en service
  pour les essais, jusqu'à la mise en place du mobile money.

### F.3 Payer pour un autre membre
- **N'importe quel membre** peut payer pour un autre (membre âgé, sans téléphone, sans Internet).
  Il saisit le **matricule** et le **nombre de mois**, ou choisit la cotisation spéciale.
- Avant de payer, il voit une **confirmation réduite** : grade, prénoms, initiale du nom et paroisse
  (ex. « Soldat Albert A. — Paroisse de GBOA »). Rien de plus.
- Ce sont les **plus anciens mois dus** qui sont payés, sans être montrés au payeur.
- La **personne aidée** reçoit la notification et le reçu. Sa paroisse est avertie, pour pouvoir lui
  remettre le reçu imprimé.
- Le payeur reçoit seulement la confirmation « paiement fait pour le matricule … ».

### F.4 Cotisations spéciales (créées par le BN)
- **Description** : libellé, description, échéance.
- **Type de montant** :
  - **fixe** ;
  - **minimum** (on peut payer plus) ;
  - **libre** (comme un don).
- **Cible**, cochée à la création :
  - **tous les membres** (par défaut) ;
  - ou certains membres, choisis par catégorie, grade, statut, région, circuit, paroisse, sexe ou
    âge ;
  - et/ou **tous les bureaux**, ou seulement les bureaux de paroisse, de circuit ou de région.
- Elle apparaît **« en attente »** sur le profil de chaque membre concerné, ou dans l'espace de
  chaque bureau concerné.
- **Payée directement au BN**, à 100 %, sans partage.
- **Paiement en plusieurs fois** possible, avec une **quittance** PDF numérotée pour chaque paiement.
- **Pas d'espèces enregistrées sur le site** : la paroisse qui reçoit de l'argent le transmet par
  mobile money depuis le site, au nom du membre.
- **Au nom d'un bureau** : le paiement se fait sans rien taper (« Payer au nom de : Paroisse de… »),
  et la quittance porte le nom du bureau. Ce paiement s'ajoute à ceux des membres ; il ne paie pas
  pour eux.
- Pas de code ni de matricule pour les unités pour le moment.

### F.5 Espace de trésorerie
- Un **espace de trésorerie** pour le **Trésorier** de chaque bureau. Il y trouve les flux de son
  bureau : cotisations mensuelles, cotisations spéciales, parts dues, reversements reçus, paiements
  au nom du bureau.
- Le **Trésorier seul** :
  - saisit et paie pour les membres de sa paroisse ;
  - paie au nom du bureau.
- Le **Chef** et le **Secrétaire** voient la trésorerie **en lecture seule**.
- Le **numéro mobile money du Trésorier** est celui du bureau. Il est **enregistré par le BN
  seulement**.
- **Poste vacant** : le **Chef du bureau** assure l'intérim.
- **Reversements au BN** :
  1. le **Trésorier national** prépare l'état mensuel ;
  2. le **Président** (ou le Secrétaire national) le **valide** ;
  3. le Trésorier national fait les envois et enregistre chaque reversement (date, montant,
     référence).
  - Chaque unité voit ce qui lui est dû et ce qu'elle a reçu.
- **Protection des données** : la plateforme de paiement est un sous-traitant (numéro de téléphone,
  montant). Elle est à ajouter au dossier APDP et à la page « Protection de vos données ».

## G. Guides d'utilisation (après réalisation)

En français simple, avec captures d'écran, établis au nom du mainteneur, en Markdown et en PDF dans
`docs/guides/` :

| Guide | Pour qui |
|---|---|
| Le menu et la navigation | Tous |
| Les notifications | Tous |
| Enregistrer un membre (individuel, lots) | BN |
| La fiche d'un membre | BN, bureaux |
| Vérifier un membre | Chef et Secrétaire des bureaux |
| Listes et statistiques | Bureaux, BN |
| Les événements (créer, sections, convoquer, autorisations, pointage) | BN |
| Mes événements et mon autorisation | Membres, paroisses |
| Payer par mobile money (pour soi, pour un autre, pour plusieurs membres) | Membres, trésoriers |
| Les cotisations spéciales | BN, membres, trésoriers |
| L'espace de trésorerie et les reversements mensuels | Trésoriers, BN |

---

## H. Ordre de réalisation proposé (à valider par le mainteneur)

1. **Lot 1, événements et convocation (A, B)**. Le plus attendu ; il ne dépend de rien d'extérieur.
2. **Lot 2, notifications et vérification d'un membre (C, E)**.
3. **Lot 3, statistiques à paramètres (D)**, avec la cascade et la recherche, réutilisées sur la page
   Listes.
4. **Lot 4, trésorerie et cotisations spéciales (F)**, sans paiement réel :
   - l'espace de trésorerie ;
   - les numéros des trésoriers ;
   - les cotisations spéciales ;
   - l'état des reversements et leur validation.
5. **Lot 5, mobile money en mode test (F)**, après le choix de la plateforme.
6. **Lot 6, guides d'utilisation (G)**, et mise à jour du cahier des charges, du récapitulatif et du
   dossier APDP.

Après chaque lot : PR, puis mise à jour du site d'essai **seulement avec l'accord du mainteneur**.

## I. Questions restantes — propositions par défaut appliquées (« lance tout », 13/11/2026)

| Question | Proposition par défaut |
|---|---|
| Un convoqué peut-il être dans **plusieurs sections** d'un même événement ? | Non : un rôle et au plus une section par convoqué |
| Formule « à travailler » / « à participer » : par convoqué ou pour tout l'événement ? | Déduite du rôle (travailleur → travailler ; superviseur et bureau → participer), modifiable par convoqué |
| Rôle « bureau » : préciser lequel sur l'autorisation ? | Oui, si le convoqué a un mandat (ex. « Bureau de la région WEME ») |
| Filtres de convocation visibles par défaut | Recherche, Région / Circuit / Paroisse, Grade, Statut ; le reste sous « Plus de filtres » |
| Date d'événement passée | Avertissement « Revérifiez votre date », avec possibilité de confirmer (événement déjà tenu) |
| Place de « Vérifier un membre » dans le menu | « Mon bureau → Vérifier un membre » |
| « Coordonnées de sa paroisse » sur la carte | Nom de la paroisse et téléphone du Secrétaire paroissial en fonction |
