import datetime
from datetime import date
from urllib.parse import urlencode

import pytest
from django.http import QueryDict

from apps.bureaux.models import Niveau
from apps.bureaux.perimetre import Unite
from apps.listes.colonnes import COLONNES_LISTE, lignes, preparer
from apps.listes.filtres import FiltreListeForm, membres_filtres, resume_filtres

J = date(2026, 11, 10)


def U(niveau, objet=None):
    return Unite(niveau, objet)


def _form(unite, **data):
    return FiltreListeForm(unite, QueryDict(urlencode(data | {"envoye": "1"}, doseq=True)))


def _noms(unite, **data):
    form = _form(unite, **data)
    assert form.is_valid(), form.errors
    return sorted(m.nom for m in membres_filtres(unite, form.cleaned_data, J))


def test_perimetre_paroisse(monde):
    assert _noms(U(Niveau.PAROISSE, monde["P1"])) == ["Adjovi", "Secretaire", "Tresorier"]


def test_perimetre_circuit_et_national(monde):
    assert _noms(U(Niveau.CIRCUIT, monde["Ekpe A"])) == [
        "Adjovi",
        "Bio",
        "Chef",
        "Secretaire",
        "Tresorier",
    ]
    assert len(_noms(U(Niveau.NATIONAL))) == 7


@pytest.fixture
def varies(monde, nouveau_membre):
    def creer(paroisse, nom, sexe, naissance):
        m = nouveau_membre(monde[paroisse], nom)
        m.sexe = sexe
        m.date_naissance = naissance
        m.save()
        return m

    creer("P1", "Femme45", "F", date(1981, 1, 1))
    creer("P3", "FemmeB", "F", date(1981, 1, 1))
    creer("P2", "Homme45", "M", date(1981, 1, 1))
    creer("P2", "Femme30", "F", date(1996, 1, 1))
    return monde


def test_filtres_combines(varies):
    nat = U(Niveau.NATIONAL)
    data = {"sexe": "F", "age": "plus", "age_x": 40, "circuit": varies["Ekpe A"].pk}
    assert _noms(nat, **data) == ["Femme45"]
    assert _noms(nat, sexe="F") == ["Femme30", "Femme45", "FemmeB"]
    assert _noms(nat, paroisse=varies["P2"].pk, age="entre", age_x=18, age_y=40) == ["Femme30"]
    assert _noms(nat, region=varies["WEME"].pk) == ["Dossou"]


def test_filtre_fonction(monde, donner_mandat):
    from apps.bureaux.models import Fonction

    f = Fonction.objects.get(nom="Secrétaire paroissial")
    nat = U(Niveau.NATIONAL)
    assert _noms(nat, fonction=f.pk) == ["Secretaire"]
    mandat = monde["sec_p1"].mandats.get()
    mandat.date_fin = datetime.date(2026, 1, 1)
    mandat.save()
    assert _noms(nat, fonction=f.pk) == []


def test_filtre_categorie_annee_statut(monde):
    m1, m2 = monde["m1"], monde["m2"]
    m1.categorie = "honneur"
    m1.save()
    m2.statut = "decede"
    m2.save()
    nat = U(Niveau.NATIONAL)
    assert _noms(nat, categorie="honneur") == ["Adjovi"]
    assert _noms(nat, statut=["decede"]) == ["Bio"]
    assert len(_noms(nat)) == 7  # aucun statut coché = tous
    assert "Bio" not in _noms(nat, statut=["actif"])
    assert len(_noms(nat, annee=2015)) == 7 and _noms(nat, annee=2016) == []


def test_parametres_invalides_sans_fuite(monde):
    p1 = U(Niveau.PAROISSE, monde["P1"])
    ekpe = U(Niveau.CIRCUIT, monde["Ekpe A"])
    for unite, data in [
        (p1, {"age": "plus", "age_x": "abc"}),
        (p1, {"age": "entre", "age_x": 40, "age_y": 18}),
        (p1, {"age": "moins", "age_x": -1}),
        (p1, {"age": "plus"}),
        (ekpe, {"paroisse": monde["P4"].pk}),
        (p1, {"fonction": 999}),
        (ekpe, {"colonnes": ["npi"]}),
        (ekpe, {"statut": ["inconnu"]}),
    ]:
        assert not _form(unite, **data).is_valid(), data


