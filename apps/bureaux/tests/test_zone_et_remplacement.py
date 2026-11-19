"""Bureaux (décisions du 19/11/2026) : on ne nomme que des membres actifs de la zone ; un
titulaire se remplace seul ; un poste vacant se pourvoit seul ; les mandats incohérents se
ferment."""

import datetime

import pytest

from apps.bureaux.models import Fonction, Mandat
from apps.bureaux.perimetre import Unite
from apps.bureaux.services import (
    InstallationRefusee,
    installer_bureau,
    mandats_incoherents,
    pourvoir_poste,
    remplacer_titulaire,
)

D = datetime.date(2026, 1, 10)


def _f(nom):
    return Fonction.objects.get(nom=nom)


def test_paroisse_refuse_un_membre_d_une_autre_paroisse(monde, compte_technique):
    with pytest.raises(InstallationRefusee, match="P2"):
        installer_bureau(
            unite=Unite("paroisse", monde["P1"]),
            titulaires={_f("Chef d'Unité paroissiale"): monde["m2"]},
            date_debut=D,
            par=compte_technique,
        )


def test_circuit_refuse_un_membre_d_un_autre_circuit(monde, compte_technique):
    with pytest.raises(InstallationRefusee, match="circuit"):
        installer_bureau(
            unite=Unite("circuit", monde["Ekpe A"]),
            titulaires={_f("Chef de Section de Circuit"): monde["m3"]},  # P3 : Ekpe B
            date_debut=D,
            par=compte_technique,
        )


def test_region_refuse_un_membre_d_une_autre_region(monde, compte_technique):
    with pytest.raises(InstallationRefusee, match="région"):
        installer_bureau(
            unite=Unite("region", monde["HOULENOU"]),
            titulaires={_f("Coordinateur régional"): monde["m4"]},  # P4 : WEME
            date_debut=D,
            par=compte_technique,
        )


def test_zone_acceptee_et_national_ouvert_a_tous(monde, compte_technique):
    installer_bureau(
        unite=Unite("region", monde["HOULENOU"]),
        titulaires={_f("Coordinateur régional"): monde["m3"]},  # P3 est en HOULENOU
        date_debut=D,
        par=compte_technique,
    )
    installer_bureau(
        unite=Unite("national", None),
        titulaires={_f("Président"): monde["m4"], _f("Secrétaire national"): monde["m1"]},
        date_debut=D,
        par=compte_technique,
    )


@pytest.fixture
def bureau_p1(monde, compte_technique, nouveau_membre):
    a = nouveau_membre(monde["P1"], "Agossou")
    b = nouveau_membre(monde["P1"], "Bada")
    mandats = installer_bureau(
        unite=Unite("paroisse", monde["P1"]),
        titulaires={_f("Chef d'Unité paroissiale"): a, _f("Trésorier paroissial"): b},
        date_debut=D,
        par=compte_technique,
    )
    return {m.fonction.nom: m for m in mandats}


def test_remplacer_un_titulaire_seul(monde, compte_technique, nouveau_membre, bureau_p1):
    ancien = bureau_p1["Trésorier paroissial"]
    chef = bureau_p1["Chef d'Unité paroissiale"]
    c = nouveau_membre(monde["P1"], "Capo")
    jour = datetime.date(2026, 6, 1)
    nouveau = remplacer_titulaire(
        mandat=ancien, date=jour, motif="demission", remplacant=c, par=compte_technique
    )
    ancien.refresh_from_db()
    chef.refresh_from_db()
    assert ancien.date_fin == jour
    assert chef.date_fin is None and chef.date_debut == D  # les autres ne bougent pas
    assert nouveau.membre == c and nouveau.date_debut == jour
    assert nouveau.date_fin_prevue == ancien.date_fin_prevue  # il termine le mandat en cours


