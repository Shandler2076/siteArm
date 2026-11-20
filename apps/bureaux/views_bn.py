import datetime
from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from apps.bureaux.models import Fonction, Niveau
from apps.bureaux.perimetre import MODELES, Unite
from apps.bureaux.services import InstallationRefusee, _mandats_de_l_unite
from apps.comptes.models import normaliser_identifiant
from apps.membres.models import Membre


def bn_requis(vue):
    @wraps(vue)
    @login_required
    def enveloppe(request, *args, **kwargs):
        # Mandat national de gestion (via MandatBackend) ou autorisation de transition.
        if not request.user.has_perm("membres.gerer_membres"):
            raise PermissionDenied
        return vue(request, *args, **kwargs)

    return enveloppe


def direction_requise(vue):
    """Président et Secrétaire national seulement (en dur, décision du 19/11/2026)."""

    @wraps(vue)
    @login_required
    def enveloppe(request, *args, **kwargs):
        if not request.user.has_perm("bureaux.installer"):
            raise PermissionDenied
        return vue(request, *args, **kwargs)

    return enveloppe


def permission_requise(perm):
    def decorateur(vue):
        @wraps(vue)
        @login_required
        def enveloppe(request, *args, **kwargs):
            if not request.user.has_perm(perm):
                raise PermissionDenied
            return vue(request, *args, **kwargs)

        return enveloppe

    return decorateur


def _verifier_installation(unite, titulaires, date_debut):
    from apps.bureaux.services import _verifier_titulaire

    if not titulaires:
        raise InstallationRefusee("Indiquez au moins un titulaire.")
    for fonction, membre in titulaires.items():
        _verifier_titulaire(unite, fonction, membre)


def _unite(niveau, ident):
    if niveau == Niveau.NATIONAL:
        return Unite(Niveau.NATIONAL, None)
    if niveau in MODELES and str(ident or "").isdigit():
        objet = MODELES[niveau].objects.filter(pk=int(ident), active=True).first()
        if objet:
            return Unite(niveau, objet)
    return None


@direction_requise
def installer(request):
    source = request.POST if request.method == "POST" else request.GET
    niveau = source.get("niveau", "")
    unite = _unite(niveau, source.get("unite"))
    contexte = {"niveaux": Niveau.choices, "niveau": niveau, "unite": unite, "erreurs": []}
    if niveau in MODELES and unite is None:
        contexte["choix_unites"] = MODELES[niveau].objects.filter(active=True).order_by("nom")
    if unite is None:
        return render(request, "bureaux/bn_installer.html", contexte)

    fonctions = list(Fonction.objects.filter(niveau=unite.niveau).order_by("ordre"))
    actuels = {
        m.fonction_id: m for m in _mandats_de_l_unite(unite).en_cours().select_related("membre")
    }
    if request.method == "POST":
        saisies = {f.pk: (source.get(f"fonction_{f.pk}") or "").strip() for f in fonctions}
    else:
        # Préremplies avec les titulaires actuels (20/11/2026) : vider une case = retirer.
        saisies = {
            f.pk: actuels[f.pk].membre.matricule if f.pk in actuels else "" for f in fonctions
        }
    contexte["bureau_en_place"] = bool(actuels)
    contexte.update(
        fonctions=[(f, actuels.get(f.pk), saisies[f.pk]) for f in fonctions],
        date_debut=source.get("date_debut", ""),
    )
    if request.method == "POST":
        try:
            date_debut = datetime.date.fromisoformat(source.get("date_debut", ""))
        except ValueError:
            contexte["erreurs"].append("Indiquez une date de début valide.")
            date_debut = None
        titulaires = {}
        for f in fonctions:
            if not saisies[f.pk]:
                continue
            matricule = normaliser_identifiant(saisies[f.pk])
            membre = Membre.objects.filter(matricule=matricule).first()
            if membre is None:
                contexte["erreurs"].append(f"Matricule inconnu : {matricule}")
            else:
                titulaires[f] = membre
        if not contexte["erreurs"]:
            direction = [f for f in fonctions if f.nom in ("Président", "Secrétaire national")]
            if (
                unite.niveau == Niveau.NATIONAL
                and not any(saisies[f.pk] for f in direction)
                and any(f.pk in actuels for f in direction)
            ):
                garde = ", ".join(
                    f"{actuels[f.pk].membre.matricule} ({f.nom})"
                    for f in direction
                    if f.pk in actuels
                )
                contexte["erreurs"].append(
                    "Les cases Président et Secrétaire national sont vides : le bureau en place "
                    f"serait retiré ({garde}). Retapez leur matricule pour garder le bureau, ou, "
                    "pour ajouter une seule personne, utilisez « Pourvoir un poste vacant »."
                )
                return render(request, "bureaux/bn_installer.html", contexte)
            try:
                # Vérifié tout de suite (zone, statut…), même si la validation vient après.
                _verifier_installation(unite, titulaires, date_debut)
                appliquer_ou_demander(
                    request,
                    "installer",
                    {
                        "unite": unite.cle,
                        "titulaires": {str(f.pk): m.matricule for f, m in titulaires.items()},
                        "date_debut": date_debut.isoformat(),
                    },
                    f"Installer le bureau — {unite.libelle} — au {date_debut:%d/%m/%Y} "
                    f"({len(titulaires)} poste(s))",
                    succes=f"Bureau installé : {len(titulaires)} mandat(s).",
                )
            except InstallationRefusee as e:
                contexte["erreurs"].append(str(e))
            else:
                params = f"?niveau={unite.niveau}" + (
                    f"&unite={unite.objet.pk}" if unite.objet else ""
                )
                return redirect(reverse("bureaux:bn_installer") + params)
    return render(request, "bureaux/bn_installer.html", contexte)


