"""Pages des cotisations : grille de la paroisse, validation du circuit, parts reçues.

Toutes les pages passent par le gardien des périmètres (`unite_cotisations_depuis_cle`).
"""

import datetime

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from apps.bureaux.models import Niveau
from apps.bureaux.perimetre import (
    Unite,
    membres_visibles,
    unite_cotisations_depuis_cle,
    unites_cotisations,
)
from apps.cotisations.forms import AnnulationForm, VersementForm
from apps.cotisations.models import (
    EtatVersement,
    NiveauPart,
    ParametresCotisations,
    PartRecue,
    Versement,
    premier_du_mois,
)
from apps.cotisations.regles import situations
from apps.cotisations.services import (
    MOIS,
    CotisationRefusee,
    annuler,
    marquer_part_recue,
    part_due,
    refuser,
    saisir_collecte,
    saisir_versement,
    valider,
)
from apps.organisation.models import Paroisse


def aujourdhui() -> datetime.date:
    return timezone.localdate()


def _unite(request, cle, niveaux=None) -> Unite:
    unite = unite_cotisations_depuis_cle(request.user, cle)
    if niveaux and unite.niveau not in niveaux:
        raise Http404
    return unite


def _annee(request) -> int:
    try:
        return int(request.GET.get("annee", ""))
    except ValueError:
        return aujourdhui().year


@login_required
def grille(request, cle):
    """Paroisse : grille membres × mois de l'année, collecte (cases à cocher)."""
    unite = _unite(request, cle, {Niveau.PAROISSE})
    jour = aujourdhui()
    annee = _annee(request)
    membres = list(membres_visibles(unite).order_by("nom", "prenoms"))
    if request.method == "POST":
        coches = {}
        for m in membres:
            valeurs = request.POST.getlist(f"c-{m.pk}")
            mois = []
            for v in valeurs:
                try:
                    mois.append(datetime.date.fromisoformat(v))
                except ValueError:
                    continue
            if mois:
                coches[m.pk] = mois
        try:
            date_versement = datetime.date.fromisoformat(request.POST.get("date_versement", ""))
        except ValueError:
            date_versement = jour
        try:
            faits = saisir_collecte(
                unite.objet, coches=coches, date_versement=date_versement, par=request.user
            )
        except CotisationRefusee as e:
            messages.error(request, str(e))
        else:
            total = sum(v.montant for v in faits)
            messages.success(
                request,
                f"{len(faits)} versement(s) enregistré(s), {total} F : en attente de validation "
                "par le circuit.",
            )
            return redirect(request.get_full_path())
    sit = situations(membres_visibles(unite), premier_du_mois(jour))
    mois_annee = [datetime.date(annee, i, 1) for i in range(1, 13)]
    fin_payable = premier_du_mois(jour).replace(month=12)
    lignes = []
    for m in membres:
        s = sit[m.pk]
        debut = s.dus[0] if s.dus else None
        cases = []
        for mo in mois_annee:
            if mo in s.payes:
                etat = "paye"
            elif mo in s.en_attente:
                etat = "attente"
            elif mo in s.dus:
                etat = "du"
            elif debut and debut <= mo <= fin_payable:
                etat = "avance"  # mois futur de l'année : paiement d'avance possible
            else:
                etat = "non_du"
            cases.append({"mois": mo, "etat": etat})
        lignes.append({"membre": m, "situation": s, "cases": cases})
    return render(
        request,
        "cotisations/grille.html",
        {
            "unite": unite,
            "annee": annee,
            "noms_mois": [x.capitalize() for x in MOIS],
            "lignes": lignes,
            "ouvert": ParametresCotisations.courant().mois_depart is not None,
            "jour": jour,
            "en_attente": Versement.objects.filter(
                paroisse=unite.objet, etat=EtatVersement.EN_ATTENTE
            ).select_related("membre"),
        },
    )


