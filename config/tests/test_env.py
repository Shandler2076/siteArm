import os

from config.env import charger_env


def test_charger_env(tmp_path, monkeypatch):
    f = tmp_path / ".env"
    f.write_text(
        '# commentaire\n\nA_TEST_UN=valeur\nA_TEST_DEUX = "avec espaces"\n'
        "A_TEST_TROIS='simple'\nA_TEST_EXISTANT=fichier\nligne sans egal\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("A_TEST_EXISTANT", "environnement")
    for nom in ("A_TEST_UN", "A_TEST_DEUX", "A_TEST_TROIS"):
        monkeypatch.delenv(nom, raising=False)
    lus = charger_env(f)
    assert os.environ["A_TEST_UN"] == "valeur"
    assert os.environ["A_TEST_DEUX"] == "avec espaces"
    assert os.environ["A_TEST_TROIS"] == "simple"
    assert os.environ["A_TEST_EXISTANT"] == "environnement"  # l'environnement a priorité
    assert set(lus) == {"A_TEST_UN", "A_TEST_DEUX", "A_TEST_TROIS"}
    for nom in lus:
        monkeypatch.delenv(nom)


def test_fichier_absent(tmp_path):
    assert charger_env(tmp_path / "absent.env") == []
