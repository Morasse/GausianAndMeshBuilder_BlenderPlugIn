# SPDX-License-Identifier: GPL-3.0-or-later
"""Verifie qu'un dataset COLMAP est geometriquement coherent.

Le test central : reprojeter le point que toutes les cameras visent. S'il ne
tombe pas pres du centre de chaque image, la conversion de repere est fausse —
et c'est une erreur invisible a l'oeil sur les images rendues, qui ne se
manifeste que par un entrainement qui ne converge jamais.

Pur stdlib, aucune dependance, aucun Blender.

    python scripts/verifier_dataset.py ./dataset_test
"""

import sys
from pathlib import Path

# Le point vise par toutes les cameras du generateur de dataset synthetique.
CIBLE = (0.0, 0.0, 1.2)

# Tolerance de reprojection. Le generateur vise exactement, donc l'ecart
# attendu est nul ; 25 px laisse la place a un dataset produit autrement.
TOLERANCE_PX = 25.0

echecs: list[str] = []


def verifier(condition: bool, message: str) -> None:
    print(f"  {'OK  ' if condition else 'ECHEC'} {message}")
    if not condition:
        echecs.append(message)


def rotation_depuis_quaternion(qw, qx, qy, qz):
    return (
        (1 - 2 * (qy * qy + qz * qz), 2 * (qx * qy - qz * qw), 2 * (qx * qz + qy * qw)),
        (2 * (qx * qy + qz * qw), 1 - 2 * (qx * qx + qz * qz), 2 * (qy * qz - qx * qw)),
        (2 * (qx * qz - qy * qw), 2 * (qy * qz + qx * qw), 1 - 2 * (qx * qx + qy * qy)),
    )


def _projeter(point, rotation, translation, fx, fy, cx, cy):
    """Renvoie (u, v, z) en convention COLMAP : X_cam = R @ X_monde + t."""
    x, y, z = (
        sum(rotation[i][j] * point[j] for j in range(3)) + translation[i] for i in range(3)
    )
    if z <= 0:
        return None, None, z
    return fx * x / z + cx, fy * y / z + cy, z


def _lignes_utiles(chemin: Path):
    for ligne in chemin.read_text(encoding="utf-8").splitlines():
        if ligne and not ligne.startswith("#"):
            yield ligne


def main(racine: Path) -> int:
    sparse = racine / "sparse" / "0"
    dossier_images = racine / "images"

    champs = next(_lignes_utiles(sparse / "cameras.txt")).split()
    largeur, hauteur = int(champs[2]), int(champs[3])
    fx, fy, cx, cy = (float(v) for v in champs[4:8])
    print(f"Camera : {champs[1]} {largeur}x{hauteur}  fx={fx:.1f} cx={cx:.1f} cy={cy:.1f}")

    verifier(abs(cx - largeur / 2) < 1e-6, "cx au centre")
    verifier(abs(cy - hauteur / 2) < 1e-6, "cy au centre")

    poses = []
    for ligne in _lignes_utiles(sparse / "images.txt"):
        champs = ligne.split()
        if len(champs) >= 10:
            poses.append(([float(v) for v in champs[1:5]], [float(v) for v in champs[5:8]]))

    print(f"Poses  : {len(poses)}")
    verifier(bool(poses), "au moins une pose")

    fichiers = sorted(p.name for p in dossier_images.glob("*.png"))
    verifier(len(fichiers) == len(poses), f"{len(fichiers)} images pour {len(poses)} poses")

    derives, devant = [], 0
    for quaternion, translation in poses:
        rotation = rotation_depuis_quaternion(*quaternion)
        u, v, z = _projeter(CIBLE, rotation, translation, fx, fy, cx, cy)
        if z > 0:
            devant += 1
            derives.append(((u - cx) ** 2 + (v - cy) ** 2) ** 0.5)

    print(f"\nReprojection de la cible {CIBLE} :")
    print(f"  devant la camera : {devant}/{len(poses)}")
    if derives:
        moyenne = sum(derives) / len(derives)
        print(f"  derive au centre : moyenne {moyenne:.1f} px, max {max(derives):.1f} px")

    verifier(devant == len(poses), "la cible est devant TOUTES les cameras (signe de Z correct)")
    verifier(
        bool(derives) and max(derives) < TOLERANCE_PX,
        f"la cible tombe au centre de chaque image (< {TOLERANCE_PX:.0f} px)",
    )

    points = [ligne.split() for ligne in _lignes_utiles(sparse / "points3D.txt")]
    print(f"\nNuage d'initialisation : {len(points)} points")
    verifier(len(points) > 1000, "assez de points pour initialiser un entrainement")

    quaternion, translation = poses[0]
    rotation = rotation_depuis_quaternion(*quaternion)
    dans_le_cadre = 0
    for point in points:
        u, v, z = _projeter(
            [float(v) for v in point[1:4]], rotation, translation, fx, fy, cx, cy
        )
        if z > 0 and 0 <= u < largeur and 0 <= v < hauteur:
            dans_le_cadre += 1

    part = dans_le_cadre / len(points) if points else 0.0
    print(f"  visibles depuis la vue 1 : {dans_le_cadre} ({part:.0%})")
    verifier(part > 0.20, "une part substantielle du nuage tombe dans le cadre")

    print("\nRESULTAT:", "DATASET COHERENT" if not echecs else f"{len(echecs)} ECHEC(S)")
    return 1 if echecs else 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        raise SystemExit(2)
    raise SystemExit(main(Path(sys.argv[1])))
