"""Pages du courrier. Les droits viennent du gardien des périmètres (`unites_courrier`,
`membres_visibles`, `qualite_signataire`) et de `services.peut_voir`."""

import mimetypes

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Prefetch, Q
from django.http import FileResponse, Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.bureaux.perimetre import (
    Niveau,
    membres_visibles,
    peut_deposer_signature,
    unite_par_cle,
    unites_courrier,
)
from apps.courrier import services
from apps.courrier.models import (
    Courrier,
    Destinataire,
    Etat,
    Mode,
    MotClavier,
    Nature,
    OrigineMot,
    PieceJointe,
    ReglagesClavier,
    TypeDestinataire,
)

NIVEAUX = [
    (Niveau.REGION, "Tous les bureaux régionaux de coordination"),
    (Niveau.CIRCUIT, "Tous les bureaux de section circuit"),
    (Niveau.PAROISSE, "Tous les bureaux d'unité paroissiale"),
]


def _unite(request, cle):
    """Bureau dont le compte tient le courrier ; sinon 404 (même pour le BN)."""
    unite = unite_par_cle(cle)
    if unite is None or unite not in unites_courrier(request.user):
        raise Http404
    return unite


def _gerer_membres(request):
    if not request.user.has_perm("membres.gerer_membres"):
        raise Http404


def _clavier():
    return {
        "lettres": ReglagesClavier.courant().liste(),
        "mots": services.mots_suggeres(),
    }


@login_required
def recus(request, cle):
    unite = _unite(request, cle)
    courriers = list(services.courriers_recus(unite)[:200])
    lignes = {
        d.courrier_id: d
        for d in Destinataire.objects.filter(
            courrier__in=courriers, type=TypeDestinataire.BUREAU, unite_cle=unite.cle
        )
    }
    services.marquer_recus(lignes.values(), request.user)  # accusé de réception
    return render(
        request,
        "courrier/recus.html",
        {"unite": unite, "lignes": [(c, lignes.get(c.pk)) for c in courriers]},
    )


@login_required
def envoyes(request, cle):
    unite = _unite(request, cle)
    courriers = services.courriers_envoyes(unite).annotate(
        nb_destinataires=Count("destinataires", filter=Q(destinataires__transmis_par=""))
    )[:300]
    return render(request, "courrier/envoyes.html", {"unite": unite, "courriers": courriers})


def _entiers(valeurs) -> list[int]:
    return [int(v) for v in valeurs if str(v).isdigit()]


@login_required
def nouveau(request, cle):
    unite = _unite(request, cle)
    annee = timezone.localdate().year
    proposes = services.bureaux_proposes(unite)
    donnees = request.POST if request.method == "POST" else {}
    membres = []
    if request.method == "POST":
        membres = list(
            membres_visibles(unite).filter(pk__in=_entiers(request.POST.getlist("membres")))
        )
        numero = request.POST.get("numero_ordre", "")
        try:
            c = services.preparer(
                unite=unite,
                nature=request.POST.get("nature", ""),
                mode=request.POST.get("mode", Mode.REDIGE),
                objet=request.POST.get("objet", ""),
                texte=request.POST.get("texte", ""),
                fichier=request.FILES.get("fichier"),
                lieu=request.POST.get("lieu", ""),
                numero_ordre=int(numero) if numero.isdigit() else None,
                bureaux=request.POST.getlist("bureaux"),
                niveaux=request.POST.getlist("niveaux"),
                membres=membres,
                pieces=request.FILES.getlist("pieces"),
                par=request.user,
            )
        except services.CourrierRefuse as e:
            messages.error(request, str(e))
        else:
            messages.success(request, "Courrier préparé : il attend la signature.")
            return redirect("courrier:detail", c.pk)
    return render(
        request,
        "courrier/nouveau.html",
        {
            "unite": unite,
            "proposes": proposes,
            "niveaux": NIVEAUX if unite.niveau != Niveau.PAROISSE else [],
            "numero": services.proposer_numero(unite, annee),
            "apercu_numero": services.numero_complet(
                unite, services.proposer_numero(unite, annee), annee
            ),
            "lieu": services.lieu_par_defaut(unite),
            "d": donnees,
            "choisis": set(request.POST.getlist("bureaux")) if donnees else set(),
            "niveaux_choisis": set(request.POST.getlist("niveaux")) if donnees else set(),
            "membres_choisis": membres,
            "clavier": _clavier(),
            "Nature": Nature,
        },
    )


@login_required
def recherche(request, cle):
    """Recherche d'un membre du périmètre du bureau (matricule ou nom), réponse JSON."""
    from django.db.models import Q

    unite = _unite(request, cle)
    texte = request.GET.get("q", "").strip()
    resultats = []
    if len(texte) >= 2:
        filtre = Q()
        for mot in texte.split():
            filtre &= Q(nom__icontains=mot) | Q(prenoms__icontains=mot)
        membres = (
            membres_visibles(unite)
            .filter(Q(matricule__icontains=texte) | filtre)
            .exclude(statut__in=services.SORTIS)
            .order_by("nom", "prenoms")[:20]
        )
        resultats = [{"pk": m.pk, "nom": m.nom_complet, "matricule": m.matricule} for m in membres]
    return JsonResponse({"resultats": resultats})


