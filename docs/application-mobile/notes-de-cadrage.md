# Application mobile « Programmes de culte » — notes de cadrage

> Notes prises au fil des échanges avec le mainteneur (KOUDAKPO Thoovi Marc Aurel).
> Rien n'est encore décidé tant que ce n'est pas marqué **[décidé]**.
> Les propositions de Claude sont marquées **[proposition]**.

## 1. Ce que le mainteneur a dit (échange du 14/11/2026)

### But
- Application mobile pour l'église (Armée du Salut).
- Fonction principale : **générer les programmes de culte**, vite (≈ 10 minutes max pour un
  programme ou un pamphlet).

### Types de culte
- Plusieurs types, chacun avec **son format propre** : veillées de prière, cultes dominicaux,
  cultes de fête, cultes de fête de l'Armée du Salut, etc. — **liste complète à établir**.

### Remplissage guidé
- On choisit un type de culte → l'application présente les **rubriques une à une, dans l'ordre**.
- Pour chaque rubrique : numéro du cantique, officiant (rémission des péchés, 1re lecture,
  2e lecture…), annonces, etc.

### Cantiques (« le plus grand travail »)
- Les cantiques sont **dans l'application** (et sur le site).
- Recherche **par numéro ou par titre** → « numéro + titre » s'inscrit directement dans le
  programme / pamphlet.
- Recueils : **cantiques Gun (Goun)** et **cantiques Yoruba** pour commencer ; français peut-être plus tard.

### Chants spéciaux
- Chants qui ne sont pas des cantiques du recueil.
- Ajout rapide **par photo ou capture d'écran** du texte, inséré dans le pamphlet.

### Quatre documents produits
| Document | Contenu |
|---|---|
| **Programme** | ordre complet, tous les officiants, cantiques, annonces… |
| **Mini-programme** | sans la liste des officiants à l'avance |
| **Pamphlet** | les textes des chants, avec le déroulé |
| **Mini-pamphlet** | uniquement les textes des chants, petit PDF téléchargeable |

### Méthode de travail
- Tout enregistrer au fur et à mesure ; travailler **dans l'ordre**, tout mettre en place avant
  de commencer à coder.

### Échange 2 (14/11/2026)
- Pour l'instant, **c'est l'application personnelle du mainteneur**. Elle n'a **aucun lien avec le site des membres**.
- Plus tard : **vente** de l'application, avec un **code par acheteur** pour empêcher le partage
  (modalités à décider ; pas prioritaire).
- **Textes des cantiques** (Goun et Yoruba) : le mainteneur les fournira lui-même **en version
  numérique**, le moment venu. Claude ne les saisit pas.

### Échange 3 (14/11/2026)
- **Droits sur les textes :** le mainteneur **a le droit** d'utiliser et d'inclure les textes des
  cantiques, y compris dans une version vendue.
- L'application est **pour l'Église en général, pas seulement pour l'Armée du Salut**. Elle est
  **complètement indépendante** du site des membres : on ne mélange pas.
- **Formats :** chaque culte a son format. Ces formats sont **intégrés et paramétrés** dans
  l'application. On pourra peut-être les **modifier ensuite**, ou exporter le programme en **Word**
  pour le retoucher. Ce point sera discuté plus tard.

### Échange 4 (14/11/2026) — gagner de l'argent
- Les modèles réels arrivent **la semaine prochaine** (rappel programmé le lundi 16/11/2026).
- Le mainteneur constate que les applications de cantiques existantes servent **seulement à lire**.
  Aucune ne **produit de programmes ni de pamphlets**. C'est la différence de son application.
- Les textes des cantiques sont publics.
- **Idée du mainteneur :** ouvrir un **centre d'impression**. Il produit le programme ou le pamphlet
  puis l'imprime : un prix pour la production, un prix pour l'impression.

### Pistes de revenus **[propositions de Claude, à discuter]**
1. **Imprimerie (idée du mainteneur)** : commencer par un **partenariat avec des imprimeurs
   existants** (commission) avant d'acheter du matériel. Cela permet de tester la demande sans
   risque.
2. **Cérémonies familiales** : obsèques, mariages, baptêmes, actions de grâce. Les familles paient
   déjà pour des programmes imprimés, souvent avec photo. C'est sans doute le marché le plus
   rentable, à l'unité.
