# Comparatif d'hébergement — site de gestion des membres

---

*Document préparé le 11 novembre 2026 pour l'étape 8 (mise en ligne). Les prix sont indicatifs
et doivent être revérifiés sur le site de l'hébergeur le jour de la commande (voir § 6).*

## 1. Ce que le site doit avoir chez l'hébergeur

| Besoin | Pourquoi | Volume prévu au départ |
|---|---|---|
| Une application Python (Django) | Le site lui-même | 512 Mo de mémoire (production des PDF et des fichiers Excel) |
| Une base PostgreSQL | Membres, parcours, journal… | Moins de 1 Go pendant plusieurs années |
| Un espace de fichiers **privé** | Photos d'identité et photos du CIP | 2 à 6 Go (environ 10 000 membres × 2 photos) |
| Une tâche quotidienne | Échéances des mandats et fin des sanctions | 2 commandes chaque matin |
| L'envoi d'e-mails | Notifications aux membres qui ont une adresse | Quelques dizaines par jour |
| Des sauvegardes | Cahier des charges § 9.4 : quotidienne + copie hebdomadaire chiffrée ailleurs | Quelques Go |
| HTTPS et le nom de domaine `.bj` | Sécurité et adresse officielle | 1 domaine |
| Un **site d'essai** | Cahier des charges § 12.2 : on vérifie avant la mise en ligne | Petit |

## 2. Les solutions comparées

Toutes hébergent les données **en France**, sauf la quatrième, où le choix reste libre.

| | A. Scalingo | B. Clever Cloud | C. alwaysdata | D. Serveur privé (VPS) |
|---|---|---|---|---|
| Type | Plateforme gérée (PaaS) | Plateforme gérée (PaaS) | Hébergement géré | Serveur à administrer soi-même |
| Entreprise | Française (Strasbourg) | Française (Nantes) | Française (Paris) | OVHcloud (française), Hetzner… |
| Mise à jour du système et sécurité | Hébergeur | Hébergeur | Hébergeur | **Le mainteneur** |
| Mise en ligne d'une nouvelle version | `git push` automatique | `git push` automatique | Petit script (fourni) | Tout à faire soi-même |
| PostgreSQL | Inclus (offre « Starter ») | Inclus (offre « XXS ») | Inclus dans le pack (**à confirmer**) | À installer soi-même |
| Fichiers privés (photos) | **Stockage externe à ajouter**, avec une petite modification du code | Stockage externe à ajouter (Cellar), même modification | **Sur le disque**, le code actuel fonctionne tel quel | Sur le disque |
| Tâche quotidienne | Oui (`cron.json`) | Oui (`cron.json`) | Oui (tâches planifiées) | Oui (`cron`) |
| Sauvegardes de la base | Quotidiennes + retour à un instant précis sur 7 jours | Quotidiennes | Quotidiennes, gardées 30 jours | À organiser soi-même |
| Site d'essai | Une 2ᵉ application (payante, à éteindre quand on ne s'en sert pas) | Une 2ᵉ application (petite) | **Inclus** : un 2ᵉ site dans le même compte | Possible sur le même serveur |
| Montée en charge | Très facile | Très facile | Limitée par le pack (on change de pack) | Changer de serveur |

## 3. Coûts estimés

Le franc CFA est converti au taux fixe 1 € = 655,957 FCFA. « HT » veut dire sans la TVA française
de 20 %. Une association établie hors de l'Union européenne peut ne pas payer cette TVA, ce qui est
à confirmer avec l'hébergeur.

### Production seule (par mois)

| | A. Scalingo | B. Clever Cloud | C. alwaysdata | D. VPS |
|---|---|---|---|---|
| Application | Conteneur M (512 Mo) : 14,40 € | Instance XS (1 Go) : 16,00 € | Pack 10 Go : **7,00 €** (tout compris) | 4 à 7 € |
| Base PostgreSQL | Starter 512 Mo : 7,20 € | XXS : 4,90 € | incluse | incluse |
| Photos (stockage externe, environ 5 Go) | environ 0,10 € | environ 0,10 € | incluses | incluses |
| **Total HT / mois** | **≈ 21,70 €** (≈ 14 200 FCFA) | **≈ 21,00 €** (≈ 13 800 FCFA) | **7,00 €** (≈ 4 600 FCFA) | ≈ 4 à 7 € |
| Total TTC / mois | ≈ 26,00 € (≈ 17 100 FCFA) | ≈ 25,20 € (≈ 16 500 FCFA) | 8,40 € (≈ 5 500 FCFA) | ≈ 5 à 8,40 € |

### Site d'essai (par mois, s'il reste allumé en permanence)

