# SPDX-License-Identifier: Apache-2.0
"""Gardes sur la lecture d'un modèle COLMAP.

Le test qui compte est `test_la_pose_reprojette_au_centre` : il vérifie la
**convention**, pas le parsing. Lire les bons nombres dans le mauvais repère
produit un modèle qui semble correct et un entraînement qui ne converge jamais.
"""

import pytest

from gamb_engine.poses import colmap

# Caméra à 4 unités devant l'origine, regardant vers elle. En convention COLMAP
# (+Z devant), une caméra à z=-4 dans le monde qui regarde +Z a pour pose
# monde->caméra : rotation identité, translation (0, 0, 4).
_CAMERAS = "# commentaire\n1 PINHOLE 800 600 400.0 400.0 400.0 300.0\n"
_IMAGES = "# commentaire\n1 1.0 0.0 0.0 0.0 0.0 0.0 4.0 1 vue_0001.png\n\n"
_POINTS = "# commentaire\n1 0.0 0.0 0.0 128 128 128 0.5\n2 0.1 0.0 0.0 255 0 0 0.5\n"


def _modele(tmp_path, cameras=_CAMERAS, images=_IMAGES, points=_POINTS):
    dossier = tmp_path / "sparse" / "0"
    dossier.mkdir(parents=True)
    (dossier / "cameras.txt").write_text(cameras, encoding="utf-8")
    (dossier / "images.txt").write_text(images, encoding="utf-8")
    if points is not None:
        (dossier / "points3D.txt").write_text(points, encoding="utf-8")
    return tmp_path


def test_lecture_complete(tmp_path):
    modele = colmap.lire(_modele(tmp_path))

    assert len(modele) == 1
    assert modele.vues[0].nom == "vue_0001.png"
    assert len(modele.points) == 2
    assert modele.couleurs[1] == (255, 0, 0)


def test_lire_accepte_le_dossier_du_modele(tmp_path):
    racine = _modele(tmp_path)
    assert len(colmap.lire(racine / "sparse" / "0")) == 1


def test_intrinseques_pinhole(tmp_path):
    camera = colmap.lire(_modele(tmp_path)).cameras[1]

    assert (camera.largeur, camera.hauteur) == (800, 600)
    assert camera.matrice_k == [[400.0, 0.0, 400.0], [0.0, 400.0, 300.0], [0.0, 0.0, 1.0]]


def test_simple_pinhole_partage_la_focale(tmp_path):
    racine = _modele(tmp_path, cameras="1 SIMPLE_PINHOLE 800 600 500.0 400.0 300.0\n")
    camera = colmap.lire(racine).cameras[1]

    assert camera.fx == camera.fy == 500.0


def test_un_modele_non_gere_est_refuse_plutot_que_devine(tmp_path):
    """Une focale mal interprétée ne lève jamais d'erreur — elle fausse tout."""
    racine = _modele(tmp_path, cameras="1 OPENCV 800 600 400 400 400 300 0.1 0.01 0 0\n")

    with pytest.raises(colmap.ModeleIllisible, match="OPENCV"):
        colmap.lire(racine)


def test_la_pose_reprojette_au_centre(tmp_path):
    """Le point visé doit tomber au centre, et devant la caméra."""
    modele = colmap.lire(_modele(tmp_path))
    vue = modele.vues[0]
    camera = modele.camera_de(vue)
    rotation, translation = vue.rotation, vue.translation

    cible = (0.0, 0.0, 0.0)
    x, y, z = (
        sum(rotation[i][j] * cible[j] for j in range(3)) + translation[i] for i in range(3)
    )

    assert z > 0, "la cible est derrière la caméra — la convention est inversée"
    assert abs(camera.fx * x / z + camera.cx - camera.cx) < 1e-9
    assert abs(camera.fy * y / z + camera.cy - camera.cy) < 1e-9


def test_la_rotation_est_orthonormale(tmp_path):
    racine = _modele(
        tmp_path,
        images="1 0.7071068 0.7071068 0.0 0.0 1.0 2.0 3.0 1 v.png\n\n",
    )
    rotation = colmap.lire(racine).vues[0].rotation

    for i in range(3):
        norme = sum(rotation[i][j] ** 2 for j in range(3)) ** 0.5
        assert abs(norme - 1.0) < 1e-6


def test_la_matrice_de_vue_est_homogene(tmp_path):
    matrice = colmap.lire(_modele(tmp_path)).vues[0].matrice_vue()

    assert len(matrice) == 4
    assert matrice[3] == [0.0, 0.0, 0.0, 1.0]
    assert matrice[2][3] == 4.0


def test_les_lignes_de_points_2d_sont_ignorees(tmp_path):
    """images.txt alterne pose et points 2D ; la seconde ligne n'est pas une pose."""
    racine = _modele(
        tmp_path,
        images=(
            "1 1.0 0.0 0.0 0.0 0.0 0.0 4.0 1 a.png\n"
            "12.5 33.1 1 45.0 66.2 2\n"
            "2 1.0 0.0 0.0 0.0 0.0 0.0 5.0 1 b.png\n"
            "\n"
        ),
    )
    modele = colmap.lire(racine)

    assert [v.nom for v in modele.vues] == ["a.png", "b.png"]


def test_une_vue_sans_camera_est_refusee(tmp_path):
    racine = _modele(tmp_path, images="1 1.0 0.0 0.0 0.0 0.0 0.0 4.0 9 v.png\n\n")

    with pytest.raises(colmap.ModeleIllisible, match="caméra absente"):
        colmap.lire(racine)


def test_un_nuage_absent_n_est_pas_une_erreur(tmp_path):
    """L'initialisation peut être aléatoire ; le nuage est facultatif."""
    modele = colmap.lire(_modele(tmp_path, points=None))
    assert modele.points == []
