"""Pages de la trésorerie (décisions du mainteneur du 13/11/2026).

Droits : le gardien des périmètres (`unites_tresorerie`, `est_tresorier_national`,
`est_validateur_reversements`) et `membres.gerer_membres` pour le BN.
"""

import datetime

from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from apps.bureaux.perimetre import (
    Niveau,
    Unite,
    est_tresorier_national,
    est_validateur_reversements,
    peut_agir_tresorerie,
    peut_voir_cotisations_de,
    peut_voir_tresorerie,
)
from apps.membres.models import Membre
from apps.tresorerie import services as s
from apps.tresorerie.models import (
    Contribution,
    CotisationSpeciale,
    EtatPaiement,
    EtatReversement,
    NumeroMobileMoney,
    Paiement,
    PourMembres,
    Reversement,
    TypeMontant,
)


def _bn(user) -> bool:
    return user.has_perm("membres.gerer_membres")


def _membre(user):
    try:
        return user.membre
    except Membre.DoesNotExist:
        return None


def _vers_plateforme(paiement: Paiement):
    """Plateforme simulée (site d'essai) : page de confirmation ; une vraie plateforme redirigera
    vers son propre écran et confirmera par son retour signé."""
    return redirect("tresorerie:paiement", reference=paiement.reference)


def confirmation_reduite(membre) -> str:
    """« Soldat Albert A. — Paroisse de GBOA » : rien de plus (décision du 13/11/2026)."""
    grade = membre.get_grade_display() if membre.grade else "Camarade"
    initiale = (membre.nom or "?")[:1].upper()
    a = membre.affectation_actuelle
    paroisse = f" — {a.paroisse.nom}" if a else ""
    prenom = (membre.prenoms or "").split(" ")[0]
    return f"{grade} {prenom} {initiale}.{paroisse}"


# --- Membre : payer ------------------------------------------------------------------------------


@login_required
def payer(request):
    """Payer ses propres mois de cotisation par mobile money."""
    membre = _membre(request.user)
    if membre is None:
        raise Http404
    if request.method == "POST":
        try:
            p = s.initier_paiement_mensuel(
                request.user, [(membre, _entier(request.POST.get("nombre")))]
            )
        except s.TresorerieRefusee as e:
            messages.error(request, str(e))
            return redirect("tresorerie:payer")
        return _vers_plateforme(p)
    return render(
        request,
        "tresorerie/payer.html",
        {"membre": membre, "speciales": s.speciales_du_membre(membre)},
    )


def _entier(valeur) -> int:
    try:
        return int(valeur)
    except (TypeError, ValueError):
        return 0


@login_required
def payer_pour(request):
    """Payer pour un autre membre (n'importe quel membre peut aider) : matricule, confirmation
    réduite, nombre de mois ou cotisation spéciale."""
    if _membre(request.user) is None and not _bn(request.user):
        raise Http404
    matricule = (request.POST.get("matricule") or request.GET.get("matricule") or "").strip()
    beneficiaire = Membre.objects.filter(matricule=matricule.upper()).first() if matricule else None
    if request.method == "POST" and beneficiaire and request.POST.get("confirmer"):
        try:
            cs_pk = request.POST.get("speciale", "")
            if cs_pk.isdigit():
                cs = get_object_or_404(CotisationSpeciale, pk=int(cs_pk))
                p = s.initier_paiement_special(
                    request.user, cs, _entier(request.POST.get("montant")), membre=beneficiaire
                )
            else:
                p = s.initier_paiement_mensuel(
                    request.user, [(beneficiaire, _entier(request.POST.get("nombre")))]
                )
        except s.TresorerieRefusee as e:
            messages.error(request, str(e))
        else:
            return _vers_plateforme(p)
    speciales = s.speciales_du_membre(beneficiaire) if beneficiaire else []
    return render(
        request,
        "tresorerie/payer_pour.html",
        {
            "matricule": matricule,
            "beneficiaire": beneficiaire,
            "confirmation": confirmation_reduite(beneficiaire) if beneficiaire else "",
            "introuvable": bool(matricule) and beneficiaire is None,
            "speciales": [x for x in speciales if not x["reglee"]],
        },
    )


