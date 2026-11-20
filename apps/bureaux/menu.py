"""Menu principal, organisé par thèmes (décision du mainteneur du 13/11/2026).

Chaque fonction n'apparaît qu'une fois. La rubrique de la page ouverte est marquée « active »,
y compris sur ses sous-pages : le lien dont l'adresse est le plus long préfixe de la page gagne.
Les groupes sont repliés, sauf celui de la rubrique active.
Les droits viennent du gardien des périmètres (`perimetre.py`) et de `MandatBackend`.
"""

from dataclasses import dataclass, field

from django.urls import reverse

from apps.bureaux.perimetre import (
    Niveau,
    Unite,
    est_bn,
    est_tresorier_national,
    est_validateur_reversements,
    peut_deposer_signature,
    unites_cotisations,
    unites_courrier,
    unites_gerees,
    unites_tresorerie,
    unites_verification,
)

ELIGIBLES = (
    "?envoye=1&statut=actif&eligible_a=&colonnes=matricule&colonnes=nom&colonnes=prenoms"
    "&colonnes=grade&colonnes=date_grade&colonnes=paroisse"
)


@dataclass
class Lien:
    libelle: str
    url: str
    prefixes: tuple = ()
    exact: bool = False  # actif seulement sur l'adresse exacte (Accueil)
    requis: dict = field(default_factory=dict)  # paramètres d'adresse qui distinguent le lien
    compteur: int = 0
    actif: bool = False

    def score(self, chemin: str, parametres) -> int:
        """Longueur du préfixe reconnu (0 : pas reconnu)."""
        # Valeur None : le paramètre doit seulement être présent (sa valeur varie).
        if any(
            (k not in parametres) if v is None else parametres.get(k) != v
            for k, v in self.requis.items()
        ):
            return 0
        chemin_lien = self.url.split("?", 1)[0]
        if self.exact:
            return len(chemin_lien) if chemin == chemin_lien else 0
        meilleur = 0
        for p in (chemin_lien, *self.prefixes):
            if chemin.startswith(p):
                meilleur = max(meilleur, len(p))
        # Un lien sans paramètre requis cède la place à un lien qui en a (Listes / Éligibles).
        return meilleur * 2 + (1 if self.requis else 0) if meilleur else 0


@dataclass
class Groupe:
    titre: str
    liens: list
    ouvert: bool = False


@dataclass
class SousGroupe:
    """Un bureau dans une rubrique : son nom, et ses liens (dépliés au clic)."""

    titre: str
    liens: list
    ouvert: bool = False
    sous_groupe: bool = True


NOMS_BUREAUX = {
    Niveau.REGION: "Bureau régional de coordination",
    Niveau.CIRCUIT: "Section circuit",
    Niveau.PAROISSE: "Unité paroissiale",
}


def nom_bureau(unite) -> str:
    """« Bureau National de Commandement », « Section circuit — Ekpe A »…"""
    if unite.niveau == Niveau.NATIONAL:
        return "Bureau National de Commandement"
    return f"{NOMS_BUREAUX[unite.niveau]} — {unite.objet.nom}"


def _par_bureau(blocs, avant=(), apres=()) -> list:
    """Un seul bureau : ses liens à plat ; plusieurs : une entrée (dépliable) par bureau."""
    blocs = [(titre, liens) for titre, liens in blocs if liens]
    if len(blocs) == 1:
        milieu = list(blocs[0][1])
    else:
        milieu = [SousGroupe(titre, liens) for titre, liens in blocs]
    return [*avant, *milieu, *apres]


def _liens(groupe):
    """(sous-groupe ou None, lien) pour chaque lien du groupe, sous-groupes compris."""
    for element in groupe.liens:
        if isinstance(element, SousGroupe):
            for lien in element.liens:
                yield element, lien
        else:
            yield None, element


def _membre(user):
    try:
        return user.membre
    except Exception:  # pas de fiche membre (compte technique)
        return None


