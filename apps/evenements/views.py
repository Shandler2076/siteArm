"""Pages du Bureau national : événements, convocations, pointage, exports."""

import io

from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.http import HttpResponse, QueryDict
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from apps.bureaux.models import Niveau
from apps.bureaux.perimetre import Unite
from apps.evenements.forms import EvenementForm
from apps.evenements.models import Convocation, Evenement, Formule, Presence, Role, Session
from apps.evenements.services import (
    EvenementRefuse,
    annuler_evenement,
    convoquer,
    creer_evenement,
    modifier_evenement,
    pointer,
    rechercher_membres,
    retirer,
)
from apps.listes.filtres import FiltreListeForm, membres_filtres

bn = permission_required("membres.gerer_membres", raise_exception=True)
NATIONAL = Unite(Niveau.NATIONAL, None)
MAX_PROPOSES = 500
# Filtres visibles d'emblée sur la page « Convoquer » ; les autres sont sous « Plus de filtres ».
FILTRES_PRINCIPAUX = ["region", "circuit", "paroisse", "grade", "statut"]


def _pk(valeur) -> int:
    """Identifiant envoyé par un formulaire ; une valeur non numérique donne une page 404."""
    from django.http import Http404

    if not (valeur or "").isdigit():
        raise Http404
    return int(valeur)


@login_required
@bn
def liste(request):
    maintenant = timezone.now()
    tous = Evenement.objects.all()
    return render(
        request,
        "evenements/liste.html",
        {
            "a_venir": tous.filter(debut__gte=maintenant, etat="prevu").order_by("debut"),
            "passes": tous.filter(debut__lt=maintenant, etat="prevu"),
            "annules": tous.filter(etat="annule"),
        },
    )


def _champs(d) -> dict:
    return {
        "nom": d["nom"],
        "debut": d["debut"],
        "fin": d["fin"],
        "lieu": d["lieu"],
        "description": d["description"],
        "avec_autorisation": d["avec_autorisation"],
        "avec_sections": d["avec_sections"],
        "validite_debut": d["validite_debut"],
        "validite_heures": d["validite_heures"],
    }


@login_required
@bn
def nouveau(request):
    form = EvenementForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            ev = creer_evenement(
                **_champs(form.cleaned_data), sessions=form.liste_sessions(), par=request.user
            )
        except EvenementRefuse as e:
            form.add_error(None, str(e))
        else:
            messages.success(
                request, "Événement créé. Vous pouvez maintenant convoquer les membres."
            )
            return redirect("evenements:detail", pk=ev.pk)
    return render(request, "evenements/formulaire.html", {"form": form, "ev": None})


@login_required
@bn
def modifier(request, pk):
    ev = get_object_or_404(Evenement, pk=pk)
    form = EvenementForm(
        request.POST or None, initial=EvenementForm.initial_depuis(ev), deja_cree=True
    )
    if request.method == "POST" and form.is_valid():
        try:
            modifier_evenement(
                ev, par=request.user, sessions=form.liste_sessions(), **_champs(form.cleaned_data)
            )
        except EvenementRefuse as e:
            form.add_error(None, str(e))
        else:
            messages.success(request, "Événement modifié.")
            return redirect("evenements:detail", pk=ev.pk)
    return render(request, "evenements/formulaire.html", {"form": form, "ev": ev})


def _par_session(ev):
    convocations = list(ev.convocations.filter(active=True).select_related("membre", "session"))
    groupes = []
    for session in [*ev.sessions.all(), None]:
        membres = [c for c in convocations if c.session_id == (session.pk if session else None)]
        if membres:
            groupes.append({"session": session, "convocations": membres})
    presents = sum(1 for c in convocations if c.presence == Presence.PRESENT)
    pointes = sum(1 for c in convocations if c.presence)
    return groupes, len(convocations), presents, pointes


@login_required
@bn
def detail(request, pk):
    ev = get_object_or_404(Evenement, pk=pk)
    if request.method == "POST":
        action = request.POST.get("action")
        try:
            if action == "retirer":
                c = get_object_or_404(ev.convocations, pk=_pk(request.POST.get("convocation")))
                retirer(c, motif=request.POST.get("motif", ""), par=request.user)
                messages.success(request, f"Convocation de {c.membre.nom_complet} retirée.")
            elif action == "annuler":
                annuler_evenement(ev, motif=request.POST.get("motif", ""), par=request.user)
                messages.success(request, "Événement annulé ; les convoqués sont avertis.")
            else:
                raise EvenementRefuse("Action inconnue.")
        except EvenementRefuse as e:
            messages.error(request, str(e))
        return redirect("evenements:detail", pk=ev.pk)
    groupes, total, presents, pointes = _par_session(ev)
    retires = ev.convocations.filter(active=False).select_related("membre")
    return render(
        request,
        "evenements/detail.html",
        {
            "ev": ev,
            "groupes": groupes,
            "total": total,
            "presents": presents,
            "pointes": pointes,
            "taux": round(100 * presents / pointes) if pointes else None,
            "retires": retires,
        },
    )


