"""Menu principal : groupes thématiques sans doublon, rubrique active, groupes repliables."""

from html import unescape

from django.test import RequestFactory


def _menu(compte, chemin="/", **get):
    from apps.bureaux.menu import construire_menu

    requete = RequestFactory().get(chemin, get)
    requete.user = compte
    return construire_menu(requete)


def _titres(menu):
    return [g.titre for g in menu]


def _actifs(menu):
    return [(g.titre, lien.libelle) for g in menu for lien in g.liens if lien.actif]


def test_menu_bn_groupes_sans_doublon(compte_technique):
    menu = _menu(compte_technique)
    assert _titres(menu) == [
        "Mon espace",
        "Gestion des membres (BN)",
        "Listes et statistiques",
        "Grades",
        "Cotisations mensuelles",
        "Événements",
        "Bureaux et droits",
        "Contrôle",
    ]
    adresses = [(lien.url, lien.libelle) for g in menu for lien in g.liens]
    assert len(adresses) == len(set(adresses))
    libelles = [lien.libelle for g in menu for lien in g.liens]
    assert len(libelles) == len(set(libelles))
    gestion = next(g for g in menu if g.titre == "Gestion des membres (BN)")
    assert [lien.libelle for lien in gestion.liens] == [
        "Tous les membres",
        "Enregistrer un membre",
        "Enregistrer par lots",
        "Photos à valider",
        "Demandes",
        "Décisions à prendre",
    ]


def test_menu_rubrique_active_sur_sous_page(compte_technique, monde):
    m1 = monde["m1"]
    menu = _menu(compte_technique, f"/bureau/national/membres/{m1.matricule}/")
    assert _actifs(menu) == [("Gestion des membres (BN)", "Tous les membres")]
    ouverts = [g.titre for g in menu if g.ouvert]
    assert ouverts == ["Gestion des membres (BN)"]
    # Fiche BN d'un membre : rattachée aussi à « Tous les membres ».
    menu = _menu(compte_technique, f"/membres/bn/{m1.matricule}/")
    assert _actifs(menu) == [("Gestion des membres (BN)", "Tous les membres")]
    # Le plus long préfixe gagne : « Enregistrer un membre », pas « Tous les membres ».
    menu = _menu(compte_technique, "/membres/bn/enregistrer/")
    assert _actifs(menu) == [("Gestion des membres (BN)", "Enregistrer un membre")]
    menu = _menu(compte_technique, "/cotisations/national/parts/")
    assert _actifs(menu) == [("Cotisations mensuelles", "Parts reçues")]


def test_eligibles_distingues_des_listes(compte_technique):
    menu = _menu(compte_technique, "/bureau/national/listes/", envoye="1", eligible="on")
    assert _actifs(menu) == [("Grades", "Éligibles au grade suivant")]
    menu = _menu(compte_technique, "/bureau/national/listes/")
    assert _actifs(menu) == [("Listes et statistiques", "Listes")]


def test_accueil_seulement_sur_la_page_d_accueil(compte_technique):
    assert _actifs(_menu(compte_technique, "/")) == [("Mon espace", "Accueil")]
    assert _actifs(_menu(compte_technique, "/page-inconnue/")) == []


def test_menu_bureau_paroisse(monde):
    menu = _menu(monde["sec_p1"].compte)
    titres = _titres(menu)
    assert titres[:2] == ["Mon espace", "Mon bureau"]
    assert "Listes et statistiques" in titres and "Grades" in titres
    assert "Bureaux et droits" not in titres and "Contrôle" not in titres
    assert "Événements" not in titres
    bureau = next(g for g in menu if g.titre == "Mon bureau")
    assert [lien.libelle for lien in bureau.liens] == ["Membres", "Anciens membres", "Demandes"]


def test_menu_membre_simple(monde):
    assert _titres(_menu(monde["m1"].compte)) == ["Mon espace"]


def test_rendu_groupes_repliables(client_technique, monde):
    r = client_technique.get(f"/bureau/national/membres/{monde['m1'].matricule}/")
    html = unescape(r.content.decode())
    debut = html.index('<nav class="menu"')
    menu = html[debut : html.index("</nav>", debut)]
    assert menu.count("<details") == 8
    assert menu.count("<details class=\"menu__groupe\" open") == 1
    assert 'class="actif" aria-current="page">Tous les membres' in menu