3. **Formule gratuite + formule payante** : lecture des cantiques et mini-pamphlet gratuits (avec la
   mention de l'application). Programme complet, logo de la paroisse, sans mention et export Word
   payants. Paiement **mobile money**.
4. **Abonnement par paroisse** (mois ou année) pour le secrétariat ou la chorale.
5. **Plusieurs Églises et plusieurs recueils** : les Églises qui chantent en Goun et en Yoruba sont
   nombreuses. Chaque nouveau recueil élargit le marché.
6. **Revendeurs** : secrétaires de paroisse ou imprimeurs qui vendent des codes contre commission.
7. **Projection** : afficher les chants sur un écran ou un vidéoprojecteur pendant le culte.

### Échange 5 (14/11/2026) — comment on fait aujourd'hui
- Dans la paroisse du mainteneur, le programme se fait **sur papier, dans un cahier**.
- C'est souvent le **maître de chœur** qui le prépare. Il passe du temps à **fouiller** dans les
  applications de cantiques ou dans les recueils papier, puis à **choisir, aligner et changer** les
  chants. Il réfléchit aussi aux officiants si besoin.
- C'est pareil pour les cérémonies (obsèques, mariages…).
- **Conclusion [proposition] :** l'utilisateur principal est le **maître de chœur**. La difficulté
  principale, c'est de **trouver et d'arranger les chants**. C'est sur ce point que l'application
  doit être la meilleure (recherche instantanée, changement et déplacement d'un chant en un
  geste), avant même les officiants.

### Échange 6 (14/11/2026) — ce qui guide le choix des chants
- Le choix dépend :
  - du **type de culte** (dominical, fête…) ;
  - des **textes** (lectures bibliques) ;
  - de la **place dans le culte** : certains chants ne servent qu'à ouvrir le culte, d'autres vont
    avant la 1re lecture, après la 2e lecture, etc.
- Le mainteneur fournira **beaucoup d'exemplaires** de programmes réels.
- **Deux modes [décidé] :**
  1. **Automatique** : l'application génère seule un programme complet.
  2. **Manuel** : le maître de chœur choisit lui-même chaque chant à chaque place.
- **[proposition]** Le mode automatique produit une *proposition* que le maître de chœur ajuste
  ensuite sur le même écran (remplacer, déplacer). Les deux modes n'en font qu'un en pratique.
- **[proposition]** Les exemplaires servent à apprendre **quels chants vont à quelle place** et
  pour quel culte. Chaque cantique reçoit des étiquettes (places possibles, thèmes, fêtes).

### Échange 7 (14/11/2026) — calendrier des lectures ; PC ou mobile
- L'Église du mainteneur a un **calendrier des lectures** couvrant toute l'année, du 1er janvier au
  31 décembre. Il est donné par le **pamphlet du 25 décembre**, qui fixe les lectures de l'année
  suivante.
  - **[proposition]** Chaque année, on saisit ou on importe ce calendrier dans l'application. Le mode
    automatique part alors de la date pour connaître les lectures. Les autres Églises auront
    leur propre calendrier, ou pas de calendrier du tout (saisie manuelle des lectures).
- **Nouvelle idée du mainteneur :** une application **installée sur son PC**. C'est lui qui produit
  les programmes et les pamphlets pour les clients, en association avec un imprimeur.
- Il garde aussi l'option d'une **application mobile à vendre**. → Analyse des deux possibilités
  demandée (voir réponse de Claude, échange 7).

### Échange 8 (14/11/2026) — option A retenue
- **[décidé] Option A d'abord** : application **sur le PC du mainteneur**. Il produit lui-même
  les programmes et les pamphlets pour ses clients. La version mobile à vendre (option B) viendra
  plus tard, sur le même cœur.
- **[proposition]** Technique : un même code pour Windows maintenant et Android plus tard
  (par exemple Flutter).
- **Déroulement d'une commande :**
  1. Le client, qui peut être n'importe qui, en ligne, envoie sa demande **par WhatsApp**.
  2. Le mainteneur conçoit le programme ou le pamphlet en **5 minutes environ**.
  3. Il envoie le **PDF** au client.
  4. Ensuite, au choix : le client **imprime lui-même**, ou le mainteneur **imprime** (avec
     l'imprimeur partenaire) **et livre**.
- **[proposition]** Deux sorties PDF par document : une **légère pour WhatsApp** (lecture sur
  téléphone) et une **prête à imprimer** (format et pliage à préciser avec les exemplaires).

### Échange 9 (14/11/2026) — ce que le client envoie
- Le client peut préparer son programme sur une feuille. Ce qu'il envoie se résume à :
  - les **numéros des cantiques**, en précisant **Goun ou Yoruba** ;
  - la **liste des officiants**.
- **Concurrence actuelle :** les **centres de saisie**, où quelqu'un tape tout un par un. L'avantage
  du mainteneur est la **rapidité** : l'application sort le document en très peu de temps.
- **[proposition] Saisie rapide :** coller ou taper d'un coup une liste du genre
  `G12, G45, Y230, G7`. L'application retrouve chaque cantique, l'affiche avec son titre et
  son texte, et le place dans l'ordre des rubriques du culte. Les officiants se collent de la
  même façon, un par ligne.
- **[proposition]** La lecture automatique d'une **photo écrite à la main** n'est pas
  prévue au départ : elle n'est pas assez fiable. Elle reste prévue pour les **textes
  imprimés** (chants spéciaux).

### Échange 10 (14/11/2026) — photos, mélange des recueils, lectures
- Si le client envoie une **photo**, le mainteneur la transforme lui-même en texte avec une
  **application externe**, ou relit simplement les informations. **[décidé]** Pas de lecture
  de photo dans notre application pour les demandes des clients.
- Le mainteneur n'a besoin **que des numéros**. L'application a tous les cantiques en mémoire :
  on tape un numéro et elle sort **le titre et le texte complet**.
- **Mélange des recueils dans un même culte : Goun, Yoruba et français.** → Le recueil **français**
  entre aussi dans le projet (texte à fournir).
  - **[proposition]** Une lettre devant le numéro pour éviter toute confusion : `G` = Goun,
    `Y` = Yoruba, `F` = français (ex. `G12`, `Y45`, `F230`), avec un recueil par défaut quand
    on tape le numéro seul.
- Les **noms des officiants** sont tapés rapidement par le mainteneur.
- **Lectures :** le calendrier sert **uniquement aux cultes dominicaux**. Pour les **fêtes**, les
  lectures sont choisies par les devanciers ou les chargés de paroisse, et elles figurent
  **rarement** dans le pamphlet. **[proposition]** Pour les fêtes, le champ « lectures » est
  facultatif et saisi à la main.

### Échange 11 (14/11/2026) — obsèques et pages de couverture
- Mariages : rare. **Obsèques : fréquent** (cultes d'enterrement).
- Les pamphlets ont souvent besoin d'une **page de couverture en couleur, soignée**, avec :
  - des **photos** : défunt, chargé de paroisse, chorale… ;
  - des **logos** sur la première page.
- **[décidé]** L'application génère **plusieurs modèles de couverture**. Le mainteneur les
  **soumet au client**, qui choisit rapidement.
- Le client envoie les **photos à insérer** (chorale, etc.).
- **[proposition]** Les modèles de couverture sont produits automatiquement à partir des mêmes
  photos et textes (plusieurs mises en page et couleurs). On les envoie au client sur WhatsApp
  sous forme d'**images d'aperçu côte à côte**, et il répond « le 2 ».

## 2. Questions ouvertes
- Liste des types de culte, avec un **modèle réel** de programme et de pamphlet pour chacun
  (photo ou PDF).
- Modification des formats dans l'application ou export Word (à discuter).
- Clients réguliers (même paroisse chaque semaine) ou surtout ponctuels ? (→ fiche client
  avec logo, nom de paroisse, photo du chargé, recueil par défaut)
- Notation `G12` / `Y45` / `F230` : à confirmer.
- Format imprimé du pamphlet : feuille simple, livret plié (A4 → A5), nombre de pages ?
- Hors ligne ? Android seulement ? Partage (WhatsApp, impression) ?
- **Dépôt GitHub séparé** à créer par le mainteneur (Claude ne peut pas créer de dépôt). Ces notes
  y seront déplacées.
- Liste et format exact de chaque type de culte (modèles papier existants ?)
- Clients réguliers (même paroisse chaque semaine) ou surtout ponctuels ? (→ fiche client
  avec logo, nom de paroisse, photo du chargé, recueil par défaut)
- Notation `G12` / `Y45` / `F230` : à confirmer.
- Format imprimé du pamphlet : feuille simple, livret plié (A4 → A5), nombre de pages ?
- Hors ligne ? Android seulement ? Partage (WhatsApp, impression) ?

## 3. Décisions
- **[décidé]** Application indépendante du site des membres, propriété du mainteneur.
- **[décidé]** Textes des cantiques fournis par le mainteneur sous forme numérique ; droits acquis.
- **[décidé]** Application pour l'Église en général ; code dans un dépôt séparé.
- **[décidé]** Formats de culte intégrés et paramétrés par type de culte (modification
  ultérieure ou export Word : à discuter).