@direction_requise
def fonctions(request):
    """Cases de droits par fonction. Les pouvoirs du Président et du Secrétaire national
    (bureaux, droits, sanctions, enregistrement) sont en dur : aucune case ne les donne."""
    from apps.bureaux.perimetre import DROITS_PAR_CASE

    if request.method == "POST":
        f = get_object_or_404(Fonction, pk=request.POST.get("fonction"))
        case = request.POST.get("case", "droit_gerer")
        permises = DROITS_PAR_CASE if f.niveau == Niveau.NATIONAL else {"droit_gerer": None}
        if case in permises:
            valeur = request.POST.get("valeur") == "on"
            libelle = Fonction._meta.get_field(case).verbose_name
            etat = "cocher" if valeur else "décocher"
            appliquer_ou_demander(
                request,
                "droits",
                {"fonction": f.pk, "case": case, "valeur": valeur},
                f"Droits : {etat} « {libelle} » pour la fonction {f.nom}",
                succes=f"« {f.nom} » : case « {libelle} » {'cochée' if valeur else 'décochée'}.",
            )
        return redirect("bureaux:bn_fonctions")
    cases_nationales = [
        (case, Fonction._meta.get_field(case).verbose_name) for case in DROITS_PAR_CASE
    ]
    par_niveau = [
        (valeur, libelle, Fonction.objects.filter(niveau=valeur).order_by("ordre"))
        for valeur, libelle in Niveau.choices
    ]
    return render(
        request,
        "bureaux/bn_fonctions.html",
        {"par_niveau": par_niveau, "cases_nationales": cases_nationales},
    )


@bn_requis
def echeances(request):
    """Échéances par bureau (décision du 19/11/2026) : un bureau, pas une personne."""
    from django.utils import timezone

    from apps.bureaux.services import bureaux_a_echeance

    j = timezone.localdate()
    lignes = [
        {"unite": unite, "fin": fin, "jours": (fin - j).days, "echu": fin <= j, "nombre": len(m)}
        for unite, fin, m in bureaux_a_echeance(j)
    ]
    return render(request, "bureaux/bn_echeances.html", {"lignes": lignes})


def _bureaux_installes(jour=None) -> dict:
    """{clé d'unité : mandats en cours} pour tous les bureaux installés, en une requête."""
    from apps.bureaux.models import Mandat

    installes: dict = {}
    for m in (
        Mandat.objects.en_cours(jour)
        .select_related("fonction", "membre")
        .order_by("fonction__ordre")
    ):
        niveau = m.fonction.niveau
        cle = "national" if niveau == Niveau.NATIONAL else f"{niveau}-{getattr(m, niveau + '_id')}"
        installes.setdefault(cle, []).append(m)
    return installes