@login_required
def payer_speciale(request, pk):
    """Payer une cotisation spéciale pour soi, ou au nom d'un bureau (Trésorier)."""
    cs = get_object_or_404(CotisationSpeciale, pk=pk, ouverte=True)
    cle = request.GET.get("bureau") or request.POST.get("bureau") or ""
    unite = s.unite_par_cle(cle) if cle else None
    if unite is not None and not peut_agir_tresorerie(request.user, unite):
        raise PermissionDenied
    membre = None if unite else _membre(request.user)
    if unite is None and membre is None:
        raise Http404
    reste = s.reste_a_payer(cs, membre=membre, unite_cle=unite.cle if unite else "")
    if request.method == "POST":
        try:
            p = s.initier_paiement_special(
                request.user, cs, _entier(request.POST.get("montant")), membre=membre, unite=unite
            )
        except s.TresorerieRefusee as e:
            messages.error(request, str(e))
        else:
            return _vers_plateforme(p)
    return render(
        request,
        "tresorerie/payer_speciale.html",
        {"cs": cs, "unite": unite, "reste": reste, "TypeMontant": TypeMontant},
    )


@login_required
def paiement(request, reference):
    """Plateforme simulée : seul le payeur voit et confirme son paiement."""
    p = get_object_or_404(Paiement, reference=reference, payeur=request.user)
    if request.method == "POST" and p.etat == EtatPaiement.EN_ATTENTE:
        if request.POST.get("action") == "confirmer":
            p = s.confirmer_paiement(p)
            if p.etat == EtatPaiement.CONFIRME:
                messages.success(request, f"Paiement confirmé : {p.montant} F.")
            else:
                messages.error(request, p.message)
        else:
            s.echouer_paiement(p, "Paiement annulé par le payeur.")
            messages.info(request, "Paiement annulé : rien n'a été prélevé.")
        return redirect("tresorerie:paiement", reference=p.reference)
    return render(request, "tresorerie/paiement.html", {"p": p})


@login_required
def quittance(request, pk):
    c = get_object_or_404(
        Contribution.objects.select_related("cotisation", "membre", "paiement"), pk=pk
    )
    autorise = (
        _bn(request.user)
        or est_tresorier_national(request.user)
        or c.paiement.payeur_id == request.user.pk
        or (c.membre is not None and c.membre.compte_id == request.user.pk)
        or (c.membre is not None and peut_voir_cotisations_de(request.user, c.membre))
        or (c.unite_cle and _peut_voir_cle(request.user, c.unite_cle))
    )
    if not autorise:
        raise Http404
    from apps.tresorerie.pdf import quittance_pdf

    r = HttpResponse(quittance_pdf(c), content_type="application/pdf")
    r["Content-Disposition"] = f'inline; filename="quittance-{c.quittance}.pdf"'
    r["Cache-Control"] = "private, no-store"
    return r


def _peut_voir_cle(user, cle) -> bool:
    unite = s.unite_par_cle(cle)
    return unite is not None and peut_voir_tresorerie(user, unite)


# --- Espace de trésorerie d'un bureau ---------------------------------------------------------


@login_required
def espace(request, cle):
    unite = s.unite_par_cle(cle)
    if (
        unite is None
        or unite.niveau == Niveau.NATIONAL
        or not peut_voir_tresorerie(request.user, unite)
    ):
        raise Http404
    agit = peut_agir_tresorerie(request.user, unite)
    from apps.cotisations.models import EtatVersement, ModeVersement, Versement

    filtre = {"paroisse": unite.objet}
    if unite.niveau == Niveau.CIRCUIT:
        filtre = {"paroisse__circuit": unite.objet}
    elif unite.niveau == Niveau.REGION:
        filtre = {"paroisse__circuit__region": unite.objet}
    versements = (
        Versement.objects.filter(
            mode=ModeVersement.MOBILE_MONEY, etat=EtatVersement.VALIDE, **filtre
        )
        .select_related("membre", "paroisse")
        .order_by("-date_validation")[:50]
    )
    return render(
        request,
        "tresorerie/espace.html",
        {
            "unite": unite,
            "agit": agit,
            "versements": versements,
            "reversements": Reversement.objects.filter(cle=unite.cle).order_by("-mois")[:24],
            "speciales": s.speciales_du_bureau(unite),
            "contributions": Contribution.objects.filter(unite_cle=unite.cle).select_related(
                "cotisation"
            )[:50],
            "numero": NumeroMobileMoney.objects.filter(cle=unite.cle).first(),
        },
    )