@login_required
@bn
def convoquer_vue(request, pk):
    ev = get_object_or_404(Evenement, pk=pk)
    if request.method == "POST":
        pks = [int(x) for x in request.POST.getlist("membres") if x.isdigit()]
        session = None
        if request.POST.get("session", "").isdigit():
            session = get_object_or_404(Session, pk=request.POST["session"], evenement=ev)
        from apps.membres.models import Membre

        membres = list(Membre.objects.filter(pk__in=pks).select_related("compte"))
        try:
            if not membres:
                raise EvenementRefuse("Cochez au moins un membre.")
            faites = convoquer(
                ev,
                membres,
                session=session,
                sans_session=session is None,
                role=request.POST.get("role", Role.TRAVAILLEUR),
                formule=request.POST.get("formule", ""),
                role_autre=request.POST.get("role_autre", ""),
                par=request.user,
            )
        except EvenementRefuse as e:
            messages.error(request, str(e))
            return redirect(request.get_full_path())
        messages.success(request, f"{len(faites)} membre(s) convoqué(s) ; ils sont notifiés.")
        return redirect("evenements:detail", pk=ev.pk)
    form = FiltreListeForm(NATIONAL, request.GET or QueryDict(""))
    proposes, trop = [], False
    if request.GET.get("envoye") and form.is_valid():
        qs = membres_filtres(NATIONAL, form.cleaned_data, timezone.localdate())
        proposes = list(qs.select_related("compte")[: MAX_PROPOSES + 1])
        trop = len(proposes) > MAX_PROPOSES
        proposes = proposes[:MAX_PROPOSES]
    deja = set(ev.convocations.filter(active=True).values_list("membre_id", flat=True))
    principaux = [n for n in FILTRES_PRINCIPAUX if n in form.fields]
    return render(
        request,
        "evenements/convoquer.html",
        {
            "ev": ev,
            "form": form,
            "principaux": [form[n] for n in principaux],
            "autres": [
                form[n]
                for n in form.fields
                if n not in principaux and n not in ("envoye", "colonnes")
            ],
            "proposes": proposes,
            "trop": trop,
            "deja": deja,
            "roles": Role.choices,
            "formules": Formule.choices,
            "roles_autres": sorted(
                set(ev.convocations.exclude(role_autre="").values_list("role_autre", flat=True))
            ),
        },
    )


@login_required
@bn
def recherche_membres(request, pk):
    """Recherche d'un membre à convoquer, par matricule ou par nom (réponse JSON, BN seulement)."""
    from django.http import JsonResponse

    ev = get_object_or_404(Evenement, pk=pk)
    deja = set(ev.convocations.filter(active=True).values_list("membre_id", flat=True))
    resultats = []
    for m in rechercher_membres(request.GET.get("q", "")):
        a = m.affectation_actuelle
        resultats.append(
            {
                "pk": m.pk,
                "nom": m.nom_complet,
                "matricule": m.matricule,
                "paroisse": a.paroisse.nom if a else "",
                "deja": m.pk in deja,
            }
        )
    return JsonResponse({"resultats": resultats})


@login_required
@bn
def pointage(request, pk):
    ev = get_object_or_404(Evenement, pk=pk)
    if request.method == "POST":
        c = get_object_or_404(ev.convocations, pk=_pk(request.POST.get("convocation")))
        try:
            pointer(c, request.POST.get("presence", ""), par=request.user)
        except EvenementRefuse as e:
            messages.error(request, str(e))
        return redirect(f"{request.get_full_path()}#c{c.pk}")
    q = request.GET.get("q", "").strip()
    convocations = ev.convocations.filter(active=True).select_related("membre", "session")
    if q:
        from django.db.models import Q

        convocations = convocations.filter(
            Q(membre__nom__icontains=q)
            | Q(membre__prenoms__icontains=q)
            | Q(membre__matricule__icontains=q)
        )
    return render(
        request,
        "evenements/pointage.html",
        {"ev": ev, "convocations": convocations, "q": q, "presences": Presence.choices[1:]},
    )


def _lignes(ev):
    for c in ev.convocations.filter(active=True).select_related("membre", "session"):
        m = c.membre
        yield [
            m.matricule,
            m.get_grade_display() if m.grade is not None else "",
            m.nom.upper(),
            m.prenoms,
            c.get_role_display(),
            c.session.nom if c.session else "",
            c.get_presence_display() if c.presence else "Non pointé",
        ]


ENTETES = ["Matricule", "Grade", "Nom", "Prénoms", "Rôle", "Section", "Présence"]


