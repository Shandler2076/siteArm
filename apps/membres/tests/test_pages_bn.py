
from apps.comptes.models import Compte
from apps.membres.models import Membre

URL = "/membres/bn/enregistrer/"


def _post(client, paroisse, **extra):
    d = {
        "nom": "Hounkpè", "prenoms": "Jean-Marc", "sexe": "M", "telephone": "0197000000",
        "date_naissance": "1990-05-01", "annee_integration": "2015",
        "paroisse_integration": paroisse.pk, "categorie": "actif",
    }
    d.update(extra)
    return client.post(URL, d)


def test_refuse_sans_permission(client, db):
    client.force_login(
        Compte.objects.create_user("X", "MotDePasse!2026", doit_changer_mot_de_passe=False)
    )
    assert client.get(URL).status_code == 403


def test_categorie_presente_et_preselectionnee(client, bn, paroisse):
    html = client.get(URL).content.decode()
    assert 'name="categorie"' in html
    assert "Membre actif" in html and "Membre d&#x27;honneur" in html
    assert "Membre sympathisant" in html
    assert 'value="actif" required id="id_categorie_0" checked' in html


def test_enregistrement_redirige_vers_la_fiche(client, bn, paroisse):
    r = _post(client, paroisse)
    assert r.status_code == 302 and r.url == "/membres/bn/2015-03AS-0001/"
    m = Membre.objects.get()
    assert m.enregistre_par == bn and m.categorie == "actif"
    assert "2015-03AS-0001" in client.get(r.url).content.decode()


def test_categorie_choisie(client, bn, paroisse):
    _post(client, paroisse, categorie="sympathisant")
    assert Membre.objects.get().categorie == "sympathisant"


def test_doublon_demande_confirmation(client, bn, paroisse):
    _post(client, paroisse)
    r = _post(client, paroisse, nom="HOUNKPE", prenoms="jean marc")
    assert r.status_code == 200 and "Doublons possibles" in r.content.decode()
    assert Membre.objects.count() == 1
    r = _post(client, paroisse, nom="HOUNKPE", prenoms="jean marc", confirmer_malgre_doublon="on")
    assert r.status_code == 302 and Membre.objects.count() == 2


def test_capacite_atteinte_message(client, bn, paroisse):
    from apps.membres.models import CompteurMatricule

    CompteurMatricule.objects.create(annee=2015, region=paroisse.region, dernier_numero=9999)
    r = _post(client, paroisse)
    assert r.status_code == 200 and "9 999" in r.content.decode()
    assert Membre.objects.count() == 0


def test_paroisses_fermees_absentes(client, bn, paroisse):
    from apps.organisation.models import Paroisse

    fermee = Paroisse.objects.create(circuit=paroisse.circuit, nom="Paroisse fermée X")
    fermee.fermer()
    assert "Paroisse fermée X" not in client.get(URL).content.decode()


def test_chaque_champ_affiche_une_seule_fois(client, bn, paroisse):
    html = client.get(URL).content.decode()
    for nom in ["nom", "prenoms", "telephone", "urgence_nom", "urgence_telephone", "categorie"]:
        attendu = 3 if nom == "categorie" else 1
        assert html.count(f'name="{nom}"') == attendu, nom
