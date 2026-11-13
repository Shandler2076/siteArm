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
    est_bn,
    est_tresorier_national,
    est_validateur_reversements,
    unites_cotisations,
    unites_gerees,
    unites_tresorerie,
    unites_verification,
)

ELIGIBLES = (
    "?envoye=1&statut=actif&eligible=on&colonnes=matricule&colonnes=nom&colonnes=prenoms"
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
        if any(parametres.get(k) != v for k, v in self.requis.items()):
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

    # Gestion des membres
    liens = []
    if national:
        liens.append(
            Lien(
                "Tous les membres",
                reverse("bureaux:membres", args=["national"]),
                prefixes=("/membres/bn/",),
            )
        )
    if gestion_bn:
        liens += [
            Lien("Enregistrer un membre", reverse("membres:bn_enregistrer")),
            Lien("Enregistrer par lots", reverse("lots:liste")),
            Lien("Photos à valider", reverse("membres:bn_photos")),
        ]
    if national:
        liens.append(
            Lien(
                f"Demandes{national_suffixe}",
                reverse("mouvements:demandes", args=["national"]),
            )
        )
    if gestion_bn:
        liens.append(
            Lien(
                "Décisions à prendre",
                reverse("mouvements:bn_decisions"),
                compteur=_nb_decisions(),
            )
        )
    for u in unites:
        liens += [
            Lien(f"Membres{suffixe(u)}", reverse("bureaux:membres", args=[u.cle])),
            Lien(f"Anciens membres{suffixe(u)}", reverse("bureaux:anciens", args=[u.cle])),
            Lien(f"Demandes{suffixe(u)}", reverse("mouvements:demandes", args=[u.cle])),
        ]
    if unites_verification(user):
        liens.append(Lien("Vérifier un membre", reverse("bureaux:verifier")))
    if liens:
        groupes.append(Groupe("Gestion des membres (BN)" if gestion_bn else "Mon bureau", liens))

    # Listes et statistiques, grades
    cles = (["national"] if national else []) + [u.cle for u in unites]
    noms = {"national": national_suffixe} | {u.cle: suffixe(u) for u in unites}
    listes, grades = [], []
    for cle in cles:
        url_listes = reverse("listes:liste", args=[cle])
        listes += [
            Lien(f"Listes{noms[cle]}", url_listes),
            Lien(f"Statistiques{noms[cle]}", reverse("listes:statistiques", args=[cle])),
        ]
        grades.append(
            Lien(
                f"Éligibles au grade suivant{noms[cle]}",
                url_listes + ELIGIBLES,
                requis={"eligible": "on"},
            )
        )
    if gestion_bn:
        listes.append(Lien("Tranches d'âge", reverse("listes:tranches")))
        grades.append(Lien("Promotions en série", reverse("grades:bn_serie")))
    if listes:
        groupes.append(Groupe("Listes et statistiques", listes))
    if grades:
        groupes.append(Groupe("Grades", grades))

    # Cotisations mensuelles
    u_cot = list(unites_cotisations(user))
    cot = []
    for u in u_cot:
        s = f" — {u.libelle}" if len(u_cot) > 1 else ""
        cot.append(Lien(f"Tableau de bord{s}", reverse("cotisations:accueil", args=[u.cle])))
        if u.niveau != Niveau.PAROISSE:
            cot.append(Lien(f"Parts reçues{s}", reverse("cotisations:parts", args=[u.cle])))
    if gestion_bn:
        cot.append(Lien("Réglages", reverse("cotisations:bn_reglages")))
    if cot:
        groupes.append(Groupe("Cotisations mensuelles", cot))

    # Trésorerie (13/11/2026) : espace de chaque bureau, et pages du BN.
    tres = []
    u_tres = unites_tresorerie(user)
    for u, _agit in u_tres:
        s = f" — {u.libelle}" if len(u_tres) > 1 else ""
        tres.append(Lien(f"Trésorerie du bureau{s}", reverse("tresorerie:espace", args=[u.cle])))
    if gestion_bn:
        tres += [
            Lien("Cotisations spéciales", reverse("tresorerie:bn_speciales")),
            Lien("Numéros des trésoriers", reverse("tresorerie:bn_numeros")),
        ]
    if gestion_bn or est_tresorier_national(user) or est_validateur_reversements(user):
        tres.append(Lien("Reversements mensuels", reverse("tresorerie:bn_reversements")))
    if tres:
        groupes.append(Groupe("Trésorerie", tres))

    if gestion_bn:
        groupes += [
            Groupe("Événements", [Lien("Événements nationaux", reverse("evenements:liste"))]),
            Groupe(
                "Bureaux et droits",
                [
                    Lien("Installer un bureau", reverse("bureaux:bn_installer")),
                    Lien("Fonctions et droits", reverse("bureaux:bn_fonctions")),
                    Lien("Mandats à échéance", reverse("bureaux:bn_echeances")),
                ],
            ),
        ]
        controle = [Lien("Journal", reverse("journal:liste"))]
        if user.is_superuser:
            controle.append(Lien("Administration technique", "/gestion/"))
        groupes.append(Groupe("Contrôle", controle))

    _marquer_actif(groupes, request.path, request.GET)
    return groupes


def _mon_espace(user) -> list[Lien]:
    liens = [Lien("Accueil", reverse("accueil"), exact=True)]
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


def _nb_decisions() -> int:
    from apps.mouvements.models import EN_COURS, EtatDemande, Mutation, Signalement

    return (
        Mutation.objects.filter(etat__in=EN_COURS).count()
        + Signalement.objects.filter(etat=EtatDemande.BN).count()
    )


def _marquer_actif(groupes: list[Groupe], chemin: str, parametres) -> None:
    meilleur, choix = 0, None
    for g in groupes:
        for lien in g.liens:
            s = lien.score(chemin, parametres)
            if s > meilleur:
                meilleur, choix = s, (g, lien)
    if choix:
        choix[0].ouvert = True
        choix[1].actif = True