@login_required
@bn
def export_excel(request, pk):
    from openpyxl import Workbook

    ev = get_object_or_404(Evenement, pk=pk)
    wb = Workbook()
    ws = wb.active
    ws.title = "Convoqués"
    ws.append([ev.nom])
    ws["A1"].data_type = "s"  # jamais de formule
    ws.append(ENTETES)
    for ligne in _lignes(ev):
        ws.append(ligne)
        for cellule in ws[ws.max_row]:
            cellule.data_type = "s"
    tampon = io.BytesIO()
    wb.save(tampon)
    r = HttpResponse(
        tampon.getvalue(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    r["Content-Disposition"] = f'attachment; filename="convoques-{ev.pk}.xlsx"'
    return r


@login_required
@bn
def export_pdf(request, pk):
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.pdfgen import canvas

    from apps.listes.exports import MARGE, entete_officiel, pied_de_page
    from apps.membres.pdf import MARINE, _ajuste, _polices

    ev = get_object_or_404(Evenement, pk=pk)
    _polices()
    larg, haut = A4
    tampon = io.BytesIO()
    c = canvas.Canvas(tampon, pagesize=A4)
    debut = timezone.localtime(ev.debut)
    sous = [f"{debut:%d/%m/%Y à %H:%M}" + (f" — {ev.lieu}" if ev.lieu else "")]
    largeurs = [27, 27, 30, 34, 20, 26, 20]
    numero = 1

    def entete():
        y = entete_officiel(c, f"Convoqués — {ev.nom}", sous, larg, haut)
        c.setFont("Sans-Gras", 8.5)
        c.setFillColor(MARINE)
        x = MARGE
        for t, w in zip(ENTETES, largeurs, strict=True):
            c.drawString(x, y, t)
            x += w * mm
        return y - 6 * mm

    y = entete()
    for ligne in _lignes(ev):
        if y < 18 * mm:
            pied_de_page(c, numero, larg)
            c.showPage()
            numero += 1
            y = entete()
        c.setFont("Sans", 8.5)
        x = MARGE
        for v, w in zip(ligne, largeurs, strict=True):
            c.drawString(x, y, _ajuste(str(v), "Sans", 8.5, w * mm - 2 * mm))
            x += w * mm
        y -= 5.5 * mm
    pied_de_page(c, numero, larg)
    c.showPage()
    c.save()
    r = HttpResponse(tampon.getvalue(), content_type="application/pdf")
    r["Content-Disposition"] = f'attachment; filename="convoques-{ev.pk}.pdf"'
    return r


@login_required
@bn
def autorisations_pdf(request, pk):
    """Toutes les autorisations valables d'un événement (Task 3)."""
    from apps.evenements.pdf import autorisations_pdf as fabriquer

    ev = get_object_or_404(Evenement, pk=pk, avec_autorisation=True)
    r = HttpResponse(fabriquer(ev), content_type="application/pdf")
    r["Content-Disposition"] = f'inline; filename="autorisations-{ev.pk}.pdf"'
    return r


@login_required
def mes_evenements(request):
    from apps.evenements.services import autorisation_valable
    from apps.membres.models import Membre

    try:
        membre = request.user.membre
    except Membre.DoesNotExist:
        membre = None
    convocations = []
    if membre is not None:
        for c in membre.convocations.filter(active=True).select_related("evenement", "session"):
            c.valable = autorisation_valable(c)
            convocations.append(c)
    return render(request, "evenements/mes_evenements.html", {"convocations": convocations})


@login_required
def autorisation(request, pk):
    from django.http import Http404

    from apps.bureaux.perimetre import peut_imprimer_autorisation
    from apps.evenements.pdf import autorisation_pdf
    from apps.evenements.services import autorisation_valable

    c = get_object_or_404(
        Convocation.objects.select_related("evenement", "membre", "session"), pk=pk
    )
    if not autorisation_valable(c) or not peut_imprimer_autorisation(request.user, c):
        raise Http404
    r = HttpResponse(autorisation_pdf(c), content_type="application/pdf")
    r["Content-Disposition"] = f'inline; filename="autorisation-{c.membre.matricule}.pdf"'
    r["Cache-Control"] = "private, no-store"
    return r


def maintenant():
    return timezone.now()


def verifier(request, jeton):
    """Page publique du QR code : valable, pas encore valable, expirée ou non valable."""
    import base64

    from apps.evenements.services import convocation_par_jeton, etat_scan

    c = convocation_par_jeton(jeton)
    etat, raison = etat_scan(c, maintenant())
    photo = None
    if etat in ("valable", "pas_encore") and c.membre.photo_acceptee:
        try:
            with c.membre.photo_acceptee.fichier.open("rb") as f:
                photo = base64.b64encode(f.read()).decode()
        except OSError:
            photo = None  # fichier introuvable (restauration incomplète…) : pas de photo
    reponse = render(
        request,
        "evenements/verifier.html",
        {
            "c": c,
            "etat": etat,
            "valable": etat == "valable",
            "photo": photo,
            "raison": raison,
            "peut_pointer": etat == "valable" and request.user.has_perm("membres.gerer_membres"),
        },
    )
    reponse["Cache-Control"] = "no-store"
    reponse["X-Robots-Tag"] = "noindex"
    return reponse


__all__ = ["Convocation"]