def test_remplacer_sans_remplacant_laisse_le_poste_vacant(compte_technique, bureau_p1):
    ancien = bureau_p1["Trésorier paroissial"]
    assert (
        remplacer_titulaire(
            mandat=ancien,
            date=datetime.date(2026, 6, 1),
            motif="voyage",
            remplacant=None,
            par=compte_technique,
        )
        is None
    )
    ancien.refresh_from_db()
    assert ancien.date_fin == datetime.date(2026, 6, 1)


def test_remplacant_hors_zone_refuse(monde, compte_technique, bureau_p1):
    with pytest.raises(InstallationRefusee):
        remplacer_titulaire(
            mandat=bureau_p1["Trésorier paroissial"],
            date=datetime.date(2026, 6, 1),
            motif="demission",
            remplacant=monde["m4"],
            par=compte_technique,
        )
    bureau_p1["Trésorier paroissial"].refresh_from_db()
    assert bureau_p1["Trésorier paroissial"].date_fin is None  # rien n'a changé


def test_pourvoir_un_poste_vacant(monde, compte_technique, nouveau_membre, bureau_p1):
    s = nouveau_membre(monde["P1"], "Sossa")
    jour = datetime.date(2026, 3, 1)
    m = pourvoir_poste(
        unite=Unite("paroisse", monde["P1"]),
        fonction=_f("Secrétaire paroissial"),
        membre=s,
        date_debut=jour,
        par=compte_technique,
    )
    assert m.date_debut == jour
    assert m.date_fin_prevue == bureau_p1["Chef d'Unité paroissiale"].date_fin_prevue
    assert Mandat.objects.en_cours(jour).filter(paroisse=monde["P1"]).count() == 3
    with pytest.raises(InstallationRefusee, match="déjà"):
        pourvoir_poste(
            unite=Unite("paroisse", monde["P1"]),
            fonction=_f("Secrétaire paroissial"),
            membre=monde["m1"],
            date_debut=jour,
            par=compte_technique,
        )


def test_mandats_incoherents(monde, donner_mandat):
    # Créé « à la main » (comme sur le site d'essai avant la correction) : m4 (WEME) chef d'Ekpe A.
    faux = donner_mandat(monde["m4"], "Chef de Section de Circuit", monde["Ekpe A"])
    assert faux in [m for m, _raison in mandats_incoherents()]
    assert monde["sec_p1"].mandats.first() not in [m for m, _r in mandats_incoherents()]


def test_pages_remplacer_pourvoir_et_mandats_a_corriger(
    client_technique, monde, nouveau_membre, bureau_p1, donner_mandat
):
    cle = f"paroisse-{monde['P1'].pk}"
    page = client_technique.get(f"/bureau/bn/bureaux/{cle}/").content.decode()
    tres = bureau_p1["Trésorier paroissial"]
    assert f"/bureau/bn/bureaux/{cle}/remplacer/{tres.pk}/" in page
    assert f"/bureau/bn/bureaux/{cle}/pourvoir/" in page
    c = nouveau_membre(monde["P1"], "Capo")
    r = client_technique.post(
        f"/bureau/bn/bureaux/{cle}/remplacer/{tres.pk}/",
        {"date": "2026-06-01", "motif": "demission", "matricule": c.matricule},
    )
    assert r.status_code == 302
    assert Mandat.objects.en_cours(datetime.date(2026, 6, 2)).filter(membre=c).exists()
    page = client_technique.get(f"/bureau/bn/bureaux/{cle}/pourvoir/").content.decode()
    assert "Secrétaire paroissial" in page and "Trésorier paroissial" not in page

    faux = donner_mandat(monde["m4"], "Chef de Section de Circuit", monde["Ekpe A"])
    page = client_technique.get("/bureau/bn/mandats-a-corriger/").content.decode()
    assert monde["m4"].matricule in page
    r = client_technique.post(f"/bureau/bn/mandats-a-corriger/{faux.pk}/fermer/")
    faux.refresh_from_db()
    assert r.status_code == 302 and faux.date_fin is not None
    assert (
        monde["m4"].matricule
        not in client_technique.get("/bureau/bn/mandats-a-corriger/").content.decode()
    )