def vue_complete(request, c: Courrier) -> bool:
    """L'expéditeur et le Bureau national voient les noms de tous les destinataires."""
    unite = services.unite_expeditrice(c)
    if unite is not None and unite in unites_courrier(request.user):
        return True
    return c.envoye and request.user.has_perm("membres.gerer_membres")


def _courrier_visible(request, pk) -> Courrier:
    c = get_object_or_404(Courrier, pk=pk)
    if not services.peut_voir(request.user, c):
        raise Http404
    return c


@login_required
def detail(request, pk):
    c = _courrier_visible(request, pk)
    mes_lignes = services.destinataires_du_compte(request.user, c)
    for d in mes_lignes:
        services.ouvrir(d, request.user)  # accusé de lecture
    unite = services.unite_expeditrice(c)
    expediteur = unite is not None and unite in unites_courrier(request.user)
    voit_suivi = vue_complete(request, c)
    transmis = (
        c.destinataires.exclude(transmis_par="")
        .values("transmis_par")
        .annotate(n=Count("pk"), lus=Count("lu_le"))
        .order_by("transmis_par")
        if voit_suivi
        else []
    )
    paroisses = [
        u
        for u in unites_courrier(request.user)
        if u.niveau == Niveau.PAROISSE
        and any(d.type == "bureau" and d.unite_cle == u.cle for d in mes_lignes)
    ]
    return render(
        request,
        "courrier/detail.html",
        {
            "c": c,
            "mes_lignes": [Destinataire.objects.get(pk=d.pk) for d in mes_lignes],
            "expediteur": expediteur,
            "suivi": list(services.destinataires_directs(c).select_related("lu_par", "accuse_par"))
            if voit_suivi
            else [],
            "transmis": [(unite_par_cle(t["transmis_par"]), t["n"], t["lus"]) for t in transmis],
            "qualite": services.peut_signer(request.user, c),
            "a_signature": services.signature_active(request.user) is not None,
            "transmettre": paroisses if c.communique and c.envoye else [],
            "destinataire_texte": services.libelle_destinataires(
                c, avec_membres=voit_suivi, membre=getattr(request.user, "membre", None)
            ),
        },
    )


@login_required
@require_POST
def action(request, pk):
    c = _courrier_visible(request, pk)
    quoi = request.POST.get("action", "")
    try:
        if quoi == "valider":
            version = request.POST.get("version", "")
            services.valider(c, par=request.user, version=int(version) if version.isdigit() else -1)
            messages.success(request, "Courrier signé et envoyé.")
        elif quoi == "renvoyer":
            services.renvoyer(c, motif=request.POST.get("motif", ""), par=request.user)
            messages.success(request, "Courrier renvoyé pour correction.")
        elif quoi == "abandonner":
            services.annuler(c, par=request.user)
            messages.success(request, "Courrier abandonné.")
        elif quoi == "accuser":
            ligne = get_object_or_404(Destinataire, pk=request.POST.get("ligne", ""), courrier=c)
            services.accuser(ligne, par=request.user)
            messages.success(request, "Merci : l'expéditeur voit que vous avez reçu le courrier.")
        elif quoi == "transmettre":
            unite = unite_par_cle(request.POST.get("unite", ""))
            if unite is None:
                raise Http404
            n = services.transmettre_aux_membres(c, unite, par=request.user)
            messages.success(request, f"Communiqué transmis à {n} membre(s).")
        else:
            raise Http404
    except services.CourrierRefuse as e:
        messages.error(request, str(e))
    return redirect("courrier:detail", c.pk)


@login_required
def modifier(request, pk):
    c = _courrier_visible(request, pk)
    unite = services.unite_expeditrice(c)
    if unite is None or unite not in unites_courrier(request.user):
        raise Http404
    if c.etat not in (Etat.A_SIGNER, Etat.A_CORRIGER):
        return redirect("courrier:detail", c.pk)
    if request.method == "POST":
        numero = request.POST.get("numero_ordre", "")
        try:
            services.modifier(
                c,
                objet=request.POST.get("objet", ""),
                texte=request.POST.get("texte", ""),
                fichier=request.FILES.get("fichier"),
                lieu=request.POST.get("lieu", ""),
                numero_ordre=int(numero) if numero.isdigit() else None,
                par=request.user,
            )
        except services.CourrierRefuse as e:
            messages.error(request, str(e))
        else:
            messages.success(request, "Courrier modifié : il attend la signature.")
            return redirect("courrier:detail", c.pk)
    return render(request, "courrier/modifier.html", {"c": c, "clavier": _clavier()})


def _fichier(champ, nom):
    if not champ:
        raise Http404
    type_contenu = mimetypes.guess_type(champ.name)[0] or "application/octet-stream"
    r = FileResponse(champ.open("rb"), content_type=type_contenu, filename=nom)
    r["Cache-Control"] = "private, no-store"
    return r


