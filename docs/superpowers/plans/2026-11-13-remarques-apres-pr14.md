# Remarques du mainteneur après la PR #14 — liste en cours (à compiler, NE PAS exécuter)

> **Règle du mainteneur** : on compile seulement. **On ne modifie rien sans son accord** ; la
> réalisation se fera en bloc, après l'ensemble de ses remarques.

## 1. Page « Convoquer des membres » : deux colonnes

Constat (capture du 13/11/2026) : le tableau des membres à cocher est dans le fil de la page,
sous la recherche. On voit mal qui est déjà sélectionné.

Décisions du mainteneur :
- **Ordinateur, deux colonnes** :
  - **à gauche** : la recherche (matricule ou nom), les filtres et les **résultats trouvés** à cocher,
    avec « Tout cocher » ;
  - **à droite**, à part : un panneau **« Membres sélectionnés (N) »** qui se remplit **au fur et à
    mesure** (par la recherche ou par les filtres) et reste visible quand on fait défiler la page.
- **Le panneau de droite ne montre que les membres cochés**, chacun avec un bouton pour le retirer.
  Cocher un résultat à gauche l'envoie à droite ; le décocher l'en retire.
- Le rôle (Invité(e) en tant que), la section, la formule et le bouton **« Convoquer les membres
  sélectionnés »** sont dans le panneau de droite.
- **Téléphone** : une **barre fixe en bas de l'écran**, « N membres sélectionnés — Voir / Convoquer »,
  qui ouvre la liste des sélectionnés (avec le rôle, la section, la formule et le bouton).

## 2. « Invité(e) en tant que » : nouvelle liste de rôles

« Bureau » tout court n'est pas adéquat : il peut y avoir des **bureaux d'organisation**, qui sont
aussi comme des superviseurs. Nouvelle liste :
- **Travailleur** ;
- **Superviseur** ;
- **Bureau d'organisation** (remplace « Bureau ») ;
- **Officiel** ;
- **Autre**, écrit **à la main** (ex. « Chorale », « Protocole », « Secouriste »…). Il peut y avoir
  **plusieurs** rôles « autres » différents dans un même événement.

Questions à poser au mainteneur avant de réaliser :
- Quels rôles se rattachent à une **section** ? Proposition : Travailleur et Superviseur ; les autres
  (Bureau d'organisation, Officiel, Autre) sans section, sauf si on en choisit une.
- Formule par défaut de chaque rôle : « à travailler » pour Travailleur ; « à participer » pour les
  autres, toujours modifiable ?
- « Autre » : un seul rôle écrit par convoqué (ex. « Protocole »), le site gardant en mémoire les rôles
  déjà écrits pour l'événement afin de les proposer à nouveau ?
- Pour les membres déjà convoqués « en tant que bureau » : les passer en « Bureau d'organisation » ?

*(À compléter au fil des remarques du mainteneur.)*
