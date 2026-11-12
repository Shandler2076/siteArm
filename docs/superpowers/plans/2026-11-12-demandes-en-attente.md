# Demandes du mainteneur en attente (12 novembre 2026, fin d'après-midi)

> À exécuter dès que possible, ou le lendemain matin si la limite quotidienne est atteinte.
> Chaque point se termine par des tests, la suite complète (SQLite + PostgreSQL), une PR.

## 1. Cotisations : page « Parts reçues » plus lisible (tous les niveaux)

Constat du mainteneur au niveau du Bureau national (à corriger aussi aux autres niveaux) :

- **Classer les paroisses dans leur circuit, et les circuits dans leur région** : regroupement
  Région → Circuit → Paroisse, de façon à lire « telle paroisse, dans tel circuit, dans telle
  région ».
- Pour chaque paroisse, afficher le **nombre de membres de l'Armée du Salut** de la paroisse
  (membres actuellement affectés) et ce que la paroisse **peut payer** : nombre de membres × montant
  mensuel (cotisation attendue par mois), à côté des versements validés et de la part due.
- **Recherche** par nom de paroisse dans cette page.

## 2. Fiche d'un membre ouverte depuis une liste : rubriques

Quand le Bureau national (Secrétaire national, Président…) clique sur le nom d'un membre :

- la page est **subdivisée en rubriques** (onglets) :
  1. **Profil** (la fiche actuelle) ;
  2. **Cotisation mensuelle** (situation : mois payés, retard, versements, reçus) ;
  3. **Participation aux événements** (convocations, session, présence).
- D'autres rubriques pourront s'ajouter plus tard.
- Pour les bureaux (paroisse, circuit, région) : Profil et Cotisation mensuelle seulement (ils ne
  voient pas les événements, décision du 12/11/2026).

## 3. À ne pas changer

- Les libellés « Membres » et « Listes » du menu restent comme ils sont pour le moment.
