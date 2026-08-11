# SPDX-License-Identifier: Apache-2.0
"""Gardes sur les modules de l'addon testables hors Blender.

Trois modules de l'addon sont ecrits sans `bpy` a dessein — `client`, `lanceur`
et `state`. C'est ce qui permet de tester ici la partie la plus facile a casser
de l'extension sans lancer Blender.

Le test le plus important est `test_ladresse_du_client_suit_le_serveur` : le
port est duplique entre le moteur et l'addon parce qu'ils ne peuvent pas
s'importer l'un l'autre. La duplication est donc verifiee, comme celle du
manifeste et celle de naming.py.
"""

from pathlib import Path

from gamb_engine import server


def test_ladresse_du_client_suit_le_serveur(client_addon):
    assert client_addon.HOTE_DEFAUT == server.HOTE_DEFAUT
    assert client_addon.PORT_DEFAUT == server.PORT_DEFAUT


def test_le_client_naddresse_pas_bpy(client_addon):
    """S'il importait bpy, le chargement par chemin aurait deja echoue."""
    assert client_addon.url_base("127.0.0.1", 8765) == "http://127.0.0.1:8765"


def test_sante_renvoie_hors_ligne_sans_lever(client_addon):
    """Cas nominal quand le moteur n'est pas demarre — jamais une exception.

    Le port 1 est reserve et rien n'y ecoute : l'appel doit echouer proprement,
    parce que l'appelant reel est un timer d'interface qu'une exception
    desenregistrerait en silence.
    """
    charge, raison = client_addon.sante("127.0.0.1", 1, delai_s=0.5)
    assert charge is None
    assert raison


def test_le_resume_affiche_la_vram(client_addon):
    charge = {
        "statut": "online",
        "gpu": {"nom": "RTX 4080", "vram_totale_go": 16.0, "vram_libre_go": 15.2},
    }
    resume = client_addon.resume(charge)
    assert "online" in resume
    assert "15.2" in resume
    assert "16.0" in resume


def test_le_resume_tient_sans_gpu(client_addon):
    assert "hors ligne" in client_addon.resume(None)
    assert "aucun GPU" in client_addon.resume({"statut": "online", "gpu": None})


def test_la_commande_de_demarrage_prefere_le_python_explicite(lanceur_addon, tmp_path):
    faux_python = tmp_path / "python.exe"
    faux_python.write_text("", encoding="utf-8")

    commande = lanceur_addon.commande_demarrage(tmp_path, "127.0.0.1", 8765, faux_python)

    assert commande is not None
    assert commande[0] == str(faux_python)
    assert commande[1:3] == ["-m", "gamb_engine.cli"]
    assert "serve" in commande


def test_la_commande_de_demarrage_passe_ladresse(lanceur_addon, tmp_path):
    faux_python = tmp_path / "python.exe"
    faux_python.write_text("", encoding="utf-8")

    commande = lanceur_addon.commande_demarrage(tmp_path, "127.0.0.1", 9999, faux_python)

    assert "--port" in commande
    assert commande[commande.index("--port") + 1] == "9999"


def test_la_commande_de_demarrage_abandonne_proprement(lanceur_addon, monkeypatch):
    """Ni uv ni python : renvoie None au lieu de fabriquer une commande cassee."""
    monkeypatch.setattr(lanceur_addon.shutil, "which", lambda _: None)
    assert lanceur_addon.commande_demarrage(Path("/inexistant"), "127.0.0.1", 8765) is None