@login_required
def pdf(request, pk):
    from apps.courrier.pdf import courrier_pdf

    c = _courrier_visible(request, pk)
    complet = vue_complete(request, c)
    membre = getattr(request.user, "membre", None)
    r = HttpResponse(
        courrier_pdf(c, avec_membres=complet, membre=membre), content_type="application/pdf"
    )
    nom = f"courrier-{c.annee}-{c.numero_ordre:03d}.pdf"
    r["Content-Disposition"] = f'inline; filename="{nom}"'
    r["Cache-Control"] = "private, no-store"
    return r


@login_required
def original(request, pk):
    c = _courrier_visible(request, pk)
    return _fichier(c.fichier, c.fichier.name.rsplit("/", 1)[-1] if c.fichier else "")


@login_required
def piece(request, pk, piece_pk):
    c = _courrier_visible(request, pk)
    p = get_object_or_404(PieceJointe, pk=piece_pk, courrier=c)
    return _fichier(p.fichier, p.fichier.name.rsplit("/", 1)[-1])


@login_required
def a_signer(request):
    return render(
        request,
        "courrier/a_signer.html",
        {
            "courriers": services.courriers_a_signer(request.user),
            "a_signature": services.signature_active(request.user) is not None,
        },
    )


@login_required
def moi(request):
    membre = getattr(request.user, "membre", None)
    if membre is None:
        raise Http404
    courriers = list(services.courriers_du_membre(membre)[:200])
    return render(request, "courrier/moi.html", {"courriers": courriers})


@login_required
def ma_signature(request):
    if not peut_deposer_signature(request.user):
        raise Http404
    if request.method == "POST":
        fichier = request.FILES.get("image")
        if fichier is None:
            messages.error(request, "Choisissez l'image de votre signature.")
        else:
            try:
                services.deposer_signature(request.user, fichier)
            except services.CourrierRefuse as e:
                messages.error(request, str(e))
            else:
                messages.success(request, "Votre signature est enregistrée.")
                return redirect("courrier:ma_signature")
    return render(
        request,
        "courrier/ma_signature.html",
        {"signature": services.signature_active(request.user)},
    )


@login_required
def ma_signature_image(request):
    """L'image n'est montrée qu'à son propriétaire (pas même au BN)."""
    sig = services.signature_active(request.user)
    if sig is None:
        raise Http404
    return _fichier(sig.image, "signature.png")


def verifier(request, jeton):
    """Page publique ouverte par le QR code : authentique ou non, sans le texte du courrier."""
    if not services.JETON.match(jeton or ""):
        c = None
    else:
        c = Courrier.objects.filter(jeton=jeton, etat=Etat.ENVOYE).first()
    return render(request, "courrier/verifier.html", {"c": c})


@login_required
def bn_registre(request):
    _gerer_membres(request)
    courriers = Courrier.objects.filter(etat=Etat.ENVOYE).prefetch_related(
        Prefetch("destinataires", queryset=Destinataire.objects.filter(transmis_par=""))
    )
    bureau = request.GET.get("bureau", "")
    if bureau:
        courriers = courriers.filter(expediteur_cle=bureau)
    annee = request.GET.get("annee", "")
    if annee.isdigit():
        courriers = courriers.filter(annee=int(annee))
    expediteurs = (
        Courrier.objects.filter(etat=Etat.ENVOYE)
        .values_list("expediteur_cle", "expediteur_libelle")
        .distinct()
        .order_by("expediteur_libelle")
    )
    return render(
        request,
        "courrier/bn_registre.html",
        {
            "courriers": courriers.order_by("-date_envoi")[:500],
            "expediteurs": expediteurs,
            "bureau": bureau,
            "annee": annee,
        },
    )


@login_required
def bn_clavier(request):
    _gerer_membres(request)
    if request.method == "POST":
        quoi = request.POST.get("action")
        try:
            if quoi == "lettres":
                services.enregistrer_lettres(request.POST.get("lettres", ""), par=request.user)
                messages.success(request, "Lettres du clavier enregistrées.")
            elif quoi == "mots":
                n = services.enregistrer_mots_bn(request.POST.get("mots", ""), par=request.user)
                messages.success(request, f"{n} mot(s) enregistré(s).")
            elif quoi == "masquer":
                services.masquer_mot(request.POST.get("mot", ""), par=request.user)
                messages.success(request, "Mot retiré des propositions.")
        except services.CourrierRefuse as e:
            messages.error(request, str(e))
        return redirect("courrier:bn_clavier")
    return render(
        request,
        "courrier/bn_clavier.html",
        {
            "lettres": ReglagesClavier.courant().lettres,
            "mots_bn": "\n".join(
                MotClavier.objects.filter(origine=OrigineMot.BN, actif=True)
                .order_by("mot")
                .values_list("mot", flat=True)
            ),
            "appris": services.mots_appris_proposes(),
            "clavier": _clavier(),
        },
    )
