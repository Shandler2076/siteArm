"""Politique de sécurité des contenus (CSP) : seul le JavaScript du site s'exécute ; un script
injecté (faille XSS) serait bloqué par le navigateur."""

import re
from pathlib import Path

import pytest

GABARITS = Path(__file__).resolve().parents[3] / "templates"


def test_aucun_gestionnaire_en_ligne_dans_les_gabarits():
    """onclick=, onsubmit=… sont interdits par la CSP : tout passe par static/js/site.js."""
    fautifs = []
    for f in GABARITS.rglob("*.html"):
        for n, ligne in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
            if re.search(r"\son[a-z]+=[\"']", ligne) or "javascript:" in ligne:
                fautifs.append(f"{f.relative_to(GABARITS)}:{n}")
    assert not fautifs, fautifs


def test_scripts_en_ligne_portent_le_jeton():
    fautifs = []
    for f in GABARITS.rglob("*.html"):
        for balise in re.findall(r"<script\b[^>]*>", f.read_text(encoding="utf-8")):
            if "src=" in balise or "application/json" in balise:
                continue
            if 'nonce="{{ request.csp_nonce }}"' not in balise:
                fautifs.append(f"{f.relative_to(GABARITS)} : {balise}")
    assert not fautifs, fautifs


@pytest.mark.django_db
def test_entete_csp(client):
    r = client.get("/")
    csp = r.headers["Content-Security-Policy"]
    jeton = re.search(r"'nonce-([^']+)'", csp).group(1)
    script_src = re.search(r"script-src ([^;]+)", csp).group(1)
    assert "'unsafe-inline'" not in script_src and "'self'" in script_src
    for directive in ("object-src 'none'", "frame-ancestors 'none'", "base-uri 'self'"):
        assert directive in csp
    page = r.content.decode()
    for balise in re.findall(r"<script\b[^>]*>", page):
        if "src=" not in balise and "application/json" not in balise:
            assert f'nonce="{jeton}"' in balise
    # Un jeton neuf à chaque page.
    assert jeton not in client.get("/").headers["Content-Security-Policy"]