def test_valeurs_initiales(monde):
    form = FiltreListeForm(U(Niveau.PAROISSE, monde["P1"]), QueryDict(""))
    assert form.is_valid()
    assert form.cleaned_data["statut"] == ["actif"]
    assert form.cleaned_data["colonnes"] == [
        "matricule",
        "nom",
        "prenoms",
        "sexe",
        "age",
        "telephone",
        "paroisse",
    ]


def test_options_limitees_au_perimetre(monde):
    form = _form(U(Niveau.CIRCUIT, monde["Ekpe A"]))
    assert set(form.fields["paroisse"].queryset) == {monde["P1"], monde["P2"]}
    assert "region" not in form.fields and "circuit" not in form.fields
    assert "paroisse" not in _form(U(Niveau.PAROISSE, monde["P1"])).fields
    region = _form(U(Niveau.REGION, monde["HOULENOU"]))
    assert set(region.fields["circuit"].queryset) == {monde["Ekpe A"], monde["Ekpe B"]}
    assert "region" in _form(U(Niveau.NATIONAL)).fields


def test_resume_filtres(monde):
    form = _form(
        U(Niveau.NATIONAL),
        statut=["actif"],
        sexe="F",
        age="plus",
        age_x=40,
        circuit=monde["Ekpe A"].pk,
    )
    assert form.is_valid()
    assert resume_filtres(form) == [
        "Statut : Actif",
        "Sexe : Féminin",
        "Circuit : Ekpe A",
        "Âge : plus de 40 ans",
    ]
    vide = _form(U(Niveau.NATIONAL))
    assert vide.is_valid() and resume_filtres(vide) == ["Aucun filtre"]


def test_lignes_colonnes(monde):
    from apps.membres.models import Membre

    qs = preparer(Membre.objects.filter(pk=monde["sec_p1"].pk), J)
    (ligne,) = list(lignes(qs, list(COLONNES_LISTE), J))
    m = monde["sec_p1"]
    assert ligne == [
        m.matricule,
        "Secretaire",
        "Test",
        "M",
        None,
        "0197000000",
        "",
        "P1",
        "Ekpe A",
        "Camarade",
        "01/01/2015",
        0,
        0,
        0,
        "Membre actif",
        "Actif",
        "Secrétaire paroissial",
    ]


def test_membre_sans_affectation(monde):
    from apps.membres.models import Membre

    a = monde["m1"].affectations.get()
    a.date_fin = J
    a.save()
    qs = preparer(Membre.objects.filter(pk=monde["m1"].pk), J)
    (ligne,) = list(lignes(qs, ["paroisse", "circuit"], J))
    assert ligne == [None, None]


def test_lignes_sans_n_plus_1(monde, nouveau_membre, django_assert_max_num_queries):
    from apps.membres.models import Membre

    for i in range(27):
        nouveau_membre(monde["P1"], f"Nom{i}")
    # Colonnes du module 1 : 3 requêtes ; avec les cotisations, un nombre fixe par paquet
    # de 500 membres (jamais une requête par membre).
    module1 = [c for c in COLONNES_LISTE if c not in ("mois_payes", "total_verse", "reste_du")]
    with django_assert_max_num_queries(3):
        assert len(list(lignes(preparer(Membre.objects.all(), J), module1, J))) == 34
    with django_assert_max_num_queries(10):
        assert len(list(lignes(preparer(Membre.objects.all(), J), list(COLONNES_LISTE), J))) == 34


def test_annee_future_refusee(monde):
    assert not _form(U(Niveau.NATIONAL), annee=J.year + 50).is_valid()