| A. Scalingo | B. Clever Cloud | C. alwaysdata | D. VPS |
|---|---|---|---|
| ≈ 14,40 € HT (moins s'il est éteint entre deux essais) | ≈ 6 € HT (base « Dev » gratuite) | **0 €** (inclus dans le pack) | 0 € (même serveur) |

### Coûts communs à toutes les solutions

| Élément | Coût estimé |
|---|---|
| Nom de domaine `.bj`, chez un bureau d'enregistrement béninois | ≈ 9 900 à 10 500 FCFA par an |
| E-mails (Brevo, offre gratuite : 300 e-mails par jour) | 0 € |
| Copie de sauvegarde hebdomadaire chiffrée chez un autre fournisseur (Scaleway, quelques Go) | < 1 € par mois |

### Total sur un an (production + site d'essai + domaine, HT)

| A. Scalingo | B. Clever Cloud | C. alwaysdata | D. VPS |
|---|---|---|---|
| ≈ 455 € (≈ 298 000 FCFA) | ≈ 345 € (≈ 226 000 FCFA) | **≈ 105 € (≈ 69 000 FCFA)** | ≈ 70 à 105 €, **plus le temps du mainteneur** |

## 4. Avantages et inconvénients

**A. Scalingo**
- ✅ C'est la plateforme la plus « clé en main » : mise en ligne par `git push`, base avec retour à un instant précis, et le site est déjà préparé pour elle (fichier `Procfile`).
- ✅ Elle s'adapte facilement si le nombre d'utilisateurs grandit.
- ⚠ Elle coûte environ trois fois plus cher que C.
- ⚠ Les photos doivent aller sur un stockage externe, ce qui demande une petite modification du code et un fournisseur de plus.

**B. Clever Cloud**
- ✅ Les avantages sont proches de ceux de Scalingo, et le site d'essai coûte moins cher.
- ⚠ La grille tarifaire est moins lisible : elle est facturée à la consommation, et je n'ai pas trouvé tous les prix officiels.
- ⚠ Le stockage externe des photos est nécessaire, comme pour A.

**C. alwaysdata**
- ✅ C'est le coût le plus bas, et tout est inclus : base, tâches planifiées, sauvegardes de 30 jours, HTTPS et e-mail.
- ✅ Les photos privées restent sur le disque : **aucune modification du code** n'est nécessaire.
- ✅ Le site d'essai est inclus.
- ✅ L'hébergeur gère la sécurité du système.
- ⚠ La mise en ligne d'une nouvelle version passe par un petit script, que je fournirai et documenterai, plutôt que par un `git push`.
- ⚠ Les ressources sont partagées. C'est suffisant pour quelques milliers de membres, mais il faudrait changer de pack, ou passer à A, si l'usage grandissait beaucoup.
- ⚠ Il n'y a pas de retour à un instant précis : les sauvegardes sont quotidiennes.

**D. Serveur privé (VPS)**
- ✅ C'est le moins cher en apparence.
- ❌ Les mises à jour de sécurité, le pare-feu, les sauvegardes et la surveillance sont à la charge du mainteneur. C'est contraire au choix du cahier des charges (§ 1 : hébergeur géré, adapté à un mainteneur seul). **Je ne le recommande pas.**

## 5. Recommandation

**Démarrer avec C (alwaysdata, pack 10 Go)**, pour un coût d'environ 69 000 FCFA par an, domaine et site
d'essai compris.

**Pourquoi :**
- C'est le coût le plus faible pour un service géré.
- Les données sont hébergées en France.
- Les sauvegardes et les tâches quotidiennes sont incluses.
- Le site actuel fonctionne sans aucune modification.

**Si l'usage grandit beaucoup**, le passage à Scalingo (A) reste simple, car le site y est déjà préparé : il
suffirait d'ajouter le stockage externe des photos.

**Plan B :** si l'Église préfère d'emblée la solution la plus automatisée, choisir A (Scalingo), pour environ
298 000 FCFA par an, site d'essai compris.

## 6. Points à vérifier avant de commander

1. **Les prix du jour sur les sites officiels.** Pendant cette étude, je n'ai pas pu consulter directement les pages tarifaires : les chiffres viennent des pages des hébergeurs et de comparatifs récents.
2. **Chez alwaysdata** : que PostgreSQL est bien inclus dans le pack 10 Go et quelle mémoire est disponible pour l'application.
3. **La TVA** : si l'Église commande comme association établie au Bénin, la TVA française peut ne pas s'appliquer. Il faut le demander à l'hébergeur.
4. **Le moyen de paiement** : une carte bancaire internationale ou PayPal, en euros, avec un prélèvement mensuel.
5. **Le nom de domaine `.bj`** : choisir le bureau d'enregistrement béninois, le nom exact (par exemple `armeedusalut.bj`) et le titulaire, qui sera l'Église et non une personne.
6. **La protection des données (APDP)** : héberger les données en France est un **transfert de données personnelles hors du Bénin**. Le Code du numérique (loi n° 2017-20) l'encadre. Il faudra le mentionner dans la déclaration à l'APDP, préparée à l'étape suivante, et obtenir son accord **avant** la mise en ligne réelle.

## Sources consultées (11 novembre 2026)

- Scalingo : [tarifs](https://scalingo.com/pricing), [politique de sauvegarde des bases](https://doc.scalingo.com/databases/backup-policies), [comparatif européen 2026](https://pethost.dev/blog/european-hosting-postgres-flat-price/)
- Clever Cloud : [comparatif Clever Cloud / Heroku](https://www.clever.cloud/clever-cloud-vs-heroku/), [orkestr vs Clever Cloud](https://orkestr.eu/alternatives/clever-cloud), [documentation PostgreSQL](https://www.clever-cloud.com/doc/deploy/addon/postgresql/)
- alwaysdata : [hébergement Django](https://www.alwaysdata.com/fr/hebergement-django/), [Dev WP — quelle offre choisir](https://www.dev-wp.fr/quelle-offre-alwaysdata-choisir/), [Guide Hébergeur](https://www.guide-hebergeur.fr/offres/hebergement-linux/alwaysdata/PackMini/)
- VPS : [VPS-1 OVHcloud (vpsbenchmarks)](https://www.vpsbenchmarks.com/hosters/ovhcloud/plans/vps-1), [gamme VPS 2027 OVHcloud](https://blog.ovhcloud.com/vps-2027/)
- Stockage et e-mails : [tarifs Scaleway Object Storage](https://www.scaleway.com/fr/tarifs/storage), [Brevo — API e-mail gratuite](https://www.brevo.com/en/features/email-api/)
- Domaine `.bj` : [MTN GoDigital — tarifs](https://godigital.mtn.bj/domain/pricing), [nom-domaine.bj](http://www.nom-domaine.bj/), [Afriregister Bénin](https://www.afriregister.bj/)
