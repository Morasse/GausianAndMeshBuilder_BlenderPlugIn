# SPDX-License-Identifier: Apache-2.0
"""Lecture d'un modèle COLMAP en texte, sans dépendance.

`pycolmap` lira le format binaire quand on exécutera COLMAP nous-mêmes (P5).
Ici, le besoin est différent : lire le modèle **texte** que produit le
générateur de dataset synthétique, sans imposer une dépendance de plus à un
module qui doit rester importable pour les tests CPU du CI.

Conventions, à ne jamais confondre :

- COLMAP stocke la transformation **monde vers caméra** : `X_cam = R @ X_monde + t`.
- Sa caméra regarde **+Z**, avec **Y vers le bas**.
- Blender regarde −Z, avec +Y vers le haut. La bascule est une rotation de 180°
  autour de X — appliquée à l'export, jamais en interne.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

# Modèles COLMAP qu'on sait lire, avec le nombre de paramètres attendu.
# On refuse le reste plutôt que de deviner : une focale mal interprétée produit
# un entraînement qui converge vers autre chose, sans jamais lever d'erreur.
MODELES = {
    "PINHOLE": 4,  # fx, fy, cx, cy
    "SIMPLE_PINHOLE": 3,  # f, cx, cy
}


class ModeleIllisible(Exception):
    """Le modèle COLMAP est absent, incomplet, ou dans un format non géré."""


@dataclass(frozen=True)
class Camera:
    identifiant: int
    modele: str
    largeur: int
    hauteur: int
    fx: float
    fy: float
    cx: float
    cy: float

    @property
    def matrice_k(self) -> list[list[float]]:
        return [[self.fx, 0.0, self.cx], [0.0, self.fy, self.cy], [0.0, 0.0, 1.0]]


@dataclass(frozen=True)
class Vue:
    """Une image et sa pose monde vers caméra."""

    identifiant: int
    quaternion: tuple[float, float, float, float]  # (w, x, y, z)
    translation: tuple[float, float, float]
    camera_id: int
    nom: str

    @property
    def rotation(self) -> list[list[float]]:
        w, x, y, z = self.quaternion
        return [
            [1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
            [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
            [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)],
        ]

    def matrice_vue(self) -> list[list[float]]:
        """Matrice 4x4 monde vers caméra, en convention COLMAP."""
        rotation = self.rotation
        return [
            [*rotation[0], self.translation[0]],
            [*rotation[1], self.translation[1]],
            [*rotation[2], self.translation[2]],
            [0.0, 0.0, 0.0, 1.0],
        ]


@dataclass
class Modele:
    cameras: dict[int, Camera]
    vues: list[Vue]
    points: list[tuple[float, float, float]]
    couleurs: list[tuple[int, int, int]]

    def __len__(self) -> int:
        return len(self.vues)

    def camera_de(self, vue: Vue) -> Camera:
        return self.cameras[vue.camera_id]


def _lignes_utiles(chemin: Path):
    if not chemin.is_file():
        raise ModeleIllisible(f"fichier absent : {chemin}")
    for ligne in chemin.read_text(encoding="utf-8").splitlines():
        depouillee = ligne.strip()
        if depouillee and not depouillee.startswith("#"):
            yield depouillee


def _lire_cameras(chemin: Path) -> dict[int, Camera]:
    cameras: dict[int, Camera] = {}
    for ligne in _lignes_utiles(chemin):
        champs = ligne.split()
        modele = champs[1]
        if modele not in MODELES:
            raise ModeleIllisible(
                f"modèle de caméra non géré : {modele}. Gérés : {', '.join(MODELES)}. "
                "Convertis le modèle plutôt que de laisser deviner la focale."
            )
        parametres = [float(v) for v in champs[4:]]
        if len(parametres) < MODELES[modele]:
            raise ModeleIllisible(
                f"{modele} attend {MODELES[modele]} paramètres, {len(parametres)} lus"
            )

        if modele == "PINHOLE":
            fx, fy, cx, cy = parametres[:4]
        else:  # SIMPLE_PINHOLE : une seule focale pour les deux axes
            focale, cx, cy = parametres[:3]
            fx = fy = focale

        identifiant = int(champs[0])
        cameras[identifiant] = Camera(
            identifiant, modele, int(champs[2]), int(champs[3]), fx, fy, cx, cy
        )
    if not cameras:
        raise ModeleIllisible(f"aucune caméra dans {chemin}")
    return cameras


def _lire_vues(chemin: Path) -> list[Vue]:
    vues: list[Vue] = []
    for ligne in _lignes_utiles(chemin):
        champs = ligne.split()
        # Le format alterne une ligne de pose et une ligne de points 2D. Cette
        # dernière peut être vide ou très longue ; on la reconnaît au fait
        # qu'elle n'a pas la forme d'une pose.
        if len(champs) < 10:
            continue
        try:
            identifiant = int(champs[0])
            quaternion = tuple(float(v) for v in champs[1:5])
            translation = tuple(float(v) for v in champs[5:8])
            camera_id = int(champs[8])
        except ValueError:
            continue
        vues.append(Vue(identifiant, quaternion, translation, camera_id, champs[9]))

    if not vues:
        raise ModeleIllisible(f"aucune pose dans {chemin}")
    return vues


def _lire_points(chemin: Path):
    points: list[tuple[float, float, float]] = []
    couleurs: list[tuple[int, int, int]] = []
    if not chemin.is_file():
        return points, couleurs
    for ligne in _lignes_utiles(chemin):
        champs = ligne.split()
        if len(champs) < 7:
            continue
        points.append(tuple(float(v) for v in champs[1:4]))
        couleurs.append(tuple(int(v) for v in champs[4:7]))
    return points, couleurs


def lire(racine: Path | str) -> Modele:
    """Lit un modèle COLMAP texte.

    Accepte la racine du projet (le modèle est cherché dans `sparse/0`) ou le
    dossier du modèle lui-même.
    """
    racine = Path(racine)
    dossier = racine if (racine / "cameras.txt").is_file() else racine / "sparse" / "0"

    cameras = _lire_cameras(dossier / "cameras.txt")
    vues = _lire_vues(dossier / "images.txt")
    points, couleurs = _lire_points(dossier / "points3D.txt")

    inconnues = {v.camera_id for v in vues} - set(cameras)
    if inconnues:
        raise ModeleIllisible(f"vues référençant une caméra absente : {sorted(inconnues)}")

    return Modele(cameras=cameras, vues=vues, points=points, couleurs=couleurs)