@login_required
def versement(request, cle):
    """Paroisse : un versement (montant réparti sur les mois les plus anciens)."""
    unite = _unite(request, cle, {Niveau.PAROISSE})
    form = VersementForm(request.POST or None, membres=membres_visibles(unite).order_by("nom"))
    if request.method == "POST" and form.is_valid():
        d = form.cleaned_data
        try:
            v = saisir_versement(
                d["membre"],
                montant=d["montant"],
                date_versement=d["date_versement"],
                par=request.user,
            )
        except CotisationRefusee as e:
            form.add_error(None, str(e))
        else:
            messages.success(
                request,
                f"Versement de {v.montant} F enregistré : en attente de validation par le circuit.",
            )
            return redirect("cotisations:grille", cle=cle)
    return render(request, "cotisations/versement.html", {"unite": unite, "form": form})


@login_required
def a_valider(request, cle):
    """Circuit : versements de ses paroisses en attente ; valider ou refuser (avec motif)."""
    unite = _unite(request, cle, {Niveau.CIRCUIT})
    attente = (
        Versement.objects.filter(paroisse__circuit=unite.objet, etat=EtatVersement.EN_ATTENTE)
        .select_related("membre", "paroisse")
        .prefetch_related("mois")
        .order_by("paroisse__nom", "date_saisie")
    )
    if request.method == "POST":
        pks = {int(x) for x in request.POST.getlist("versements") if x.isdigit()}
        choisis = [v for v in attente if v.pk in pks]
        action = request.POST.get("action")
        try:
            if not choisis:
                raise CotisationRefusee("Cochez au moins un versement.")
            if action == "valider":
                faits = valider(choisis, par=request.user)
                messages.success(request, f"{len(faits)} versement(s) validé(s).")
            elif action == "refuser":
                motif = request.POST.get("motif", "")
                if not motif.strip():
                    raise CotisationRefusee("Le motif du refus est obligatoire.")
                for v in choisis:
                    refuser(v, motif=motif, par=request.user)
                messages.success(request, f"{len(choisis)} versement(s) refusé(s).")
            else:
                raise CotisationRefusee("Action inconnue.")
        except CotisationRefusee as e:
            messages.error(request, str(e))
        else:
            return redirect(request.path)
    return render(request, "cotisations/a_valider.html", {"unite": unite, "attente": attente})


def _paroisses(unite: Unite):
    qs = Paroisse.objects.select_related("circuit__region").order_by("nom")
    if unite.niveau == Niveau.CIRCUIT:
        return qs.filter(circuit=unite.objet)
    if unite.niveau == Niveau.REGION:
        return qs.filter(circuit__region=unite.objet)
    return qs


@login_required
def parts(request, cle):
    """Circuit, région, national : part due par paroisse et par mois de validation ; « Reçue »."""
    unite = _unite(request, cle, {Niveau.CIRCUIT, Niveau.REGION, Niveau.NATIONAL})
    niveau = {
        Niveau.CIRCUIT: NiveauPart.CIRCUIT,
        Niveau.REGION: NiveauPart.REGION,
        Niveau.NATIONAL: NiveauPart.NATIONAL,
    }[unite.niveau]
    paroisses = _paroisses(unite)
    if request.method == "POST":
        paroisse = get_object_or_404(paroisses, pk=request.POST.get("paroisse"))
        try:
            mois = datetime.date.fromisoformat(request.POST.get("mois", ""))
            marquer_part_recue(
                niveau=niveau, paroisse=paroisse, mois_validation=mois, par=request.user
            )
        except (ValueError, CotisationRefusee) as e:
            messages.error(
                request, str(e) if isinstance(e, CotisationRefusee) else "Mois invalide."
            )
        else:
            messages.success(request, f"Part de la paroisse {paroisse.nom} marquée comme reçue.")
            return redirect(request.get_full_path())
    # Couples (paroisse, mois de validation) ayant des versements validés, du plus récent.
    couples = set()
    for paroisse_id, date_validation in Versement.objects.filter(
        paroisse__in=paroisses, etat=EtatVersement.VALIDE
    ).values_list("paroisse_id", "date_validation"):
        couples.add((paroisse_id, premier_du_mois(timezone.localdate(date_validation))))
    par_pk = {p.pk: p for p in paroisses}
    recues = {
        (p.paroisse_id, p.mois_validation): p
        for p in PartRecue.objects.filter(niveau=niveau, paroisse__in=paroisses)
    }
    lignes = []
    for paroisse_id, mo in sorted(couples, key=lambda c: (-c[1].toordinal(), par_pk[c[0]].nom)):
        montant = part_due(niveau, par_pk[paroisse_id], mo)
        if montant:
            lignes.append(
                {
                    "paroisse": par_pk[paroisse_id],
                    "mois": mo,
                    "montant": montant,
                    "recue": recues.get((paroisse_id, mo)),
                }
            )
    return render(
        request,
        "cotisations/parts.html",
        {"unite": unite, "lignes": lignes, "niveau": NiveauPart(niveau).label},
    )


