from apps.cotisations.templatetags.cotisations import mois_court


def test_mois_courts_distincts():
    noms = [
        "janvier", "février", "mars", "avril", "mai", "juin",
        "juillet", "août", "septembre", "octobre", "novembre", "décembre",
    ]  # fmt: skip
    courts = [mois_court(n) for n in noms]
    assert courts == [
        "Janv", "Févr", "Mars", "Avr", "Mai", "Juin",
        "Juil", "Août", "Sept", "Oct", "Nov", "Déc",
    ]  # fmt: skip
    assert mois_court("Juillet") == "Juil"
