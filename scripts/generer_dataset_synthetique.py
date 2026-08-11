# SPDX-License-Identifier: GPL-3.0-or-later
"""Genere un dataset multi-vues synthetique au format COLMAP, depuis Blender.

**Pourquoi synthetique.** Sur un dataset photo passe par COLMAP, un PSNR
decevant peut venir d'un mauvais entrainement ou de mauvaises poses, et rien ne
permet de les distinguer. Ici les poses sont **exactes** : si le resultat est
mauvais, c'est l'entrainement. C'est ce qui rend le critere d'acceptation de la
phase d'entrainement falsifiable.

Consequence utile : ce dataset porte deja ses poses au format COLMAP, donc
l'entraineur se valide **sans COLMAP**.

    blender --background --factory-startup --python scripts/generer_dataset_synthetique.py \
        -- --sortie ./dataset_test

Puis, pour verifier la coherence geometrique :

    python scripts/verifier_dataset.py ./dataset_test
"""

import argparse
import math
import sys

import bpy
from mathutils import Matrix, Vector

# Blender : la camera regarde -Z, +Y en haut.
# COLMAP  : la camera regarde +Z, Y vers le bas.
# La bascule entre les deux est une rotation de 180 degres autour de X. S'y
# tromper produit un dataset d'apparence correcte et un entrainement qui ne
# converge jamais — d'ou le script de verification.
BASCULE_BLENDER_VERS_COLMAP = Matrix(((1, 0, 0), (0, -1, 0), (0, 0, -1)))

CIBLE = Vector((0, 0, 1.2))


def analyser_arguments() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    analyseur = argparse.ArgumentParser()
    analyseur.add_argument("--sortie", required=True)
    analyseur.add_argument("--vues", type=int, default=60)
    analyseur.add_argument("--largeur", type=int, default=800)
    analyseur.add_argument("--hauteur", type=int, default=600)
    analyseur.add_argument("--rayon", type=float, default=6.0)
    return analyseur.parse_args(argv)


def construire_la_scene() -> None:
    """Une scene volontairement peu symetrique.

    Un cube seul se reconstruit trop bien et masquerait les defauts. Il faut de
    la geometrie courbe, des occlusions et des couleurs distinctes pour qu'un
    PSNR veuille dire quelque chose.
    """
    bpy.ops.wm.read_factory_settings(use_empty=True)

    bpy.ops.mesh.primitive_plane_add(size=20, location=(0, 0, 0))
    _peindre(bpy.context.active_object, (0.35, 0.35, 0.38, 1.0))

    bpy.ops.mesh.primitive_monkey_add(size=2.4, location=(0, 0, 1.6))
    singe = bpy.context.active_object
    singe.rotation_euler = (math.radians(15), 0, math.radians(25))
    bpy.ops.object.shade_smooth()
    bpy.ops.object.modifier_add(type="SUBSURF")
    singe.modifiers["Subdivision"].levels = 2
    singe.modifiers["Subdivision"].render_levels = 2
    _peindre(singe, (0.75, 0.28, 0.16, 1.0))

    for position, couleur, taille in (
        ((2.4, 1.1, 0.5), (0.15, 0.45, 0.75, 1.0), 1.0),
        ((-2.2, -1.4, 0.35), (0.85, 0.72, 0.2, 1.0), 0.7),
    ):
        bpy.ops.mesh.primitive_cube_add(size=taille, location=position)
        _peindre(bpy.context.active_object, couleur)

    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.8, location=(-1.6, 2.2, 0.8))
    bpy.ops.object.shade_smooth()
    _peindre(bpy.context.active_object, (0.2, 0.6, 0.3, 1.0))

    # Eclairage fixe : aucune variation d'exposition entre les vues, sinon on
    # testerait le bilateral grid au lieu de l'entrainement.
    for position, energie in (((5, -5, 8), 1200), ((-6, 4, 6), 600), ((0, 7, 3), 400)):
        bpy.ops.object.light_add(type="POINT", location=position)
        bpy.context.active_object.data.energy = energie

    monde = bpy.data.worlds.new("Monde")
    monde.use_nodes = True
    monde.node_tree.nodes["Background"].inputs[0].default_value = (0.05, 0.06, 0.08, 1.0)
    bpy.context.scene.world = monde


def _peindre(objet, couleur) -> None:
    materiau = bpy.data.materials.new(name=f"mat_{objet.name}")
    materiau.use_nodes = True
    principled = materiau.node_tree.nodes["Principled BSDF"]
    principled.inputs["Base Color"].default_value = couleur
    principled.inputs["Roughness"].default_value = 0.6
    objet.data.materials.append(materiau)


def positions_de_camera(nombre: int, rayon: float) -> list[Vector]:
    """Spirale de Fibonacci sur une demi-sphere : couverture angulaire reguliere.

    Un simple anneau donnerait une couverture degeneree — toutes les cameras a
    la meme hauteur, aucune information verticale, et un 3DGS qui comble ce
    qu'il ne voit pas en inventant.
    """
    positions = []
    nombre_dor = math.pi * (3 - math.sqrt(5))
    for index in range(nombre):
        # Borne basse a 0.15 pour ne pas raser le sol, haute a 0.9 pour ne pas
        # survoler a la verticale.
        z = 0.15 + 0.75 * (index / max(nombre - 1, 1))
        rayon_anneau = math.sqrt(max(1 - z * z, 1e-6)) * rayon
        angle = nombre_dor * index
        positions.append(
            Vector((math.cos(angle) * rayon_anneau, math.sin(angle) * rayon_anneau, z * rayon))
        )
    return positions