def construire_menu(request) -> list[Groupe]:
    user = request.user
    if not getattr(user, "is_authenticated", False):
        return []
    gestion_bn = user.has_perm("membres.gerer_membres")
    national = est_bn(user)
    unites = [u for u in unites_gerees(user) if u.niveau != Niveau.NATIONAL]
    # Plusieurs unités (ou le national en plus d'une unité) : chaque lien porte le nom de l'unité.
    plusieurs = len(unites) > 1 or (national and bool(unites))
    national_suffixe = " — national" if national and unites else ""

    def suffixe(unite):
        return f" — {unite.libelle}" if plusieurs else ""

    groupes = [Groupe("Mon espace", _mon_espace(user))]

    # Décision du 19/11/2026 : chaque rubrique est organisée PAR BUREAU. Un seul bureau : liens
    # à plat ; plusieurs : une entrée par bureau (avec son nom), qui se déplie sur ses liens.
    nat = Unite(Niveau.NATIONAL, None)

    # Mon bureau : « Vérifier un membre » d'abord, puis chaque bureau.
    blocs = []
    if national or gestion_bn:
        liens = []
        if national:
            liens.append(
                Lien(
                    "Tous les membres",
                    reverse("bureaux:membres", args=["national"]),
                    prefixes=("/membres/bn/",),
                )
            )
        if user.has_perm("membres.enregistrer"):
            liens += [
                Lien("Enregistrer un membre", reverse("membres:bn_enregistrer")),
                Lien("Enregistrer par lots", reverse("lots:liste")),
            ]
        if gestion_bn:
            liens.append(Lien("Photos à valider", reverse("membres:bn_photos")))
        if national:
            liens.append(Lien("Demandes", reverse("mouvements:demandes", args=["national"])))
        if gestion_bn:
            liens.append(
                Lien(
                    "Décisions à prendre",
                    reverse("mouvements:bn_decisions"),
                    compteur=_nb_decisions(),
                )
            )
        blocs.append((nom_bureau(nat), liens))
    for u in unites:
        blocs.append(
            (
                nom_bureau(u),
                [
                    Lien("Membres", reverse("bureaux:membres", args=[u.cle])),
                    Lien("Anciens membres", reverse("bureaux:anciens", args=[u.cle])),
                    Lien("Demandes", reverse("mouvements:demandes", args=[u.cle])),
                ],
            )
        )
    avant = []
    if unites_verification(user):
        avant.append(Lien("Vérifier un membre", reverse("bureaux:verifier")))
    liens = _par_bureau(blocs, avant=avant)
    if liens:
        groupes.append(Groupe("Mon bureau", liens))

    # Listes et statistiques (par bureau) ; grades : une ligne par niveau (lisible ainsi).
    blocs, grades = [], []
    for u in ([nat] if national else []) + unites:
        bloc = [
            Lien("Listes", reverse("listes:liste", args=[u.cle])),
            Lien("Statistiques", reverse("listes:statistiques", args=[u.cle])),
        ]
        if u.niveau == Niveau.NATIONAL and gestion_bn:
            bloc.append(Lien("Tranches d'âge", reverse("listes:tranches")))
        blocs.append((nom_bureau(u), bloc))
        # Le BN (case « grades ») a sa propre page, avec les sessions de test.
        if not (u.niveau == Niveau.NATIONAL and user.has_perm("grades.gerer")):
            nom = national_suffixe if u.niveau == Niveau.NATIONAL else suffixe(u)
            grades.append(
                Lien(
                    f"Éligibles au grade visé{nom}",
                    reverse("listes:liste", args=[u.cle]) + ELIGIBLES,
                    requis={"eligible_a": None},
                )
            )
    if user.has_perm("grades.gerer"):
        # Grades (13/11/2026) : éligibles au grade visé → test ou examen → promotion ; à part,
        # la promotion spéciale (art. 84) ; et les actes.
        grades = [
            Lien("Éligibles au grade visé", reverse("grades:bn_eligibles")),
            Lien(
                "Promotion après test ou examen",
                reverse("grades:bn_sessions"),
                prefixes=("/grades/bn/serie/",),
            ),
            Lien("Promotions spéciales", reverse("grades:bn_speciales")),
            Lien("Actes de promotion", reverse("grades:bn_actes")),
        ] + grades
    listes = _par_bureau(blocs)
    if listes:
        groupes.append(Groupe("Listes et statistiques", listes))
    if grades:
        groupes.append(Groupe("Grades", grades))

    # Cotisations mensuelles (par bureau)
    blocs = []
    for u in unites_cotisations(user):
        bloc = [Lien("Tableau de bord", reverse("cotisations:accueil", args=[u.cle]))]
        if u.niveau != Niveau.PAROISSE:
            bloc.append(Lien("Parts reçues", reverse("cotisations:parts", args=[u.cle])))
        blocs.append((nom_bureau(u), bloc))
    apres = [Lien("Réglages", reverse("cotisations:bn_reglages"))] if gestion_bn else []
    cot = _par_bureau(blocs, apres=apres)
    if cot:
        groupes.append(Groupe("Cotisations mensuelles", cot))

    # Trésorerie (par bureau), puis les pages nationales.
    blocs = [
        (nom_bureau(u), [Lien("Trésorerie du bureau", reverse("tresorerie:espace", args=[u.cle]))])
        for u, _agit in unites_tresorerie(user)
    ]
    apres = []
    if user.has_perm("tresorerie.creer_speciales"):
        apres.append(Lien("Cotisations spéciales", reverse("tresorerie:bn_speciales")))
    if gestion_bn:
        apres.append(Lien("Numéros des trésoriers", reverse("tresorerie:bn_numeros")))
    if gestion_bn or est_tresorier_national(user) or est_validateur_reversements(user):
        apres.append(Lien("Reversements mensuels", reverse("tresorerie:bn_reversements")))
    tres = _par_bureau(blocs, apres=apres)
    if tres:
        groupes.append(Groupe("Trésorerie", tres))

    if user.has_perm("evenements.gerer"):
        groupes.append(
            Groupe("Événements", [Lien("Événements nationaux", reverse("evenements:liste"))])
        )

    # Courrier et communiqués (par bureau ; décisions des 13, 14 et 16/11/2026).
    blocs = []
    for u in unites_courrier(user):
        blocs.append(
            (
                nom_bureau(u),
                [
                    Lien("Nouveau courrier", reverse("courrier:nouveau", args=[u.cle])),
                    Lien("Courrier reçu", reverse("courrier:recus", args=[u.cle])),
                    Lien(
                        "Courriers envoyés",
                        reverse("courrier:envoyes", args=[u.cle]),
                        prefixes=(f"/courrier/{u.cle}/",),
                    ),
                    Lien(
                        "En correction",
                        reverse("courrier:en_correction", args=[u.cle]),
                        compteur=_nb_courriers(u.cle, "a_corriger"),
                    ),
                    Lien("Courriers abandonnés", reverse("courrier:abandonnes", args=[u.cle])),
                ],
            )
        )
    apres = []
    if peut_deposer_signature(user):
        apres += [
            Lien("Courriers à signer", reverse("courrier:a_signer"), compteur=_nb_a_signer(user)),
            Lien("Ma signature", reverse("courrier:ma_signature")),
        ]
    if gestion_bn:
        apres += [
            Lien("Registre des courriers", reverse("courrier:bn_registre")),
            Lien("Clavier goun", reverse("courrier:bn_clavier")),
        ]
    courrier = _par_bureau(blocs, apres=apres)
    if courrier:
        groupes.append(Groupe("Courrier", courrier))

    bureaux = []
    if user.has_perm("bureaux.installer"):
        bureaux.append(Lien("Installer un bureau", reverse("bureaux:bn_installer")))
    if gestion_bn:
        bureaux.append(
            Lien(
                "Bureaux en place",
                reverse("bureaux:bn_bureaux"),
                prefixes=("/bureau/bn/bureaux/",),
            )
        )
    if user.has_perm("bureaux.installer"):
        bureaux += [
            Lien("Fonctions et droits", reverse("bureaux:bn_fonctions")),
            Lien("Mandats à corriger", reverse("bureaux:bn_mandats_a_corriger")),
        ]
    if gestion_bn:
        bureaux.append(Lien("Mandats à échéance", reverse("bureaux:bn_echeances")))
    from apps.bureaux import deux_cles

    if deux_cles.peut_voir_les_demandes(user):
        bureaux.insert(
            0,
            Lien(
                "Actions à valider",
                reverse("bureaux:bn_validations"),
                compteur=deux_cles.demandes_en_attente().count(),
            ),
        )
    if deux_cles._a_la_fonction(user, "Président"):
        bureaux.append(Lien("Déléguer une validation", reverse("bureaux:bn_delegations")))
    if bureaux:
        groupes.append(Groupe("Bureaux et droits", bureaux))
    controle = []
    if user.has_perm("journal.voir"):
        controle.append(Lien("Journal", reverse("journal:liste")))
    if user.is_superuser:
        controle.append(Lien("Administration technique", "/gestion/"))
    if controle:
        groupes.append(Groupe("Contrôle", controle))

    _marquer_actif(groupes, request.path, request.GET, getattr(request, "rubrique_menu", None))
    return groupes


