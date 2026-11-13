# Menu réorganisé, paroisse actuelle à l'inscription, identifiants : plan de réalisation

> Décisions du mainteneur du 13 novembre 2026. Exécution : native, une relecture finale indépendante,
> puis PR vers `main`.

**Goal :**
- un menu clair, sans doublons, où l'on voit tout de suite sur quelle rubrique on se trouve ;
- la paroisse actuelle d'un membre saisie dès son inscription sur le site ;
- les identifiants d'un nouveau membre faciles à retrouver.

## Décisions

1. **Paroisse actuelle** :
   - nouveau champ facultatif « Paroisse actuelle (si différente de la paroisse d'intégration) », dans
     l'enregistrement individuel et dans les lots Excel (colonne facultative « Paroisse actuelle ») ;
   - le membre est considéré dans cette paroisse **à partir de la date d'inscription sur le site**.
     Avant cette date, on reste sur la paroisse d'intégration ; on ne retrace pas les étapes passées ;
   - le suivi des mutations commence ensuite normalement ;
   - le matricule ne change pas : il garde l'année et la région d'intégration.
2. **Menu** du Secrétaire national, chaque fonction une seule fois :
   - MON ESPACE : Accueil, Ma fiche, Ma photo, Mes coordonnées, Mes cotisations, Mes événements,
     Notifications, Protection des données ;
   - GESTION DES MEMBRES (BN) : Tous les membres, Enregistrer un membre, Enregistrer par lots,
     Photos à valider, Demandes, Décisions à prendre ;
   - LISTES ET STATISTIQUES : Listes, Statistiques, Tranches d'âge ;
   - GRADES : Éligibles au grade suivant, Promotions en série ;
   - COTISATIONS MENSUELLES : Tableau de bord, Parts reçues, Réglages ;
   - ÉVÉNEMENTS : Événements nationaux ;
   - BUREAUX ET DROITS : Installer un bureau, Fonctions et droits, Mandats à échéance ;
   - CONTRÔLE : Journal.
   Pour les bureaux de région, de circuit et de paroisse, la même logique s'applique avec seulement
   leurs droits :
   - MON ESPACE ;
   - MON BUREAU (nom de l'unité) : Membres, Anciens membres, Demandes ;
   - LISTES ET STATISTIQUES ;
   - GRADES (Éligibles) ;
   - COTISATIONS MENSUELLES.
   Un responsable de plusieurs unités garde un groupe par unité.
3. **Rubrique choisie bien visible** :
   - fond bleu marine, texte blanc, barre dorée à gauche ;
   - la rubrique reste en évidence sur ses sous-pages (ex. fiche d'un membre ouverte depuis « Tous
     les membres ») ;
   - à l'ouverture de chaque page, le menu se place sur la rubrique choisie, au lieu de remonter
     tout en haut.
4. **Identifiants** :
   - juste après l'enregistrement, la fiche du membre affiche en haut un encadré « Identifiants à
     remettre » avec le bouton « Imprimer la fiche avec identifiants » ;
   - si le membre a un e-mail, il reçoit un message : son compte est créé, son identifiant est son
     matricule, sa paroisse lui remettra son mot de passe provisoire ;
   - le mot de passe n'est **jamais** envoyé par e-mail ni gardé en clair.

## Tâches

1. **Paroisse actuelle** (`apps/membres/forms.py`, `services.py::enregistrer_membre`,
   `apps/lots`, gabarit d'enregistrement) :
   - si la paroisse actuelle est donnée et différente : affectation d'intégration close la veille
     de l'inscription, nouvelle affectation à la date d'inscription avec le motif « Paroisse actuelle
     à l'inscription sur le site » ;
   - les notifications « nouveau membre » partent vers la paroisse actuelle (et son circuit, sa
     région) ;
   - journal.
   - Tests : `test_enregistrer_avec_paroisse_actuelle`, `test_sans_paroisse_actuelle_inchange`,
     `test_lot_colonne_paroisse_actuelle`, `test_paroisse_actuelle_gere_le_membre` (gardien des
     périmètres).
2. **Menu** (`templates/_menu.html`, processeur de contexte, `static/css/site.css`, petit script
   de positionnement) :
   - groupes ci-dessus ;
   - rubrique active par préfixe d'adresse ;
   - défilement automatique vers la rubrique active.
   - Tests : `test_menu_bn_sans_doublon`, `test_menu_rubrique_active_sur_sous_page`,
     `test_menu_bureau_paroisse`.
3. **Identifiants** :
   - encadré après l'enregistrement ;
   - e-mail de bienvenue sans mot de passe.
   - Tests : `test_encadre_identifiants_apres_enregistrement`,
     `test_email_bienvenue_sans_mot_de_passe`.
4. **Documents** :
   - cahier des charges (§ enregistrement, menu) ;
   - guide de maintenance ;
   - récapitulatif ;
   - page « Protection de vos données » (e-mail de bienvenue).
