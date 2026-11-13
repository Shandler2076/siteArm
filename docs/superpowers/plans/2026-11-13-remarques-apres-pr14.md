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

## 3. Cases à cocher mal alignées (page « Cotisations spéciales » du BN)

Constat (capture du 13/11/2026) : dans « Type de montant », les ronds à cocher ne sont pas sur la
même ligne que leur texte (Montant fixe, Montant minimum, Montant libre) : ils sont décalés au-dessus
et à droite.

À corriger :
- chaque rond ou case **sur la même ligne, à gauche de son texte**, et toute la ligne cliquable ;
- même correction pour les autres choix de la page : « Membres concernés » (ronds) et « Bureaux
  concernés » (cases) ;
- vérifier tous les autres formulaires du site qui ont des ronds ou des cases (une règle de style
  commune).

## 4. Page « Cotisations spéciales » (BN) : réorganisation complète

Décisions du mainteneur (13/11/2026) :

### 4.1 Type de montant
- Ronds alignés, explicites, faciles à cocher (voir point 3).
- **Montant fixe** : une case « montant » s'ouvre **juste devant**, obligatoire.
- **Montant minimum** : une case « montant minimum » s'ouvre **juste devant**, obligatoire.
- **Montant libre** (don) : une case **« montant suggéré »**, facultative, s'ouvre devant. Elle est
  montrée aux membres comme indication ; chacun donne ce qu'il veut.
- Il n'y a plus de case « montant » commune en bas.

### 4.2 À qui s'adresse la cotisation (choix combinables)
- **Tous les membres** : rien d'autre à choisir.
- **Unités**, où toute l'unité paie **ensemble** un montant :
  - unité paroissiale ;
  - unité de section circuit ;
  - unité régionale de coordination.
- **Bureaux**, où le bureau de l'unité paie :
  - bureau de l'unité paroissiale ;
  - bureau de l'unité de section circuit ;
  - bureau de l'unité régionale de coordination.
- Pour une unité comme pour un bureau, **c'est le Trésorier de l'unité qui paie** depuis le site
  (après avoir collecté l'argent). La **quittance porte deux noms distincts** : « Unité paroissiale
  de … » pour une cotisation d'unité, « Bureau de l'unité paroissiale de … » pour une cotisation de
  bureau. On sait ainsi qui a payé quoi.
- **Certains membres** : en cliquant, une liste se déroule avec **trois façons de choisir,
  combinables** :
  1. **les membres des bureaux** (bureaux d'unité paroissiale, de section circuit, d'unité régionale
     de coordination, national), chaque membre de bureau payant pour lui-même ;
  2. **par critères** (grade, région, catégorie, âge…) ;
  3. **membres désignés** : recherche par **nom ou matricule**, on ajoute une ou plusieurs personnes
     (par exemple une seule personne).
- On peut cocher plusieurs cibles à la fois (ex. tous les membres + les unités paroissiales).

### 4.3 Sanction à payer en numéraire (amende)
- **Liée à la sanction** :
  - le BNC inscrit la sanction (comme aujourd'hui) et indique « amende à payer : X F » ;
  - l'amende apparaît **en attente chez le membre seul**, avec une quittance à chaque paiement ;
  - elle reste dans l'historique de la sanction (motif : la faute et la décision prise à telle date).
- Pour la discrétion, l'amende **n'apparaît pas** dans la liste des cotisations spéciales.
- Elle est payée au BN par mobile money, comme les cotisations spéciales. Comme aujourd'hui, seul le
  BNC inscrit les sanctions.

### 4.4 Questions restantes
- Amende : peut-on la payer pour un autre membre (« payer pour un autre ») ? Proposition : oui, mais
  le payeur ne voit que « Amende — X F » et rien de la faute.
- Unités : le montant demandé à une unité est-il le même pour toutes les unités (ex. 50 000 F par
  paroisse) ? Proposition : oui, un montant par type d'unité.

## 5. Numéros mobile money des bureaux

On garde la page comme elle est : la recherche suffit à trouver un bureau, à saisir son numéro et à
l'enregistrer (décision du 13/11/2026).

## 6. Reversements mensuels : page plus claire

Constat : en changeant de mois, on ne voyait pas si l'état serait généré automatiquement. En effet :
- « Afficher » ne fait que choisir le mois ;
- le bouton « Préparer » n'est visible que du Trésorier national ;
- le site d'essai n'avait aucun paiement mobile money de cotisation mensuelle dans un mois terminé.

À réaliser :
1. **Aperçu avant de préparer** : le tableau des parts dues pour le mois choisi (paroisse, circuit,
   région, montant, numéro du Trésorier) et le total, visibles avant toute préparation.
2. **Messages clairs** :
   - « Rien à reverser pour ce mois : aucune cotisation payée par mobile money » ;
   - « Ce mois n'est pas encore terminé » ;
   - « En attente de préparation par le Trésorier national » ;
   - « En attente de validation par le Président ou le Secrétaire national » ;
   - « Validé : envois à faire ».
3. **Un rappel des trois étapes** (préparer → valider → envoyer), avec l'étape en cours mise en
   évidence et le nom de la personne qui doit agir maintenant.
4. **Démonstration** : des paiements mobile money (simulés) de cotisations mensuelles dans les mois
   passés, pour pouvoir essayer les trois étapes sur le site d'essai.

## 7. Accueil : afficher le matricule

Sur la page d'accueil (Mon espace → Accueil), sous « Bienvenue, Grade Prénoms NOM », afficher aussi
le **matricule** du membre, bien visible, sans qu'il ait à ouvrir sa fiche.

## 8. « Changement de catégorie » : à revoir (analyse en cours avec le mainteneur)

Remarque du mainteneur : il n'y a pas lieu de faire des « changements de catégorie » (comme si un
membre voulait quitter la catégorie active pour devenir membre d'honneur ou sympathisant).

Ce que dit le règlement intérieur :
- art. 25 : trois catégories (actifs, d'honneur, sympathisants) ;
- art. 27 : la qualité de membre d'honneur est **accordée par le mouvement**, en reconnaissance ;
- art. 87 : elle **ne constitue pas un grade** et ne modifie pas le grade détenu.

L'analyse et les options sont proposées au mainteneur. La décision sera reportée ici.

*(À compléter au fil des remarques du mainteneur.)*
