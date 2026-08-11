# SPDX-License-Identifier: Apache-2.0
"""Poses de caméra.

À P3, une seule source : un modèle COLMAP déjà présent dans le projet — celui
du dataset synthétique, dont les poses sont **exactes** plutôt qu'estimées.

L'exécution de COLMAP elle-même viendra plus tard, avec `pycolmap`. Ce n'est
pas un raccourci : tant qu'on valide l'entraîneur, des poses estimées
ajouteraient une variable dont on ne saurait pas la séparer d'un bug de
l'entraîneur.
"""

from gamb_engine.poses import colmap

__all__ = ["colmap"]
