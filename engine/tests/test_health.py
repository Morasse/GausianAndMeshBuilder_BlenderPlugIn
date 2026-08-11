# SPDX-License-Identifier: Apache-2.0
"""La route /health, et la contrainte qui la rend utile.

`/health` doit repondre **sans avoir charge le moindre modele**. Le test
`test_health_ne_charge_pas_torch` est la pour ca : le jour ou quelqu'un
importera torch pour lire la VRAM, le panneau Blender mettra trois secondes a
s'allumer et personne ne saura pourquoi.
"""

import sys

from fastapi.testclient import TestClient

from gamb_engine import server


def test_etat_expose_les_champs_attendus():
    charge = server.etat()
    assert charge["statut"] == "online"
    assert charge["version"] == server.VERSION
    assert "python" in charge
    # Un seul job GPU a la fois : ce champ est un objet ou null, jamais une liste.
    assert charge["job_courant"] is None
    assert not isinstance(charge["job_courant"], list)


def test_health_repond_200():
    with TestClient(server.creer_application()) as client:
        reponse = client.get("/health")
    assert reponse.status_code == 200
    assert reponse.json()["statut"] == "online"


def test_le_gpu_est_absent_ou_complet():
    """Pas de demi-reponse : soit null, soit les quatre champs."""
    gpu = server.etat()["gpu"]
    if gpu is not None:
        for champ in ("nom", "driver", "vram_totale_go", "vram_libre_go"):
            assert champ in gpu


def test_health_ne_charge_pas_torch():
    server.etat()
    assert "torch" not in sys.modules, (
        "/health a charge torch. La VRAM doit venir de nvidia-smi : le panneau "
        "Blender doit s'allumer en millisecondes, pas apres un import CUDA."
    )


def test_le_serveur_ecoute_en_local_par_defaut():
    """Aucune authentification a P1 : l'exposer sur le reseau serait une RCE."""
    assert server.HOTE_DEFAUT == "127.0.0.1"
