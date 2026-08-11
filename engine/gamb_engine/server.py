# SPDX-License-Identifier: Apache-2.0
"""Serveur du sidecar : REST pour les commandes, WebSocket pour la progression.

A P1, une seule route : `/health`. C'est deja la route la plus importante du
projet — c'est elle qui permet a l'addon d'afficher un etat honnete au lieu de
lancer un job dans le vide.

Elle repond **sans avoir charge le moindre modele**. La VRAM vient de
`nvidia-smi`, pas de torch : le panneau Blender doit s'allumer en quelques
millisecondes, pas apres trois secondes d'import CUDA.
"""

from __future__ import annotations

import sys
from typing import Any

from fastapi import FastAPI

from gamb_engine import machine, naming

VERSION = "0.1.0"

# Boucle locale uniquement. Le sidecar n'a aucune authentification a P1 :
# l'exposer sur une interface reseau ouvrirait une execution de code arbitraire
# a qui passe par la. Le mode distant de la spec (Q7) devra apporter sa propre
# reponse a cette question.
HOTE_DEFAUT = "127.0.0.1"
PORT_DEFAUT = 8765


def etat() -> dict[str, Any]:
    """Charge utile de /health. Extraite pour etre testable sans serveur."""
    gpu = machine.gpu_principal()
    return {
        "statut": "online",
        "moteur": naming.ENGINE_DISTRIBUTION,
        "version": VERSION,
        "python": ".".join(str(n) for n in sys.version_info[:3]),
        "gpu": None
        if gpu is None
        else {
            "nom": gpu.nom,
            "driver": gpu.driver,
            "vram_totale_go": gpu.vram_totale_go,
            "vram_libre_go": gpu.vram_libre_go,
        },
        # Place tenue pour P5 : la queue est sequentielle, un seul job GPU a la
        # fois, donc ce champ est un objet ou null, jamais une liste.
        "job_courant": None,
    }


def creer_application() -> FastAPI:
    application = FastAPI(title=naming.EXTENSION_NAME, version=VERSION)

    @application.get("/health")
    def health() -> dict[str, Any]:
        return etat()

    return application


app = creer_application()


def servir(hote: str = HOTE_DEFAUT, port: int = PORT_DEFAUT) -> None:
    """Demarre le serveur. Import d'uvicorn differe : `gamb doctor` n'en a pas besoin."""
    import uvicorn

    uvicorn.run(app, host=hote, port=port, log_level="info")
