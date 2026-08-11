# SPDX-License-Identifier: Apache-2.0
"""Mesh mode Fast : profondeur rendue depuis le splat, fusion TSDF, marching cubes.

Le chemin est volontairement conventionnel. gsplat sait rendre une carte de
profondeur en même temps que la couleur (`render_mode="RGB+ED"`), Open3D sait
fusionner des RGB-D en volume TSDF et en extraire une surface. Il n'y a rien à
inventer ici, et c'est précisément l'intérêt : ce mesh sert de **proxy**, à
corriger dans Blender puis à réinjecter comme prior géométrique. Sa qualité
absolue compte moins que le fait qu'il arrive vite et sans dette juridique.

`ED` et non `D` : gsplat propose la profondeur *attendue* (`ED`, normalisée par
l'alpha accumulé) et la profondeur *accumulée* (`D`). Seule la première est une
distance ; la seconde est pondérée par l'opacité et donne un TSDF creux.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

# Un voxel plus fin que ça sur une scène d'ambiance donne surtout du bruit
# mémorisé ; plus grossier, on perd les arêtes.
TAILLE_VOXEL_PAR_DEFAUT = 0.02

# Troncature du TSDF : classiquement quelques voxels. Trop court, les surfaces
# se percent ; trop long, les fines cloisons fusionnent entre elles.
FACTEUR_TRONCATURE = 4.0


@dataclass
class Resultat:
    chemin: Path
    sommets: int
    triangles: int
    vues_integrees: int


def _rendre_rgbd(parametres, dataset, indice, degre_sh: int, torch):
    """Couleur et profondeur d'une vue, depuis le splat entraîné."""
    from gsplat import rasterization

    couleurs = torch.cat([parametres["sh0"], parametres["shN"]], dim=1)
    rendus, _, _ = rasterization(
        means=parametres["means"],
        quats=parametres["quats"],
        scales=torch.exp(parametres["scales"]),
        opacities=torch.sigmoid(parametres["opacities"]),
        colors=couleurs,
        viewmats=dataset.matrices_vue[indice],
        Ks=dataset.intrinseques[indice],
        width=dataset.largeur,
        height=dataset.hauteur,
        sh_degree=degre_sh,
        packed=False,
        render_mode="RGB+ED",
    )
    # [1, H, W, 4] : trois canaux de couleur, puis la profondeur attendue.
    image = rendus[0]
    return image[..., :3].clamp(0.0, 1.0), image[..., 3]


def extraire(
    parametres,
    dataset,
    destination: Path | str,
    degre_sh: int = 3,
    taille_voxel: float = TAILLE_VOXEL_PAR_DEFAUT,
    profondeur_max: float = 20.0,
    decimation: int = 0,
    torch: Any = None,
) -> Resultat:
    """Extrait une surface depuis un splat entraîné et l'écrit en PLY.

    `decimation` est un nombre de triangles cible ; 0 laisse le mesh brut.
    """
    import numpy as np
    import open3d as o3d

    if torch is None:
        import torch as torch_module

        torch = torch_module

    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)

    volume = o3d.pipelines.integration.ScalableTSDFVolume(
        voxel_length=taille_voxel,
        sdf_trunc=FACTEUR_TRONCATURE * taille_voxel,
        color_type=o3d.pipelines.integration.TSDFVolumeColorType.RGB8,
    )

    integrees = 0
    with torch.no_grad():
        for indice in range(len(dataset.matrices_vue)):
            paquet = torch.tensor([indice], device=dataset.images.device)
            couleur, profondeur = _rendre_rgbd(parametres, dataset, paquet, degre_sh, torch)

            couleur_np = (couleur.cpu().numpy() * 255).astype(np.uint8)
            profondeur_np = profondeur.cpu().numpy().astype(np.float32)
            # Une profondeur nulle signifie « rien de rencontré » : l'intégrer
            # creuserait un trou devant la caméra.
            profondeur_np[profondeur_np <= 0] = 0.0
            profondeur_np[profondeur_np > profondeur_max] = 0.0

            rgbd = o3d.geometry.RGBDImage.create_from_color_and_depth(
                o3d.geometry.Image(np.ascontiguousarray(couleur_np)),
                o3d.geometry.Image(np.ascontiguousarray(profondeur_np)),
                depth_scale=1.0,
                depth_trunc=profondeur_max,
                convert_rgb_to_intensity=False,
            )

            k = dataset.intrinseques[indice].cpu().numpy()
            intrinseques = o3d.camera.PinholeCameraIntrinsic(
                dataset.largeur, dataset.hauteur,
                float(k[0, 0]), float(k[1, 1]), float(k[0, 2]), float(k[1, 2]),
            )
            # Open3D attend la transformation monde vers caméra, exactement la
            # convention COLMAP — aucune bascule à faire ici.
            extrinseques = dataset.matrices_vue[indice].cpu().numpy().astype(np.float64)

            volume.integrate(rgbd, intrinseques, extrinseques)
            integrees += 1

    mesh = volume.extract_triangle_mesh()
    mesh.compute_vertex_normals()

    if decimation and len(mesh.triangles) > decimation:
        mesh = mesh.simplify_quadric_decimation(target_number_of_triangles=decimation)
        mesh.compute_vertex_normals()

    o3d.io.write_triangle_mesh(str(destination), mesh)
    return Resultat(
        chemin=destination,
        sommets=len(mesh.vertices),
        triangles=len(mesh.triangles),
        vues_integrees=integrees,
    )