@login_required
def annuler_versement(request, pk):
    """Paroisse : versement en attente ; Bureau national : versement validé."""
    v = get_object_or_404(Versement.objects.select_related("membre", "paroisse"), pk=pk)
    unites = unites_cotisations(request.user)
    est_national = Unite(Niveau.NATIONAL, None) in unites
    if v.etat == EtatVersement.EN_ATTENTE:
        autorise = est_national or Unite(Niveau.PAROISSE, v.paroisse) in unites
    elif v.etat == EtatVersement.VALIDE:
        autorise = est_national
    else:
        autorise = False
    if not autorise:
        raise Http404
    form = AnnulationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            annuler(v, motif=form.cleaned_data["motif"], par=request.user)
        except CotisationRefusee as e:
            form.add_error(None, str(e))
        else:
            messages.success(request, "Versement annulé.")
            if Unite(Niveau.PAROISSE, v.paroisse) in unites:
                return redirect("cotisations:grille", cle=f"paroisse-{v.paroisse_id}")
            return redirect("cotisations:accueil", cle="national")
    return render(request, "cotisations/annuler.html", {"versement": v, "form": form})


def _niveau_part(unite: Unite) -> str:
    return {
        Niveau.PAROISSE: "paroisse",
        Niveau.CIRCUIT: NiveauPart.CIRCUIT,
        Niveau.REGION: NiveauPart.REGION,
        Niveau.NATIONAL: NiveauPart.NATIONAL,
    }[unite.niveau]


def tableau_de_bord(unite: Unite, jour: datetime.date) -> dict:
    mois = premier_du_mois(jour)
    sit = situations(membres_visibles(unite), mois).values()
    a_jour = sum(1 for s in sit if s.a_jour)
    paroisses = (
        Paroisse.objects.filter(pk=unite.objet.pk)
        if unite.niveau == Niveau.PAROISSE
        else _paroisses(unite)
    )
    versements = Versement.objects.filter(paroisse__in=paroisses)
    valides = versements.filter(
        etat=EtatVersement.VALIDE, date_validation__year=mois.year
    ).values_list("montant", "parts")
    niveau = _niveau_part(unite)
    recue = None
    if unite.niveau != Niveau.PAROISSE:
        recue = sum(
            PartRecue.objects.filter(
                niveau=niveau, paroisse__in=paroisses, mois_validation__year=mois.year
            ).values_list("montant", flat=True)
        )
    return {
        "annee": mois.year,
        "a_jour": a_jour,
        "en_retard": len(sit) - a_jour,
        "reste_du": sum(s.reste_du for s in sit),
        "valide": sum(m for m, _p in valides),
        "en_attente": sum(
            versements.filter(etat=EtatVersement.EN_ATTENTE).values_list("montant", flat=True)
        ),
        "part": sum(int(p.get(niveau, 0)) for _m, p in valides),
        "part_recue": recue,
        "a_valider": versements.filter(etat=EtatVersement.EN_ATTENTE).count()
        if unite.niveau == Niveau.CIRCUIT
        else None,
    }


@login_required
def accueil(request, cle):
    """Tableau de bord des cotisations d'une unité."""
    unite = _unite(request, cle)
    return render(
        request,
        "cotisations/accueil.html",
        {"unite": unite, "t": tableau_de_bord(unite, aujourdhui())},
    )


def _pdf(contenu: bytes, nom: str):
    from django.http import HttpResponse

    r = HttpResponse(contenu, content_type="application/pdf")
    r["Content-Disposition"] = f'inline; filename="{nom}"'
    r["Cache-Control"] = "private, no-store"
    return r


