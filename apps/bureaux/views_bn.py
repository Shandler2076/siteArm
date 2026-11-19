import datetime
from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from apps.bureaux.models import Fonction, Niveau
from apps.bureaux.perimetre import MODELES, Unite
from apps.bureaux.services import InstallationRefusee, _mandats_de_l_unite, installer_bureau
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


def _unite(niveau, ident):
    if niveau == Niveau.NATIONAL:
        return Unite(Niveau.NATIONAL, None)
    if niveau in MODELES and str(ident or "").isdigit():
        objet = MODELES[niveau].objects.filter(pk=int(ident), active=True).first()
        if objet:
            return Unite(niveau, objet)
    return None


@bn_requis
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
    saisies = {f.pk: (source.get(f"fonction_{f.pk}") or "").strip() for f in fonctions}
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
            try:
                nouveaux = installer_bureau(
                    unite=unite, titulaires=titulaires, date_debut=date_debut, par=request.user
                )
            except InstallationRefusee as e:
                contexte["erreurs"].append(str(e))
            else:
                messages.success(request, f"Bureau installé : {len(nouveaux)} mandat(s).")
                params = f"?niveau={unite.niveau}" + (
                    f"&unite={unite.objet.pk}" if unite.objet else ""
                )
                return redirect(reverse("bureaux:bn_installer") + params)
    return render(request, "bureaux/bn_installer.html", contexte)


@bn_requis
def fonctions(request):
    if request.method == "POST":
        f = get_object_or_404(Fonction, pk=request.POST.get("fonction"))
        f.droit_gerer = request.POST.get("droit_gerer") == "on"
        f.save(update_fields=["droit_gerer"])
        etat = "peut" if f.droit_gerer else "ne peut plus"
        messages.success(request, f"La fonction « {f.nom} » {etat} gérer le site.")
        return redirect("bureaux:bn_fonctions")
    par_niveau = [
        (libelle, Fonction.objects.filter(niveau=valeur).order_by("ordre"))
        for valeur, libelle in Niveau.choices
    ]
    return render(request, "bureaux/bn_fonctions.html", {"par_niveau": par_niveau})


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


@bn_requis
def remplacer(request, cle, pk):
    """Remplacer UN titulaire (ou le retirer : poste vacant) ; les autres ne bougent pas."""
    from django.http import Http404
    from django.utils import timezone

    from apps.bureaux.perimetre import unite_par_cle
    from apps.bureaux.services import MOTIFS_DEPART, remplacer_titulaire

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
            try:
                remplacer_titulaire(
                    mandat=mandat,
                    date=date,
                    motif=request.POST.get("motif", ""),
                    remplacant=remplacant,
                    par=request.user,
                )
            except InstallationRefusee as e:
                erreurs.append(str(e))
            else:
                messages.success(
                    request,
                    "Titulaire remplacé." if remplacant else "Mandat fermé : le poste est vacant.",
                )
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


@bn_requis
def pourvoir(request, cle):
    """Nommer UNE personne à un poste vacant ; elle termine le mandat en cours du bureau."""
    from django.http import Http404
    from django.utils import timezone

    from apps.bureaux.perimetre import unite_par_cle
    from apps.bureaux.services import pourvoir_poste

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
                pourvoir_poste(
                    unite=unite, fonction=fonction, membre=membre, date_debut=date, par=request.user
                )
            except InstallationRefusee as e:
                erreurs.append(str(e))
            else:
                messages.success(request, f"{membre.nom_complet} est nommé(e) {fonction.nom}.")
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


@bn_requis
def mandats_a_corriger(request):
    """Mandats enregistrés avant le contrôle de zone : titulaire hors de sa zone ou plus actif."""
    from apps.bureaux.services import mandats_incoherents

    return render(request, "bureaux/bn_mandats_a_corriger.html", {"lignes": mandats_incoherents()})


@bn_requis
def fermer_mandat_incoherent(request, pk):
    from django.http import HttpResponseNotAllowed
    from django.utils import timezone

    from apps.bureaux.services import mandats_incoherents, remplacer_titulaire

    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    mandat = next((m for m, _r in mandats_incoherents() if m.pk == pk), None)
    if mandat is None:
        messages.error(request, "Ce mandat n'est pas (ou plus) à corriger.")
    else:
        remplacer_titulaire(
            mandat=mandat,
            date=timezone.localdate(),
            motif="incoherent",
            remplacant=None,
            par=request.user,
        )
        messages.success(request, f"Mandat de {mandat.membre.nom_complet} fermé.")
    return redirect("bureaux:bn_mandats_a_corriger")
