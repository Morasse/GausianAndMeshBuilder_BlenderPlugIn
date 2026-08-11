# SPDX-License-Identifier: Apache-2.0
"""Gardes sur l'extraction de mesh et sur l'aller-retour PLY.

Le test qui compte est `test_aller_retour_ply` : un run est **immuable**, donc
on doit pouvoir y revenir des mois plus tard pour en extraire une surface sans
réentraîner. Si le lecteur et l'écrivain divergent, la relecture donne un nuage
d'apparence correcte et de densité absurde — les valeurs sont stockées
pré-activation, `scale` en log et `opacity` en logit.
"""

import pytest

from gamb_engine.mesh import tsdf
from gamb_engine.train import gsplat_runner

torch = pytest.importorskip("torch")


def test_le_module_declare_des_defauts_raisonnables():
    assert 0.0 < tsdf.TAILLE_VOXEL_PAR_DEFAUT < 1.0
    # Une troncature de quelques voxels : trop courte, les surfaces se percent ;
    # trop longue, les cloisons fines fusionnent.
    assert 2.0 <= tsdf.FACTEUR_TRONCATURE <= 8.0


def test_aller_retour_ply(tmp_path):
    """Écrire puis relire doit rendre exactement les mêmes tenseurs."""
    nombre, bandes = 7, 15
    torch.manual_seed(0)
    origine = {
        "means": torch.randn(nombre, 3),
        "sh0": torch.randn(nombre, 1, 3),
        "shN": torch.randn(nombre, bandes, 3),
        "opacities": torch.randn(nombre),
        "scales": torch.randn(nombre, 3),
        "quats": torch.randn(nombre, 4),
    }
    chemin = tmp_path / "point_cloud.ply"
    gsplat_runner.ecrire_ply(chemin, origine, torch)

    relu = gsplat_runner.lire_ply(chemin, torch)

    for cle, attendu in origine.items():
        assert relu[cle].shape == attendu.shape, f"{cle} : forme differente"
        assert torch.allclose(relu[cle], attendu, atol=1e-6), f"{cle} : valeurs differentes"


def test_le_degre_sh_se_deduit_du_nombre_de_bandes(tmp_path):
    """La CLI en a besoin : le PLY ne stocke pas le degré, seulement les bandes."""
    for degre in (0, 1, 3):
        bandes = (degre + 1) ** 2 - 1
        parametres = {
            "means": torch.zeros(2, 3),
            "sh0": torch.zeros(2, 1, 3),
            "shN": torch.zeros(2, bandes, 3),
            "opacities": torch.zeros(2),
            "scales": torch.zeros(2, 3),
            "quats": torch.zeros(2, 4),
        }
        chemin = tmp_path / f"deg{degre}.ply"
        gsplat_runner.ecrire_ply(chemin, parametres, torch)
        relu = gsplat_runner.lire_ply(chemin, torch)

        deduit = int(round((relu["shN"].shape[1] + 1) ** 0.5)) - 1
        assert deduit == degre
