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

## E. Notifications qui mènent à la bonne page

- Quand on clique sur une notification, on arrive **directement à la page concernée**. La notification
  ne reste pas un simple message, sauf pour une information libre.
- Exemples :
  - « Vous êtes convoqué(e) à un événement » → page « Mes événements », sur cet événement (section,
    autorisation à imprimer…) ;
  - nouveau membre dans le périmètre → fiche du membre ;
  - demande de mutation ou signalement → la demande ;
  - versement à valider → « Versements à valider » ;
  - photo acceptée ou refusée → « Ma photo » ;
  - décision de grade → « Ma fiche » ;
  - cotisation validée → « Mes cotisations ».
- État actuel (vérifié le 13/11/2026) : le site sait déjà rendre une notification cliquable, mais une
  seule sorte de notification sur une trentaine porte un lien. Il faut donc relier chaque sorte de
  notification à sa page, en respectant les droits (un lien ne montre jamais ce que la personne n'a
  pas le droit de voir).
- La notification cliquée est marquée comme lue.

## F. Statistiques : un générateur à paramètres, plus lisible

1. **À chaque niveau** : statistiques nationales (BN), régionales (bureau de région), de circuit
   (bureau de circuit) et de paroisse (bureau de paroisse), chacune limitée à son périmètre.
   - État actuel (vérifié le 13/11/2026) : chaque bureau a déjà une page « Statistiques » limitée à
     son périmètre, et le nouveau menu (PR #14) la met dans « Listes et statistiques ». À vérifier
     sur place avec un compte de chaque niveau.
2. **Statistique dynamique, à paramètres**, à la place des grands tableaux croisés tout faits (grade
   par tranche d'âge, par sexe, par région…), difficiles à lire : trop de colonnes, il faut défiler à
   droite.
   - On coche les **paramètres à prendre en compte**, et le site génère la statistique et la liste
     correspondante :
     - tout ;
     - par sexe ;
     - par tranche d'âge, avec l'**âge de début** et l'**âge de fin** à saisir ;
     - par catégorie ;
     - par région, par grade, etc.
   - Exemple : on coche « région » et « grade », et on obtient la statistique pour ces deux
     paramètres seulement.
   - Règle conservée : chaque chiffre ouvre la liste des membres qu'il compte (mêmes filtres).
3. **Présentation par sous-cases dépliables**, plutôt que tout aligné : « Par grade » se déplie pour
   montrer chaque grade, « Par catégorie » ses catégories, « Par région » ses régions, etc. Une
   présentation élégante, lisible sur téléphone, sans défilement horizontal.
4. **Combiner les paramètres (réponse du mainteneur)** : on choisit une ou plusieurs valeurs pour
   chaque paramètre (ex. Région : la région concernée ; Grade : le grade concerné). Le site **croise**
   ces choix et donne le résultat recherché (ex. les Capitaines de la région WEME), au lieu de tout
   détailler.
5. **Colonnes de la liste générée** :
   - toujours affichées : **matricule, nom, prénoms, sexe, téléphone** ;
   - les autres colonnes n'apparaissent **que si le paramètre correspondant a été choisi** :
     - l'âge, seulement si l'âge (tranche d'âge) est un paramètre ;
     - la paroisse, seulement si la paroisse est un paramètre (si on a choisi seulement une région,
       on n'a pas besoin de la paroisse) ;
     - le grade, la catégorie, la région, le circuit, etc., suivent la même règle ;
   - pour en savoir plus sur une personne, on clique sur son matricule et on ouvre sa fiche.
6. **Recherche dans les longues listes à cocher** (paroisses, circuits) : un champ de recherche au-dessus
   de chaque liste, pour trouver et cocher sans tout faire défiler. Cela vaut pour les statistiques,
   les listes et la convocation.

## G. Consulter l'identité d'un membre hors de son périmètre (« Vérifier un membre »)

Besoin : un membre d'une autre paroisse arrive chez nous, ou commet une faute, et le bureau doit
savoir qui il est. Décisions du mainteneur (13/11/2026) :

1. **Qui** : seulement le **Chef** et le **Secrétaire** de chaque bureau (paroisse, circuit, région).
   Pas les autres responsables, pas les trésoriers, pas les membres simples. Le BN voit déjà tout.
2. **Comment on retrouve la personne** : par son **matricule exact** (ex. 2015-01AS-0157), que la
   personne donne ou qui figure sur sa fiche. **Pas de recherche par nom** : on ne doit pas pouvoir
   parcourir les membres des autres paroisses.
3. **Ce qu'on voit**, une **carte d'identité** seulement :
   - la photo d'identité validée, le grade, les prénoms et le NOM, le matricule ;
   - le statut (actif, sanctionné, exclu…) et la catégorie ;
   - la paroisse, le circuit et la région actuels ;
   - les coordonnées de **sa paroisse**, pour la contacter.
   On ne voit **pas** son téléphone ni son adresse, et **jamais** le NPI ni la photo du CIP.
4. **Contrôle** : un **motif obligatoire** avant d'afficher la carte (ex. « membre en visite dans
   notre paroisse », « faute commise », ou un motif écrit). Le motif, l'auteur, le bureau et la date
   sont inscrits au **journal** du BN, comme toute action sensible (règle du site).
5. Pour un membre de son propre périmètre, rien ne change : le bureau voit déjà sa fiche.
6. **Protection des données** : cette nouvelle finalité doit être reportée sur la page « Protection
   de vos données » et dans le dossier APDP. Dans la règle du gardien des périmètres, c'est une
   exception encadrée : carte réduite, matricule exact, motif, journal.

## H. Projet à étudier : paiement par mobile money et cotisations spéciales

### H.1 Un seul numéro mobile money au nom du Bureau national
- Le site passe par une plateforme de paiement (FedaPay, KkiaPay, CinetPay… à comparer). Elle accepte
  MTN MoMo, Moov Money et Celtiis, et confirme chaque paiement au site.
- L'argent arrive sur **un seul compte**, celui du BN.

### H.2 Cotisations spéciales (créées par le BN)
- Le BN crée une cotisation spéciale : libellé, description, montant et échéance.
- Elle apparaît d'office sur le profil de tous les membres concernés, **« en attente »**.
- Elle est payée **directement au BN** (100 %, sans partage).
- Une **quittance** PDF numérotée atteste le paiement.

### H.3 Cotisations mensuelles (partage 30 / 20 / 20 / 30) : proposition
Deux façons de payer coexistent :
1. **En espèces à la paroisse** : rien ne change. La paroisse saisit, le circuit valide, et chaque
   niveau reçoit sa part de la main à la main, comme aujourd'hui.
2. **Par mobile money au BN** (par le membre lui-même, ou par la paroisse pour plusieurs membres) :
   - le BN reçoit 100 % ;
   - le site marque les mois payés aussitôt (sans validation du circuit) ;
   - le site **calcule et tient le compte** de ce que le BN doit à chaque paroisse (30 %), circuit
     (20 %) et région (20 %) ;
   - le BN **reverse périodiquement** (ex. chaque mois ou chaque trimestre) par mobile money au
     numéro du trésorier de chaque paroisse, circuit et région ;
   - le site produit l'**état des reversements** et note chaque reversement (date, montant,
     référence) ;
   - chaque niveau voit sur sa page « Parts reçues » ce qui lui est dû et ce qu'il a reçu ;
   - les frais de la plateforme sont répartis selon une règle à décider.

### H.4 Décisions du mainteneur (13/11/2026)
- **Reversements : chaque mois.** Le BN reverse par mobile money la part de chacun au numéro du
  **trésorier** de chaque paroisse, circuit et région. Le site produit l'état mensuel des
  reversements.
- Pour les paiements par mobile money, **ni le circuit ni la région n'ont rien à valider** : tout se
  fait au niveau du BN.
- **Frais de la plateforme : à la charge du BN.** Le membre paie le montant exact, et les parts de la
  paroisse, du circuit et de la région sont calculées sur ce montant.
- **Cotisations spéciales**, l'option se choisit à la création :
  - **montant fixe** ;
  - **montant minimum** (on peut payer au-delà) ;
  - **montant libre / facultatif** (comme un don).
- **Paiement en plusieurs fois** possible pour une cotisation spéciale, jusqu'à atteindre le montant ;
  une quittance pour chaque paiement.
- **Pas d'espèces enregistrées sur le site pour les cotisations spéciales** : si un membre remet de
  l'argent à sa paroisse, la paroisse le **transmet elle-même par mobile money** au numéro unique du
  BN, au nom de ce membre.
- **Compte de la plateforme, pièces de l'association, responsable désigné : on en discutera plus
  tard.** On reste en phase d'essai (mode test, sans argent réel).

### H.5 Décisions complémentaires (13/11/2026)
- **Cotisation spéciale : pour qui.** À la création, le BN choisit :
  - **tous les membres** (le cas le plus fréquent, choisi par défaut) ;
  - ou **certains membres**, en choisissant parmi : catégorie, grade, statut, région, circuit,
    paroisse, sexe, tranche d'âge (mêmes filtres que les listes).
- **Paiement d'une paroisse pour plusieurs membres** :
  - le paiement part **du site**, et non d'un transfert libre depuis le téléphone ;
  - la paroisse coche sur le site les membres (matricules) et les mois, puis clique sur « Payer par
    mobile money » ;
  - le site garde la liste des matricules et des mois, liée à la référence du paiement ;
  - la description du paiement envoyée à la plateforme peut aussi mentionner les matricules, à titre
    indicatif ;
  - dès que la plateforme confirme, le site marque payés exactement ces mois-là pour ces membres.
  - Raison : un transfert mobile money fait à la main (code USSD, message libre) ne permet pas au
    site de savoir sûrement pour quels membres il a été fait.
- **Numéro mobile money du trésorier de chaque unité : enregistré par le BN seulement.**

## I. Guides d'utilisation (à préparer le moment venu)

Une fois les fonctions réalisées, préparer un **guide d'utilisation** pour chaque partie décrite, en
français simple, avec des captures d'écran, établi au nom du mainteneur. Chaque guide existera en
Markdown et en PDF, dans `docs/guides/`.

| Guide | Pour qui | Contenu |
|---|---|---|
| Le menu et la navigation | Tous | Groupes, rubrique active, Mon espace |
| Enregistrer un membre (individuel, lots) | BN | Paroisse actuelle, identifiants à remettre |
| La fiche d'un membre | BN, bureaux | Rubriques Profil / Cotisation mensuelle / Événements, années |
| Vérifier un membre | Chef et Secrétaire des bureaux | Matricule exact, motif, carte d'identité |
| Listes et statistiques | Bureaux, BN | Paramètres, sous-cases, colonnes, recherche |
| Événements | BN | Créer, sections, convoquer (recherche), rôles, autorisations, pointage |
| Mes événements et mon autorisation | Membres, paroisses | Imprimer, QR code |
| Cotisations mensuelles | Paroisse, circuit, région, BN | Espèces, grille, validation, parts, reversements |
| **Payer par mobile money** | Membres, paroisses | Payer ses mois, payer pour plusieurs membres, reçu |
| **Cotisations spéciales** | BN, membres | Créer (montant fixe / minimum / libre, cible), payer, quittance |
| **Reversements mensuels** | BN, trésoriers | État des reversements, numéros des trésoriers, suivi |
| Notifications | Tous | Cliquer pour aller à la bonne page |

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
- Vérifier un membre : où placer la rubrique dans le menu ? Proposition : « Mon bureau → Vérifier un
  membre ». Les coordonnées de la paroisse : lesquelles existent sur le site (téléphone du secrétaire
  paroissial ?) — à confirmer.
- Date passée : simple avertissement (on peut confirmer, ex. pour saisir un événement déjà tenu), ou
  refus ?

*(À compléter au fil des remarques du mainteneur.)*
