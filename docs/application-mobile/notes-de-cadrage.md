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

## 2. Questions ouvertes
- Liste des types de culte, avec un **modèle réel** de programme et de pamphlet pour chacun
  (photo ou PDF).
- Modification des formats dans l'application ou export Word (à discuter).
- Existe-t-il un **calendrier des lectures** (lectionnaire) ou un thème fixé pour chaque dimanche ?
- Hors ligne ? Android seulement ? Partage (WhatsApp, impression) ?
- **Dépôt GitHub séparé** à créer par le mainteneur (Claude ne peut pas créer de dépôt). Ces notes
  y seront déplacées.
- Liste et format exact de chaque type de culte (modèles papier existants ?)
- Existe-t-il un **calendrier des lectures** (lectionnaire) ou un thème fixé pour chaque dimanche ?
- Hors ligne ? Android seulement ? Partage (WhatsApp, impression) ?

## 3. Décisions
- **[décidé]** Application indépendante du site des membres, propriété du mainteneur.
- **[décidé]** Textes des cantiques fournis par le mainteneur sous forme numérique ; droits acquis.
- **[décidé]** Application pour l'Église en général ; code dans un dépôt séparé.
- **[décidé]** Formats de culte intégrés et paramétrés par type de culte (modification
  ultérieure ou export Word : à discuter).