def _membre_connecte(request):
    from apps.membres.models import Membre

    try:
        return request.user.membre
    except Membre.DoesNotExist as e:
        raise Http404 from e


@login_required
def mes_cotisations(request):
    from apps.cotisations.regles import situation

    membre = _membre_connecte(request)
    jour = aujourdhui()
    s = situation(membre, premier_du_mois(jour))
    annee = jour.year
    cases = []
    for i, nom in enumerate(MOIS):
        mo = datetime.date(annee, i + 1, 1)
        if mo in s.payes:
            etat = "paye"
        elif mo in s.en_attente:
            etat = "attente"
        elif mo in s.dus:
            etat = "du"
        else:
            etat = "non_du"
        cases.append({"nom": nom.capitalize(), "etat": etat})
    return render(
        request,
        "cotisations/mes_cotisations.html",
        {
            "membre": membre,
            "s": s,
            "cases": cases,
            "annee": annee,
            "mois": premier_du_mois(jour),
            "versements": membre.versements.exclude(etat=EtatVersement.ANNULE).prefetch_related(
                "mois"
            ),
        },
    )


@login_required
def mon_etat_pdf(request):
    from apps.cotisations.pdf import etat_cotisations_pdf

    membre = _membre_connecte(request)
    contenu = etat_cotisations_pdf(membre, premier_du_mois(aujourdhui()))
    return _pdf(contenu, f"cotisations-{membre.matricule}.pdf")


@login_required
def etat_membre_pdf(request, matricule):
    from apps.bureaux.perimetre import peut_voir_cotisations_de
    from apps.cotisations.pdf import etat_cotisations_pdf
    from apps.membres.models import Membre

    membre = get_object_or_404(Membre, matricule=matricule)
    if not peut_voir_cotisations_de(request.user, membre):
        raise Http404
    contenu = etat_cotisations_pdf(membre, premier_du_mois(aujourdhui()))
    return _pdf(contenu, f"cotisations-{membre.matricule}.pdf")


@login_required
def recu(request, pk):
    from apps.bureaux.perimetre import peut_voir_cotisations_de
    from apps.cotisations.pdf import recu_pdf

    v = get_object_or_404(
        Versement.objects.select_related("membre", "paroisse"),
        pk=pk,
        etat=EtatVersement.VALIDE,
    )
    if not peut_voir_cotisations_de(request.user, v.membre):
        raise Http404
    return _pdf(recu_pdf(v), f"recu-{v.numero_recu}.pdf")


@login_required
def bn_reglages(request):
    from django.core.exceptions import PermissionDenied

    from apps.cotisations.forms import DepartForm, TarifForm
    from apps.cotisations.models import Tarif, tarif_du
    from apps.cotisations.services import regler

    if not request.user.has_perm("membres.gerer_membres"):
        raise PermissionDenied
    parametres = ParametresCotisations.courant()
    action = request.POST.get("action") if request.method == "POST" else None
    depart = DepartForm(
        request.POST if action == "depart" else None,
        initial={"mois_depart": parametres.mois_depart},
    )
    courant = tarif_du(aujourdhui())
    tarif = TarifForm(
        request.POST if action == "tarif" else None,
        initial={
            "montant": courant.montant,
            "part_paroisse": courant.part_paroisse,
            "part_circuit": courant.part_circuit,
            "part_region": courant.part_region,
            "part_national": courant.part_national,
        },
    )
    formulaire = {"depart": depart, "tarif": tarif}.get(action)
    if formulaire is not None and formulaire.is_valid():
        try:
            if action == "depart":
                regler(par=request.user, mois_depart=formulaire.cleaned_data["mois_depart"])
            else:
                regler(par=request.user, tarif=formulaire.cleaned_data)
        except CotisationRefusee as e:
            formulaire.add_error(None, str(e))
        else:
            messages.success(request, "Réglages des cotisations enregistrés.")
            return redirect(request.path)
    return render(
        request,
        "cotisations/reglages.html",
        {
            "depart": depart,
            "tarif": tarif,
            "parametres": parametres,
            "courant": courant,
            "tarifs": Tarif.objects.order_by("-date_effet"),
        },
    )