@bn_requis
def bureaux_en_place(request):
    """Tableaux par région : circuits et paroisses, installés ou non (décision du 19/11/2026)."""
    from apps.organisation.models import Circuit, Paroisse, Region

    installes = _bureaux_installes()
    paroisses: dict = {}
    for p in Paroisse.objects.filter(active=True).order_by("nom"):
        paroisses.setdefault(p.circuit_id, []).append(
            {"objet": p, "cle": f"paroisse-{p.pk}", "installe": f"paroisse-{p.pk}" in installes}
        )
    circuits: dict = {}
    for c in Circuit.objects.filter(active=True).order_by("nom"):
        circuits.setdefault(c.region_id, []).append(
            {
                "objet": c,
                "cle": f"circuit-{c.pk}",
                "installe": f"circuit-{c.pk}" in installes,
                "paroisses": paroisses.get(c.pk, []),
            }
        )
    regions = []
    for r in Region.objects.filter(active=True).order_by("code"):
        lignes = circuits.get(r.pk, [])
        toutes = [p for c in lignes for p in c["paroisses"]]
        regions.append(
            {
                "objet": r,
                "cle": f"region-{r.pk}",
                "installe": f"region-{r.pk}" in installes,
                "circuits": lignes,
                "nb_paroisses": len(toutes),
                "nb_installees": sum(1 for p in toutes if p["installe"]),
            }
        )
    return render(
        request,
        "bureaux/bn_bureaux.html",
        {"regions": regions, "national_installe": "national" in installes},
    )


@bn_requis
def bureau_en_place(request, cle):
    """Composition d'un bureau installé : matricule, noms, postes."""
    from django.http import Http404

    from apps.bureaux.perimetre import unite_par_cle

    unite = unite_par_cle(cle)
    if unite is None:
        raise Http404
    mandats = _bureaux_installes().get(unite.cle, [])
    return render(request, "bureaux/bn_bureau.html", {"unite": unite, "mandats": mandats})


def _matricule_membre(saisie):
    if not (saisie or "").strip():
        return None, ""
    matricule = normaliser_identifiant(saisie)
    membre = Membre.objects.filter(matricule=matricule).first()
    return membre, ("" if membre else f"Matricule inconnu : {matricule}")


def _date_saisie(valeur):
    try:
        return datetime.date.fromisoformat(valeur or "")
    except ValueError:
        return None


@direction_requise
def remplacer(request, cle, pk):
    """Remplacer UN titulaire (ou le retirer : poste vacant) ; les autres ne bougent pas."""
    from django.http import Http404
    from django.utils import timezone

    from apps.bureaux.perimetre import unite_par_cle
    from apps.bureaux.services import MOTIFS_DEPART, _verifier_titulaire

    unite = unite_par_cle(cle)
    if unite is None:
        raise Http404
    mandat = get_object_or_404(
        _mandats_de_l_unite(unite).select_related("membre", "fonction"), pk=pk
    )
    erreurs = []
    if request.method == "POST":
        date = _date_saisie(request.POST.get("date"))
        remplacant, erreur = _matricule_membre(request.POST.get("matricule"))
        if date is None:
            erreurs.append("Indiquez la date de départ.")
        if erreur:
            erreurs.append(erreur)
        if not erreurs:
            motif = request.POST.get("motif", "")
            try:
                # « incoherent » est réservé à la page « Mandats à corriger ».
                if motif not in MOTIFS_DEPART or motif == "incoherent":
                    raise InstallationRefusee("Choisissez le motif du départ.")
                if remplacant is not None:
                    _verifier_titulaire(unite, mandat.fonction, remplacant)
                suite = f", remplacé(e) par {remplacant.nom_complet}" if remplacant else ""
                appliquer_ou_demander(
                    request,
                    "remplacer",
                    {
                        "mandat": mandat.pk,
                        "date": date.isoformat(),
                        "motif": motif,
                        "remplacant": remplacant.matricule if remplacant else "",
                    },
                    f"Fin du mandat de {mandat.fonction.nom} de {mandat.membre.nom_complet} "
                    f"({unite.libelle}) au {date:%d/%m/%Y}{suite}",
                    succes="Titulaire remplacé." if remplacant else "Mandat fermé : poste vacant.",
                )
            except InstallationRefusee as e:
                erreurs.append(str(e))
            else:
                return redirect("bureaux:bn_bureau", cle=unite.cle)
    return render(
        request,
        "bureaux/bn_remplacer.html",
        {
            "unite": unite,
            "mandat": mandat,
            "motifs": [(k, v) for k, v in MOTIFS_DEPART.items() if k != "incoherent"],
            "erreurs": erreurs,
            "aujourdhui": timezone.localdate().isoformat(),
            "saisie": request.POST,
        },
    )


