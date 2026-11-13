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

*(À compléter au fil des remarques du mainteneur.)*