def _mon_espace(user) -> list[Lien]:
    liens = [Lien("Ma page", reverse("accueil"), exact=True)]
    if _membre(user) is not None:
        liens += [
            Lien("Ma fiche et mon parcours", reverse("membres:ma_fiche")),
            Lien("Ma photo", reverse("membres:ma_photo")),
            Lien("Mes coordonnées", reverse("membres:mes_coordonnees")),
            Lien("Mes cotisations", reverse("cotisations:moi")),
            Lien(
                "Payer (mobile money)", reverse("tresorerie:payer"), prefixes=("/tresorerie/payer",)
            ),
            Lien("Mes événements", reverse("evenements:moi")),
            Lien("Mes courriers", reverse("courrier:moi")),
        ]
    liens += [
        Lien(
            "Notifications",
            reverse("notifications:liste"),
            compteur=user.notifications.filter(lue=False).count(),
        ),
        Lien("Protection de vos données", reverse("protection_donnees")),
    ]
    return liens


def _nb_courriers(cle: str, etat: str) -> int:
    from apps.courrier.models import Courrier

    return Courrier.objects.filter(expediteur_cle=cle, etat=etat).count()


def _nb_a_signer(user) -> int:
    from apps.courrier.services import courriers_a_signer

    return courriers_a_signer(user).count()


def _nb_decisions() -> int:
    from apps.mouvements.models import EN_COURS, EtatDemande, Mutation, Signalement

    return (
        Mutation.objects.filter(etat__in=EN_COURS).count()
        + Signalement.objects.filter(etat=EtatDemande.BN).count()
    )


def _marquer_actif(groupes: list[Groupe], chemin: str, parametres, rubrique=None) -> None:
    """`rubrique` : adresse imposée par la page (ex. un courrier rattaché à « En correction »)."""
    if rubrique:
        for g in groupes:
            for sous, lien in _liens(g):
                if lien.url == rubrique:
                    g.ouvert = lien.actif = True
                    if sous:
                        sous.ouvert = True
                    return
    meilleur, choix = 0, None
    for g in groupes:
        for sous, lien in _liens(g):
            score = lien.score(chemin, parametres)
            if score > meilleur:
                meilleur, choix = score, (g, sous, lien)
    if choix:
        choix[0].ouvert = choix[2].actif = True
        if choix[1]:
            choix[1].ouvert = True
