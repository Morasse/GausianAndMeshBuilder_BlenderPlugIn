# SPDX-License-Identifier: Apache-2.0
"""Entrées du pipeline.

Une seule source à P2 : des images déjà développées. Le DNG reviendra ici comme
**une source parmi d'autres** derrière la même interface, et non comme le seul
chemin d'entrée — c'est ce qui rend son report sans conséquence.
"""

from gamb_engine.ingest import images

__all__ = ["images"]
