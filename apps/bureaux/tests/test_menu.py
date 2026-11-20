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


def _tous(groupe):
    """Liens d'un groupe, y compris ceux des entrées par bureau (sous-groupes)."""
    for element in groupe.liens:
        yield from getattr(element, "liens", [element]) if hasattr(element, "titre") else [element]


def _actifs(menu):
    return [(g.titre, lien.libelle) for g in menu for lien in _tous(g) if lien.actif]


def test_menu_bn_groupes_sans_doublon(compte_technique):
    menu = _menu(compte_technique)
    assert _titres(menu) == [
        "Mon espace",
        "Mon bureau",
        "Listes et statistiques",
        "Grades",
        "Cotisations mensuelles",
        "Trésorerie",
        "Événements",
        "Courrier",
        "Bureaux et droits",
        "Contrôle",
    ]
    adresses = [(lien.url, lien.libelle) for g in menu for lien in _tous(g)]
    assert len(adresses) == len(set(adresses))
    gestion = next(g for g in menu if g.titre == "Mon bureau")
    assert [lien.libelle for lien in gestion.liens if lien.libelle != "Vérifier un membre"] == [
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
    assert _actifs(menu) == [("Mon bureau", "Tous les membres")]
    ouverts = [g.titre for g in menu if g.ouvert]
    assert ouverts == ["Mon bureau"]
    # Fiche BN d'un membre : rattachée aussi à « Tous les membres ».
    menu = _menu(compte_technique, f"/membres/bn/{m1.matricule}/")
    assert _actifs(menu) == [("Mon bureau", "Tous les membres")]
    # Le plus long préfixe gagne : « Enregistrer un membre », pas « Tous les membres ».
    menu = _menu(compte_technique, "/membres/bn/enregistrer/")
    assert _actifs(menu) == [("Mon bureau", "Enregistrer un membre")]
    menu = _menu(compte_technique, "/cotisations/national/parts/")
    assert _actifs(menu) == [("Cotisations mensuelles", "Parts reçues")]


def test_eligibles_distingues_des_listes(compte_technique, monde):
    sec = monde["sec_p1"].compte
    url = f"/bureau/paroisse-{monde['P1'].pk}/listes/"
    menu = _menu(sec, url, envoye="1", eligible_a="5")
    assert _actifs(menu) == [("Grades", "Éligibles au grade visé")]
    assert _actifs(_menu(sec, url)) == [("Listes et statistiques", "Listes")]
    # Le BN a sa propre page « Éligibles au grade visé » (sessions de test).
    menu = _menu(compte_technique, "/grades/bn/eligibles/", grade="5")
    assert _actifs(menu) == [("Grades", "Éligibles au grade visé")]


def test_accueil_seulement_sur_la_page_d_accueil(compte_technique):
    assert _actifs(_menu(compte_technique, "/")) == [("Mon espace", "Ma page")]
    assert _actifs(_menu(compte_technique, "/page-inconnue/")) == []


def test_menu_bureau_paroisse(monde):
    menu = _menu(monde["sec_p1"].compte)
    titres = _titres(menu)
    assert titres[:2] == ["Mon espace", "Mon bureau"]
    assert "Listes et statistiques" in titres and "Grades" in titres
    assert "Bureaux et droits" not in titres and "Contrôle" not in titres
    assert "Événements" not in titres and "Courrier" in titres
    bureau = next(g for g in menu if g.titre == "Mon bureau")
    # « Vérifier un membre » d'abord (décision du 19/11/2026).
    assert [lien.libelle for lien in bureau.liens] == [
        "Vérifier un membre",
        "Membres",
        "Anciens membres",
        "Demandes",
    ]


def test_menu_membre_simple(monde):
    menu = _menu(monde["m1"].compte)
    assert _titres(menu) == ["Mon espace"]
    assert "Mes courriers" in [lien.libelle for lien in menu[0].liens]


def test_rendu_groupes_repliables(client_technique, monde):
    r = client_technique.get(f"/bureau/national/membres/{monde['m1'].matricule}/")
    html = unescape(r.content.decode())
    debut = html.index('<nav class="menu"')
    menu = html[debut : html.index("</nav>", debut)]
    assert menu.count("<details") == 10
    assert menu.count('<details class="menu__groupe" open') == 1
    assert 'class="actif" aria-current="page">Tous les membres' in menu


def test_bn_avec_un_mandat_local_une_entree_par_bureau(monde, donner_mandat):
    """Décision du 19/11/2026 : dans chaque rubrique, une entrée par bureau, avec son nom."""
    from apps.bureaux.menu import SousGroupe

    sec = monde["sec_p1"]
    donner_mandat(sec, "Secrétaire national")
    menu = _menu(sec.compte)
    for titre in ("Mon bureau", "Listes et statistiques", "Courrier"):
        groupe = next(g for g in menu if g.titre == titre)
        bureaux = [e.titre for e in groupe.liens if isinstance(e, SousGroupe)]
        assert bureaux == ["Bureau National de Commandement", "Unité paroissiale — P1"], titre
    bureau = next(g for g in menu if g.titre == "Mon bureau")
    assert bureau.liens[0].libelle == "Vérifier un membre"
    p1 = bureau.liens[-1]
    assert [lien.libelle for lien in p1.liens] == ["Membres", "Anciens membres", "Demandes"]
    # La page ouverte déplie le bon bureau.
    menu = _menu(sec.compte, f"/bureau/paroisse-{monde['P1'].pk}/membres/")
    bureau = next(g for g in menu if g.titre == "Mon bureau")
    assert [e.titre for e in bureau.liens if getattr(e, "ouvert", False)] == [
        "Unité paroissiale — P1"
    ]
