# SPDX-License-Identifier: Apache-2.0
"""Sidecar de GAMB.

Le moteur tourne dans son propre processus, hors du Python embarque de Blender.
Il porte torch, gsplat et les modeles ; l'addon ne porte rien de lourd.

A P0 ce package ne contient que la table de nommage. La logique metier arrive
a partir de P1.
"""

from gamb_engine import naming

__all__ = ["naming"]
