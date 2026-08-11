# SPDX-License-Identifier: Apache-2.0
"""Sidecar de GAMB.

Le moteur tourne dans son propre processus, hors du Python embarque de Blender.
Il porte torch, gsplat et les modeles ; l'addon ne porte rien de lourd.

Contenu a P1 :

    naming      table de nommage, source de verite des noms du projet
    proc        sondes externes, avec delai de garde et sans console noire
    bootstrap   decouverte de l'interpreteur : chercher avant d'installer
    machine     GPU, VRAM et chaine de compilation CUDA — sans torch
    server      FastAPI, route /health
    cli         `gamb doctor`, `gamb serve`, `gamb health`

Ce module ne reexporte que `naming` : importer `server` ici tirerait FastAPI a
chaque `import gamb_engine`, y compris pour un simple `gamb doctor`.
"""

from gamb_engine import naming

__all__ = ["naming"]
