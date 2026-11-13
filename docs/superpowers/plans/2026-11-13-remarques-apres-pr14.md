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

Décisions du mainteneur (13/11/2026) :
- **Les trois catégories s'excluent** : un membre actif n'est pas membre d'honneur, il reste actif. La
  qualité de membre d'honneur s'accorde à une personne qui n'est pas membre actif ; elle est fixée
  par le BN (à l'enregistrement, ou par décision du BNC), avec la préséance de l'art. 87.
- **Suppression** du signalement « changement de catégorie » par les bureaux : un bureau ne peut
  plus demander de changer la catégorie d'un membre.
- **Seul passage prévu : sympathisant → membre actif**, par **décision du BNC** (date, référence de
  la décision, motif), inscrite à l'historique du membre et au journal ; le membre en est notifié.
- **Erreur de saisie** de la catégorie : corrigée seulement par le BN, comme correction
  exceptionnelle journalisée.
- Les données existantes ne sont pas touchées ; les signalements « catégorie » déjà en cours sur le
  site d'essai sont clos avec la mention « procédure supprimée ».
- Documents à mettre à jour : cahier des charges, guides, page « Protection de vos données ».

## 9. Listes : le matricule ouvre la fiche

Dans toute liste générée (depuis une statistique ou la page Listes), le **matricule** de chaque
ligne devient un **lien** vers la fiche complète du membre, avec ses rubriques : Profil, Cotisation
mensuelle, Participation aux événements (BN seulement).
- Le lien ouvre la fiche **dans l'espace du bureau qui consulte** (gardien des périmètres) : le
  bureau ne voit que les membres de son périmètre, déjà les seuls de sa liste ; au niveau national,
  c'est la fiche du BN.
- Chaque ouverture de fiche reste inscrite au journal, comme aujourd'hui.
- Les exports PDF et Excel ne changent pas.

## 10. « Éligibles au grade suivant » : choisir le grade VISÉ

Constat du mainteneur : en choisissant « Capitaine » avec « Éligibles », la liste montre des
Capitaines. Il attendait les **Sous-Capitaines éligibles à devenir Capitaine**.

Explication : aujourd'hui, le filtre « Grade » désigne le grade **actuel**, et « Éligibles » veut dire
« éligible au grade suivant le sien ». Capitaine + Éligibles donne donc les Capitaines éligibles au
grade d'après.

À réaliser :
- Sur la page « Éligibles au grade suivant », un choix clair **« Éligibles au grade de : … »** (le
  grade visé).
- La liste montre les membres **du grade juste en dessous** qui remplissent les conditions pour le
  grade visé. Exemple : « Capitaine » → les Sous-Capitaines ayant la durée minimale (art. 78).
- Si aucun grade n'est choisi : tous les éligibles, chacun avec une colonne « Grade visé ».
- Pour les grades **par nomination** (Commandant et au-dessus), le site ne peut pas dire qui est
  « éligible » : il montre les membres du grade inférieur avec la durée passée dans leur grade, et la
  mention « par nomination ».
- Dans les filtres ordinaires des listes, le libellé devient « Grade actuel », pour éviter la
  confusion.

## 11. Promotions spéciales (consécrations spéciales) dans le groupe « Grades »

Besoin : le BNC peut décider de grader quelqu'un hors du parcours normal, par exemple un Soldat de
1ʳᵉ classe directement Capitaine. C'est une **promotion spéciale**, ou consécration spéciale.

État actuel (vérifié le 13/11/2026) : le site le permet déjà (art. 84, promotion exceptionnelle). Il
accepte n'importe quel grade, sans condition de durée, avec un motif obligatoire, et l'inscrit à
l'historique et au journal. Mais la fonction est **cachée** : il faut ouvrir la fiche du membre →
« Promouvoir » → cocher « Promotion exceptionnelle ».

À réaliser :
- Une sous-rubrique **« Promotions spéciales »** dans le groupe **Grades** du menu (BN seulement).
- La page permet de :
  - rechercher le membre par nom ou matricule ;
  - choisir le **grade accordé** (n'importe lequel au-dessus du grade actuel) ;
  - indiquer la **date d'effet** et la **référence de la décision du BNC** ;
  - saisir le **motif** (mérites, services remarquables, responsabilités, circonstances : art. 84).
- On peut traiter **plusieurs membres** dans la même décision (liste, comme les promotions en série).
- L'historique du grade porte la mention « Promotion spéciale (art. 84) ». Le membre et sa paroisse
  sont notifiés, et l'action est inscrite au journal.
- Une liste des **promotions spéciales accordées** (date, membre, ancien → nouveau grade,
  référence), consultable par le BN.

## 12. Cumul de fonctions : rien à changer (décision)

Au sein de l'Armée du Salut, une même personne peut cumuler des fonctions à tous les niveaux
(national, région, circuit, paroisse). Le « comité régional » des art. 143 à 146 du règlement
intérieur ne concerne pas l'Armée du Salut. **Aucun avertissement ni aucune restriction de cumul**
n'est à ajouter, sauf mention contraire que le mainteneur transmettra plus tard.

Le site gère déjà ce cumul : plusieurs mandats par personne, des droits additionnés, et des liens
distincts dans le menu (« — national », « — Paroisse de … »).

## 13. « Promotion après test ou examen » et acte de promotion

Décisions du mainteneur (13/11/2026) :
- **« Promotions en série » devient « Promotion après test ou examen »**, distincte de la
  **« Promotion spéciale »** (point 11). Les deux sont dans le groupe « Grades ».
- **L'épreuve** est précisée : **type** (test ou examen), **date** et **lieu** (facultatif). Ces
  informations figurent sur l'acte et dans l'historique de chaque promu.
- **Acte de promotion généré** (PDF, format pré-rempli, en-tête officiel) pour chaque décision :
  - « Décision n° … du … portant promotion après le test (ou l'examen) du … » ;
  - la liste des promus (matricule, grade, prénoms et NOM, ancien grade → nouveau grade, paroisse) ;
  - la date d'effet.
  - **Numéro de la décision : saisi à la main** par le BN.
  - **Signature : le Président seul** (un bloc de signature pré-rempli avec son nom, à signer à la
    main après impression).
- **Le même acte sert pour la promotion spéciale** (art. 84), avec son motif.
- **Extrait pour chaque promu** : chaque membre promu peut télécharger, depuis sa fiche, un extrait de
  l'acte qui ne le concerne que lui (en plus de la notification).
- **Archive des actes** : une liste des actes de promotion (numéro, date, type d'épreuve ou
  « spéciale », nombre de promus), consultable et réimprimable par le BN.

## 14. Du test à la promotion : un seul parcours

Décision du mainteneur (13/11/2026) : la promotion après test ou examen ne concerne **que les
éligibles**, et ce sont les éligibles qui passent le test. Le parcours se suit d'un bout à l'autre :

1. **Éligibles** (point 10) : on choisit le **grade visé** ; le site sort la liste des éligibles.
2. **Créer une session de test ou d'examen** à partir de cette liste :
   - type (test ou examen), date, lieu (facultatif), grade visé ;
   - les éligibles retenus deviennent les **candidats** ;
   - chaque candidat est **notifié** (date, lieu, grade visé).
3. **Après l'épreuve**, saisir le résultat de chaque candidat : **admis**, **ajourné** ou **absent**.
4. **« Promouvoir les admis »** : on **coche** les admis à promouvoir, on saisit le **numéro de la
   décision** et la date d'effet. Le site :
   - promeut les admis cochés au grade visé ;
   - génère l'**acte de promotion** (point 13), avec la mention de l'épreuve ;
   - notifie chaque promu et sa paroisse, et inscrit tout au journal.
- Seuls des **éligibles** peuvent être candidats. Un membre non éligible ne peut être promu que par
  **promotion spéciale** (art. 84, point 11).
- Les **ajournés** et les **absents** restent éligibles et pourront être candidats à une session
  suivante.
- Les sessions passées restent consultables : candidats, résultats, acte associé.

*(À compléter au fil des remarques du mainteneur.)*
