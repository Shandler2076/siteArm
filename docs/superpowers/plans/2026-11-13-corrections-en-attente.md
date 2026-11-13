# Corrections relevées par le mainteneur — liste en cours (à compiler, NE PAS exécuter)

> **Règle du mainteneur (13 novembre 2026)** :
> - on compile d'abord toutes les remarques au fil de sa visite du site ;
> - on n'exécute rien et on ne fait aucune mise à jour du site d'essai sans son accord explicite ;
> - on réalise ensuite l'ensemble, en une fois, après validation du plan.
>
> La PR #14 (menu, paroisse actuelle, identifiants) reste ouverte en attendant.

## A. Créer un événement

1. **Date et heure** :
   - date au format **JJ/MM/AAAA** ;
   - l'**heure** dans un champ séparé, nettement décalé de la date (pas collé), pour un rendu plus
     élégant.
2. **Date passée** : si la date (ou la date et l'heure) choisie est antérieure au moment de la saisie,
   le site le signale aussitôt : « Revérifiez votre date ».
3. **Sections** (et non « sessions » comme option) :
   - les sections ne concernent pas tous les événements : c'est une **option à part**, à activer
     seulement si nécessaire (ex. « Organiser l'événement en sections ») ;
   - une fois l'option choisie, on **crée les sections à la main**, selon l'événement : rien de
     pré-rempli, rien à cocher ;
   - le mot est bien **SECTION** (S-E-C-T-I-O-N), partout sur le site ;
   - exemples de noms : « Section Mer » (M-E-R, la mer), « Section Culte », « Section Fruits », ou
     toute section spéciale créée pour cet événement ;
   - on répartit ensuite les convoqués dans ces sections.
4. **« Générer une autorisation pour les convoqués »** :
   - la case actuelle est beaucoup trop petite ;
   - elle devient un vrai **bouton-option**, plus grand, en couleur, bien placé, facile à toucher ;
   - les champs qui en dépendent (validité de l'autorisation, etc.) s'affichent en dessous, une fois
     l'option choisie, pour être remplis.

5. **Autorisation : rôle et formule** (précision du 13/11/2026) :
   - tout le monde ne travaille pas dans une section : il y a aussi des **superviseurs** et des
     **bureaux** conviés à l'événement, qui doivent aussi avoir leur autorisation ;
   - pour chaque convoqué, on choisit **« Invité(e) en tant que »** :
     - **travailleur** d'une section (on précise la section) ;
     - **superviseur** d'une section (on précise la section) ;
     - **bureau** (sans section) ;
   - la formule de l'autorisation se choisit aussi : **« est autorisé(e) à travailler »** ou
     **« est autorisé(e) à participer »**. « À travailler » ne doit pas être imposé dans tous les cas ;
   - l'autorisation imprimée et la page de vérification du QR code affichent ce rôle, la section s'il y
     en a une, et la formule choisie.

## B. Convoquer des membres

1. **Recherche directe d'un membre** (le plus important) :
   - champ de recherche par **matricule** ou par **nom** ;
   - le membre apparaît, on clique dessus, il s'ajoute à la liste, coché ;
   - on peut le décocher ;
   - pas besoin de passer par une région ou un circuit.
2. **Moins de filtres affichés, plus de clarté** : aujourd'hui, trop de choses en bas de la page
   (catégorie, éligible, cotisation…). Les filtres restent possibles mais rangés et discrets.
3. **Grade** et **Statut** : une **liste déroulante** chacun (on clique, la liste défile, on choisit),
   et non plus toutes les valeurs alignées verticalement.
   - « Sexe » et « Grade à partir de » : la forme actuelle convient.
4. **Région → Circuit → Paroisse en cascade** :
   - quand on choisit une région, la liste des circuits ne montre **que les circuits de cette
     région** ;
   - quand on choisit un circuit, la liste des paroisses ne montre que **ses paroisses** ;
   - on ne doit pas pouvoir choisir un circuit hors de la région choisie.
   - Ce point vaut aussi pour les autres pages qui ont ces filtres (Listes).
5. L'option **« Tout cocher »** est bonne : on la garde.

## C. Remarques précédentes déjà réalisées (PR #14, à mettre en ligne plus tard)

- Le menu par thèmes, repliable, avec la rubrique active mise en évidence.
- La paroisse actuelle à l'inscription.
- L'encadré « Identifiants à remettre » et le message de bienvenue.

## D. Questions à poser au mainteneur avant de réaliser

- Sections : un convoqué peut-il appartenir à **plusieurs** sections du même événement (par exemple
  superviseur d'une section et travailleur d'une autre) ?
- Formule « à travailler » / « à participer » : choisie **par convoqué** ou **une fois pour tout
  l'événement** ? Proposition : déduite du rôle (travailleur → « à travailler » ; superviseur et bureau
  → « à participer »), modifiable au besoin.
- Rôle « bureau » : faut-il préciser lequel (Bureau national, région, circuit…) sur l'autorisation ?
- Filtres de convocation : lesquels garder visibles par défaut ? Proposition :
  - visibles : recherche, Région / Circuit / Paroisse, Grade, Statut ;
  - repliés sous « Plus de filtres » : le reste.
- Date passée : simple avertissement (on peut confirmer, ex. pour saisir un événement déjà tenu), ou
  refus ?

*(À compléter au fil des remarques du mainteneur.)*