def pose_colmap(camera) -> tuple[list[float], Vector]:
    """Quaternion et translation monde vers camera, en convention COLMAP."""
    location, rotation, _ = camera.matrix_world.decompose()
    rotation_monde_vers_blender = rotation.to_matrix().transposed()
    translation_monde_vers_blender = -1 * rotation_monde_vers_blender @ location

    rotation_colmap = BASCULE_BLENDER_VERS_COLMAP @ rotation_monde_vers_blender
    translation_colmap = BASCULE_BLENDER_VERS_COLMAP @ translation_monde_vers_blender

    quaternion = rotation_colmap.to_quaternion()
    return [quaternion.w, quaternion.x, quaternion.y, quaternion.z], translation_colmap


def nuage_initial(nombre_max: int = 12000) -> list[tuple[Vector, tuple[int, int, int]]]:
    """Nuage epars, a la place de la sortie SfM qu'on n'a pas ici."""
    points = []
    profondeur = bpy.context.evaluated_depsgraph_get()
    for objet in bpy.context.scene.objects:
        if objet.type != "MESH":
            continue
        evalue = objet.evaluated_get(profondeur)
        maillage = evalue.to_mesh()
        couleur = (180, 180, 180)
        if evalue.data.materials and evalue.data.materials[0].use_nodes:
            base = evalue.data.materials[0].node_tree.nodes["Principled BSDF"]
            couleur = tuple(int(255 * c) for c in base.inputs["Base Color"].default_value[:3])
        for sommet in maillage.vertices:
            points.append((objet.matrix_world @ sommet.co, couleur))
        evalue.to_mesh_clear()

    if len(points) > nombre_max:
        points = points[:: len(points) // nombre_max][:nombre_max]
    return points


def main() -> None:
    arguments = analyser_arguments()
    from pathlib import Path

    racine = Path(arguments.sortie)
    dossier_images = racine / "images"
    dossier_sparse = racine / "sparse" / "0"
    dossier_images.mkdir(parents=True, exist_ok=True)
    dossier_sparse.mkdir(parents=True, exist_ok=True)

    construire_la_scene()

    scene = bpy.context.scene
    # 4.2 exposait BLENDER_EEVEE_NEXT ; 5.x est revenu a BLENDER_EEVEE.
    moteurs = scene.render.bl_rna.properties["engine"].enum_items.keys()
    scene.render.engine = "BLENDER_EEVEE" if "BLENDER_EEVEE" in moteurs else "BLENDER_EEVEE_NEXT"
    scene.render.resolution_x = arguments.largeur
    scene.render.resolution_y = arguments.hauteur
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"

    donnees_camera = bpy.data.cameras.new("camera")
    donnees_camera.lens = 35.0
    donnees_camera.sensor_fit = "HORIZONTAL"
    camera = bpy.data.objects.new("camera", donnees_camera)
    scene.collection.objects.link(camera)
    scene.camera = camera

    lignes_images = []
    for index, position in enumerate(positions_de_camera(arguments.vues, arguments.rayon), 1):
        camera.location = position
        camera.rotation_euler = (CIBLE - position).to_track_quat("-Z", "Y").to_euler()
        bpy.context.view_layer.update()

        nom = f"vue_{index:04d}.png"
        scene.render.filepath = str(dossier_images / nom)
        bpy.ops.render.render(write_still=True)

        quaternion, translation = pose_colmap(camera)
        lignes_images.append(
            f"{index} {quaternion[0]:.9f} {quaternion[1]:.9f} {quaternion[2]:.9f} "
            f"{quaternion[3]:.9f} {translation.x:.9f} {translation.y:.9f} "
            f"{translation.z:.9f} 1 {nom}"
        )
        print(f"  vue {index}/{arguments.vues}")

    focale = donnees_camera.lens * arguments.largeur / donnees_camera.sensor_width
    (dossier_sparse / "cameras.txt").write_text(
        "# Camera list\n# CAMERA_ID MODEL WIDTH HEIGHT PARAMS[]\n"
        f"1 PINHOLE {arguments.largeur} {arguments.hauteur} {focale:.9f} {focale:.9f} "
        f"{arguments.largeur / 2:.9f} {arguments.hauteur / 2:.9f}\n",
        encoding="utf-8",
    )

    (dossier_sparse / "images.txt").write_text(
        "# Image list\n# IMAGE_ID QW QX QY QZ TX TY TZ CAMERA_ID NAME\n"
        "# (la ligne des points 2D est vide : aucune correspondance a fournir)\n"
        + "".join(f"{ligne}\n\n" for ligne in lignes_images),
        encoding="utf-8",
    )

    points = nuage_initial()
    (dossier_sparse / "points3D.txt").write_text(
        "# 3D point list\n# POINT3D_ID X Y Z R G B ERROR TRACK[]\n"
        + "\n".join(
            f"{identifiant} {p.x:.6f} {p.y:.6f} {p.z:.6f} {c[0]} {c[1]} {c[2]} 0"
            for identifiant, (p, c) in enumerate(points, 1)
        )
        + "\n",
        encoding="utf-8",
    )

    print(f"\nDataset ecrit dans {racine}")
    print(f"  {arguments.vues} vues, {len(points)} points d'initialisation")


main()