@direction_requise
def pourvoir(request, cle):
    """Nommer UNE personne à un poste vacant ; elle termine le mandat en cours du bureau."""
    from django.http import Http404
    from django.utils import timezone

    from apps.bureaux.perimetre import unite_par_cle
    from apps.bureaux.services import _verifier_titulaire

    unite = unite_par_cle(cle)
    if unite is None:
        raise Http404
    occupes = set(_mandats_de_l_unite(unite).en_cours().values_list("fonction_id", flat=True))
    vacants = [
        f
        for f in Fonction.objects.filter(niveau=unite.niveau).order_by("ordre")
        if f.pk not in occupes
    ]
    erreurs = []
    if request.method == "POST":
        fonction = next((f for f in vacants if str(f.pk) == request.POST.get("fonction")), None)
        date = _date_saisie(request.POST.get("date"))
        membre, erreur = _matricule_membre(request.POST.get("matricule"))
        if fonction is None:
            erreurs.append("Choisissez un poste vacant.")
        if date is None:
            erreurs.append("Indiquez la date de début.")
        if membre is None:
            erreurs.append(erreur or "Indiquez le matricule de la personne nommée.")
        if not erreurs:
            try:
                _verifier_titulaire(unite, fonction, membre)
                appliquer_ou_demander(
                    request,
                    "pourvoir",
                    {
                        "unite": unite.cle,
                        "fonction": fonction.pk,
                        "membre": membre.matricule,
                        "date_debut": date.isoformat(),
                    },
                    f"Nommer {membre.nom_complet} {fonction.nom} ({unite.libelle}) au "
                    f"{date:%d/%m/%Y}",
                    succes=f"{membre.nom_complet} est nommé(e) {fonction.nom}.",
                )
            except InstallationRefusee as e:
                erreurs.append(str(e))
            else:
                return redirect("bureaux:bn_bureau", cle=unite.cle)
    return render(
        request,
        "bureaux/bn_pourvoir.html",
        {
            "unite": unite,
            "vacants": vacants,
            "erreurs": erreurs,
            "aujourdhui": timezone.localdate().isoformat(),
            "saisie": request.POST,
        },
    )


@direction_requise
def mandats_a_corriger(request):
    """Mandats enregistrés avant le contrôle de zone : titulaire hors de sa zone ou plus actif."""
    from apps.bureaux.services import mandats_incoherents

    return render(request, "bureaux/bn_mandats_a_corriger.html", {"lignes": mandats_incoherents()})


@direction_requise
def fermer_mandat_incoherent(request, pk):
    from django.http import HttpResponseNotAllowed
    from django.utils import timezone

    from apps.bureaux.models import Mandat
    from apps.bureaux.perimetre import Unite as _Unite
    from apps.bureaux.services import raison_hors_zone
    from apps.membres.models import Statut

    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    mandat = (
        Mandat.objects.filter(pk=pk)
        .select_related("fonction", "membre", "paroisse", "circuit", "region")
        .first()
    )
    a_corriger = mandat is not None and (
        (mandat.date_fin is None or mandat.date_fin > timezone.localdate())
        and (
            mandat.membre.statut != Statut.ACTIF
            or raison_hors_zone(_Unite(mandat.fonction.niveau, mandat.unite), mandat.membre)
        )
    )
    if not a_corriger:
        messages.error(request, "Ce mandat n'est pas (ou plus) à corriger.")
    else:
        appliquer_ou_demander(
            request,
            "remplacer",
            {
                "mandat": mandat.pk,
                "date": timezone.localdate().isoformat(),
                "motif": "incoherent",
                "remplacant": "",
            },
            f"Fermer le mandat hors zone de {mandat.membre.nom_complet} ({mandat.fonction.nom})",
            succes=f"Mandat de {mandat.membre.nom_complet} fermé.",
        )
    return redirect("bureaux:bn_mandats_a_corriger")