@login_required
def payer_membres(request, cle):
    """Trésorier de paroisse : payer pour plusieurs membres (espèces reçues) par mobile money."""
    unite = s.unite_par_cle(cle)
    if unite is None or unite.niveau != Niveau.PAROISSE:
        raise Http404
    if not peut_agir_tresorerie(request.user, unite):
        raise PermissionDenied
    from apps.bureaux.perimetre import membres_visibles

    membres = list(membres_visibles(unite).order_by("nom", "prenoms"))
    if request.method == "POST":
        lignes = [(m, _entier(request.POST.get(f"n{m.pk}"))) for m in membres]
        try:
            p = s.initier_paiement_mensuel(request.user, [(m, n) for m, n in lignes if n > 0])
        except s.TresorerieRefusee as e:
            messages.error(request, str(e))
        else:
            return _vers_plateforme(p)
    return render(request, "tresorerie/payer_membres.html", {"unite": unite, "membres": membres})


# --- Bureau national ----------------------------------------------------------------------------


class CotisationSpecialeForm(forms.Form):
    libelle = forms.CharField(label="Libellé", max_length=200)
    description = forms.CharField(
        label="Description", required=False, widget=forms.Textarea(attrs={"rows": 3})
    )
    echeance = forms.DateField(
        label="Échéance (facultatif)",
        required=False,
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    type_montant = forms.ChoiceField(
        label="Type de montant",
        choices=TypeMontant.choices,
        widget=forms.RadioSelect,
        initial=TypeMontant.FIXE,
    )
    montant = forms.IntegerField(
        label="Montant (F CFA)",
        required=False,
        min_value=1,
        help_text="Fixe ou minimum ; vide pour un montant libre.",
    )
    pour_membres = forms.ChoiceField(
        label="Membres concernés",
        choices=PourMembres.choices,
        widget=forms.RadioSelect,
        initial=PourMembres.TOUS,
    )
    pour_bureaux = forms.MultipleChoiceField(
        label="Bureaux concernés",
        choices=s.NIVEAUX_BUREAUX,
        required=False,
        widget=forms.CheckboxSelectMultiple,
    )


CRITERES = (
    "statut",
    "sexe",
    "categorie",
    "grade",
    "grade_min",
    "region",
    "circuit",
    "paroisse",
    "age",
    "age_x",
    "age_y",
)


@login_required
def bn_speciales(request):
    if not _bn(request.user):
        raise PermissionDenied
    from apps.listes.filtres import FiltreListeForm

    form = CotisationSpecialeForm(request.POST or None)
    filtres = FiltreListeForm(s.NATIONAL, request.POST if request.method == "POST" else None)
    if request.method == "POST" and form.is_valid():
        d = form.cleaned_data
        criteres = {}
        for cle in CRITERES:
            valeurs = [v for v in request.POST.getlist(cle) if v]
            if valeurs:
                criteres[cle] = (
                    valeurs if len(valeurs) > 1 or cle in ("statut", "grade") else valeurs[0]
                )
        try:
            cs = s.creer_cotisation_speciale(
                libelle=d["libelle"],
                description=d["description"],
                echeance=d["echeance"],
                type_montant=d["type_montant"],
                montant=d["montant"],
                pour_membres=d["pour_membres"],
                criteres=criteres,
                pour_bureaux=d["pour_bureaux"],
                par=request.user,
            )
        except s.TresorerieRefusee as e:
            form.add_error(None, str(e))
        else:
            messages.success(
                request,
                "Cotisation spéciale créée : elle apparaît « en attente » chez les concernés.",
            )
            return redirect("tresorerie:bn_speciale", pk=cs.pk)
    return render(
        request,
        "tresorerie/bn_speciales.html",
        {
            "form": form,
            "filtres": [filtres[n] for n in CRITERES if n in filtres.fields and n != "statut"],
            "liste": CotisationSpeciale.objects.all(),
        },
    )


@login_required
def bn_speciale(request, pk):
    if not (_bn(request.user) or est_tresorier_national(request.user)):
        raise PermissionDenied
    cs = get_object_or_404(CotisationSpeciale, pk=pk)
    if request.method == "POST" and _bn(request.user):
        cs.ouverte = not cs.ouverte  # clôture ou réouverture (rien ne s'efface)
        cs.save(update_fields=["ouverte"])
        return redirect("tresorerie:bn_speciale", pk=cs.pk)
    contributions = cs.contributions.select_related("membre").order_by("-date")
    concernes = s.membres_concernes(cs).count()
    payeurs = cs.contributions.exclude(membre=None).values("membre").distinct().count()
    return render(
        request,
        "tresorerie/bn_speciale.html",
        {
            "cs": cs,
            "contributions": contributions[:200],
            "total": sum(c.montant for c in contributions),
            "concernes": concernes,
            "payeurs": payeurs,
            "bureaux": [lib for n, lib in s.NIVEAUX_BUREAUX if n in cs.pour_bureaux],
        },
    )


@login_required
def bn_numeros(request):
    if not _bn(request.user):
        raise PermissionDenied
    from apps.organisation.models import Circuit, Paroisse, Region

    if request.method == "POST":
        unite = s.unite_par_cle(request.POST.get("cle", ""))
        if unite is None:
            raise Http404
        try:
            s.enregistrer_numero(
                unite,
                numero=request.POST.get("numero", ""),
                titulaire=request.POST.get("titulaire", ""),
                par=request.user,
            )
        except s.TresorerieRefusee as e:
            messages.error(request, str(e))
        else:
            messages.success(request, f"Numéro de {unite.libelle} enregistré.")
        return redirect(f"{request.path}?q={request.POST.get('q', '')}")
    q = request.GET.get("q", "").strip()
    unites = (
        [Unite(Niveau.REGION, r) for r in Region.objects.filter(active=True).order_by("code")]
        + [Unite(Niveau.CIRCUIT, c) for c in Circuit.objects.filter(active=True).order_by("nom")]
        + [Unite(Niveau.PAROISSE, p) for p in Paroisse.objects.filter(active=True).order_by("nom")]
    )
    if q:
        unites = [u for u in unites if q.lower() in u.libelle.lower()]
    numeros = {n.cle: n for n in NumeroMobileMoney.objects.all()}
    return render(
        request,
        "tresorerie/bn_numeros.html",
        {"lignes": [(u, numeros.get(u.cle)) for u in unites], "q": q},
    )


def _mois_param(valeur) -> datetime.date:
    try:
        annee, mois = (int(x) for x in (valeur or "").split("-"))
        return datetime.date(annee, mois, 1)
    except (TypeError, ValueError):
        jour = timezone.localdate().replace(day=1)
        return (jour - datetime.timedelta(days=1)).replace(day=1)  # le mois dernier


@login_required
def bn_reversements(request):
    tresorier, validateur = (
        est_tresorier_national(request.user),
        est_validateur_reversements(request.user),
    )
    if not (tresorier or validateur or _bn(request.user)):
        raise PermissionDenied
    mois = _mois_param(request.GET.get("mois") or request.POST.get("mois"))
    if request.method == "POST":
        action = request.POST.get("action")
        try:
            if action == "preparer" and tresorier:
                n = len(s.preparer_reversements(mois, par=request.user))
                messages.success(request, f"État préparé : {n} reversement(s).")
            elif action == "valider" and validateur:
                n = s.valider_reversements(mois, par=request.user)
                messages.success(request, f"{n} reversement(s) validé(s).")
            elif action == "envoye" and tresorier:
                r = get_object_or_404(Reversement, pk=_entier(request.POST.get("reversement")))
                s.marquer_envoye(r, reference=request.POST.get("reference", ""), par=request.user)
                messages.success(request, f"Envoi à {r.libelle} enregistré.")
            else:
                raise PermissionDenied
        except s.TresorerieRefusee as e:
            messages.error(request, str(e))
        return redirect(f"{request.path}?mois={mois:%Y-%m}")
    reversements = list(Reversement.objects.filter(mois=mois))
    return render(
        request,
        "tresorerie/bn_reversements.html",
        {
            "mois": mois,
            "reversements": reversements,
            "total": sum(r.montant for r in reversements),
            "a_preparer": s.parts_du_mois(mois),
            "tresorier": tresorier,
            "validateur": validateur,
            "Etat": EtatReversement,
        },
    )
