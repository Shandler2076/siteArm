"""Éligibles au grade visé → test → résultats → promotion des admis, actes (13/11/2026)."""

import datetime
import io

import pytest
from django.test import Client
from django.utils import timezone

from apps.grades import services as s
from apps.grades.models import ActePromotion, Candidat, ModeGrade
from apps.membres.grades import Grade
from apps.membres.models import Membre

ILYA_6_ANS = datetime.date(2019, 1, 1)


@pytest.fixture
def sous_capitaines(monde):
    """m1 et m2 Sous-Capitaines depuis 6 ans (éligibles Capitaine) ; m3 depuis peu."""
    Membre.objects.filter(pk__in=[monde["m1"].pk, monde["m2"].pk]).update(
        grade=Grade.SOUS_CAPITAINE, date_grade=ILYA_6_ANS
    )
    Membre.objects.filter(pk=monde["m3"].pk).update(
        grade=Grade.SOUS_CAPITAINE, date_grade=timezone.localdate()
    )
    return monde


def test_eligibles_au_grade_vise(sous_capitaines):
    t = sous_capitaines
    pks = set(
        s.eligibles_au_grade(Grade.CAPITAINE, timezone.localdate()).values_list("pk", flat=True)
    )
    assert pks == {t["m1"].pk, t["m2"].pk}  # pas m3 (durée), pas de Capitaines


def test_parcours_complet_jusqu_a_l_acte(sous_capitaines, compte_technique, client_technique):
    t = sous_capitaines
    session = s.creer_session(
        type_epreuve="examen",
        date=timezone.localdate(),
        lieu="Porto-Novo",
        grade_vise=Grade.CAPITAINE,
        membres=[t["m1"], t["m2"]],
        par=compte_technique,
    )
    s.saisir_resultats(session, {t["m1"].pk: "admis", t["m2"].pk: "ajourne"}, par=compte_technique)
    with pytest.raises(s.GradeRefuse):  # un ajourné ne peut pas être promu
        s.promouvoir_admis(
            session,
            [t["m2"]],
            numero="6",
            date_decision=timezone.localdate(),
            date_effet=timezone.localdate(),
            par=compte_technique,
        )
    acte = s.promouvoir_admis(
        session,
        [t["m1"]],
        numero="6",
        date_decision=timezone.localdate(),
        date_effet=timezone.localdate(),
        par=compte_technique,
    )
    m1 = Membre.objects.get(pk=t["m1"].pk)
    assert m1.grade == Grade.CAPITAINE
    h = m1.grades.latest("pk")
    assert h.acte == acte and h.reference.startswith("Décision n° 6 du")
    assert Candidat.objects.get(session=session, membre=m1).promu
    # Acte PDF et extrait
    from pypdf import PdfReader

    r = client_technique.get(f"/grades/bn/actes/{acte.pk}.pdf")
    texte = "".join(p.extract_text() for p in PdfReader(io.BytesIO(r.content)).pages)
    assert "Décision n° 6" in texte and "après l'examen" in texte
    assert m1.matricule in texte.replace("\n", "")
    c = Client()
    c.force_login(m1.compte)
    assert (
        c.get(f"/grades/acte/{acte.pk}/extrait.pdf", {"matricule": m1.matricule}).status_code == 200
    )
    autre = Client()
    autre.force_login(t["m2"].compte)
    url = f"/grades/acte/{acte.pk}/extrait.pdf"
    assert autre.get(url, {"matricule": m1.matricule}).status_code == 404


def test_seuls_les_eligibles_sont_candidats(sous_capitaines, compte_technique):
    with pytest.raises(s.GradeRefuse):
        s.creer_session(
            type_epreuve="test",
            date=timezone.localdate(),
            grade_vise=Grade.CAPITAINE,
            membres=[sous_capitaines["m3"]],
            par=compte_technique,
        )


def test_promotion_speciale(monde, compte_technique):
    m4 = monde["m4"]
    Membre.objects.filter(pk=m4.pk).update(grade=Grade.SOLDAT_1, date_grade=timezone.localdate())
    with pytest.raises(s.GradeRefuse):  # motif obligatoire
        s.promotion_speciale(
            [m4],
            grade=Grade.CAPITAINE,
            date_effet=timezone.localdate(),
            numero="7",
            date_decision=timezone.localdate(),
            motif="",
            par=compte_technique,
        )
    acte = s.promotion_speciale(
        [m4],
        grade=Grade.CAPITAINE,
        date_effet=timezone.localdate(),
        numero="7",
        date_decision=timezone.localdate(),
        motif="Services remarquables",
        par=compte_technique,
    )
    m4.refresh_from_db()
    assert m4.grade == Grade.CAPITAINE
    assert m4.grades.latest("pk").mode == ModeGrade.EXCEPTIONNELLE
    assert ActePromotion.objects.get() == acte and acte.motif == "Services remarquables"


def test_pages_grades_bn(sous_capitaines, client_technique):
    html = client_technique.get(
        "/grades/bn/eligibles/", {"grade": Grade.CAPITAINE}
    ).content.decode()
    assert sous_capitaines["m1"].matricule in html and sous_capitaines["m3"].matricule not in html
    for url in ("/grades/bn/sessions/", "/grades/bn/speciales/", "/grades/bn/actes/"):
        assert client_technique.get(url).status_code == 200
    c = Client()
    c.force_login(sous_capitaines["sec_p1"].compte)
    assert c.get("/grades/bn/eligibles/").status_code == 403


def test_liste_eligibles_au_grade_vise(sous_capitaines):
    c = Client()
    c.force_login(sous_capitaines["sec_p1"].compte)
    cle = f"paroisse-{sous_capitaines['P1'].pk}"
    html = c.get(
        f"/bureau/{cle}/listes/", {"envoye": "1", "statut": "actif", "eligible_a": Grade.CAPITAINE}
    ).content.decode()
    assert sous_capitaines["m1"].matricule in html  # m1 est à P1
    assert "Éligibles au grade de Capitaine" in html