# --- Deux clés et délégation (19/11/2026) ---------------------------------------------------
def appliquer_ou_demander(request, action, donnees, resume, *, succes):
    """Applique l'action (Président, compte technique) ou crée la demande de validation
    (Secrétaire national). Renvoie True si c'est fait ou demandé ; lève les erreurs métier."""
    from apps.bureaux.deux_cles import soumettre_ou_executer

    demande, _ = soumettre_ou_executer(request.user, action, donnees, resume)
    if demande is not None:
        messages.success(
            request,
            f"{resume} : en attente de validation du Président (demande n° {demande.pk}).",
        )
    else:
        messages.success(request, succes)
    return True


@login_required
def validations(request):
    from apps.bureaux import deux_cles as dc
    from apps.bureaux.models import DemandeValidation

    if not dc.peut_voir_les_demandes(request.user):
        raise PermissionDenied
    dc.expirer_demandes()
    attente = list(
        DemandeValidation.objects.filter(etat=DemandeValidation.Etat.ATTENTE).select_related(
            "preparee_par"
        )
    )
    for d in attente:
        d.ma_qualite = dc.qualite_pour_valider(request.user, d)
        d.mienne = d.preparee_par_id == request.user.pk
    traitees = DemandeValidation.objects.exclude(
        etat=DemandeValidation.Etat.ATTENTE
    ).select_related("preparee_par", "decidee_par")[:50]
    return render(
        request, "bureaux/bn_validations.html", {"attente": attente, "traitees": traitees}
    )


@login_required
def decider_validation(request, pk, decision):
    from django.http import HttpResponseNotAllowed

    from apps.bureaux import deux_cles as dc
    from apps.bureaux.models import DemandeValidation

    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    demande = get_object_or_404(DemandeValidation, pk=pk)
    try:
        if decision == "valider":
            d = dc.valider(demande, par=request.user)
            if d.etat == DemandeValidation.Etat.VALIDEE:
                messages.success(request, f"Validé et appliqué : {d.resume}")
            else:
                messages.error(request, f"Impossible à appliquer : {d.motif}")
        elif decision == "refuser":
            dc.refuser(demande, par=request.user, motif=request.POST.get("motif", ""))
            messages.success(request, "Demande refusée.")
        elif decision == "annuler":
            dc.annuler(demande, par=request.user)
            messages.success(request, "Demande annulée.")
        else:
            raise PermissionDenied
    except dc.DeuxClesRefusee as e:
        messages.error(request, str(e))
    return redirect("bureaux:bn_validations")


@login_required
def delegations(request):
    """Le Président délègue une validation précise, à une personne, pour une durée limitée."""
    import datetime as _dt

    from django.utils import timezone

    from apps.bureaux import deux_cles as dc
    from apps.bureaux.models import Delegation

    if not dc._a_la_fonction(request.user, "Président"):
        raise PermissionDenied
    if request.method == "POST":
        try:
            if request.POST.get("retirer"):
                d = get_object_or_404(Delegation, pk=request.POST.get("retirer"))
                dc.retirer_delegation(d, par=request.user)
                messages.success(request, "Délégation retirée.")
            else:
                membre, erreur = _matricule_membre(request.POST.get("delegataire"))
                if membre is None or membre.compte is None:
                    raise dc.DeuxClesRefusee(erreur or "Indiquez le matricule du délégataire.")
                heures = int(request.POST.get("heures") or 0)
                dc.deleguer(
                    president=request.user,
                    delegataire=membre.compte,
                    objet=request.POST.get("objet", ""),
                    fin=timezone.now() + _dt.timedelta(hours=heures),
                )
                messages.success(request, f"Délégation donnée à {membre.nom_complet}.")
        except (dc.DeuxClesRefusee, ValueError) as e:
            messages.error(request, str(e) or "Durée invalide.")
        return redirect("bureaux:bn_delegations")
    return render(
        request,
        "bureaux/bn_delegations.html",
        {
            "delegations": Delegation.objects.filter(delegant=request.user).select_related(
                "delegataire"
            )[:30],
            "objets": Delegation.Objet.choices,
            "maintenant": timezone.now(),
        },
    )
