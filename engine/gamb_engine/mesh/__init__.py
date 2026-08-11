# SPDX-License-Identifier: Apache-2.0
"""Extraction de mesh.

**Mode Fast d'abord, et Open3D seulement.** La spec le dit et la recherche du
2026-08-11 l'a confirmé : six des sept dépôts de meshing surfel (SuGaR, 2DGS,
GOF, MILo, GS-2M, Proxy-GS) sont sous licence INRIA **non commerciale**. Open3D
est MIT, fait du TSDF et du marching cubes très correctement, et donne une
baseline avant de savoir si le mode Quality vaut son coût — juridique compris.

Rappel du piège n°1 de la spec : **le mesh et le splat photoréaliste ne sortent
pas du même run.** Ce module extrait une surface *depuis* un splat entraîné ;
il ne prétend pas produire le meilleur des deux.
"""

from gamb_engine.mesh import tsdf

__all__ = ["tsdf"]
