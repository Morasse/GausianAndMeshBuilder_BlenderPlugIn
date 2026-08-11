# SPDX-License-Identifier: Apache-2.0
"""Prior géométrique — contraindre l'entraînement par une géométrie fournie.

**C'est le seul morceau de ce projet que personne d'autre n'a.** La recherche
menée le 2026-08-11 est nette :

- Initialiser les gaussiennes sur la surface d'un mesh est **résolu**
  (`mesh2splat` d'Electronic Arts, `ply_file_path` de splatfacto, Splatman).
- **Interdire les gaussiennes hors d'un volume *pendant* l'entraînement
  n'existe nulle part** : ni gsplat, ni splatfacto, ni Postshot, ni Brush. Tous
  ne proposent que du recadrage *après coup* — OBB à l'export chez Nerfstudio,
  Crop Box de rendu chez Postshot, sélection manuelle dans SuperSplat.
- **Contraindre les gaussiennes près d'une surface *fournie*** n'existe qu'à
  l'état auto-référentiel : SuGaR, MILo et 2DGS régularisent vers une surface
  dérivée des gaussiennes elles-mêmes, jamais vers un mesh que l'utilisateur a
  modelé. Proxy-GS s'en approche, mais sous licence INRIA non commerciale.

Un volume est décrit par une **matrice 4×4**, celle d'un objet Blender. Le cube
unité `[-1, 1]³` transformé par cette matrice définit la région. L'utilisateur
ajoute donc un cube ou une sphère dans sa scène, le place, et c'est fini — pas
de coordonnées à saisir, pas de format intermédiaire.

`torch` est importé dans les fonctions : ce module doit rester lisible et
testable sans GPU.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

NOM_FICHIER = "prior.json"

GARDER = "garder"
EXCLURE = "exclure"
MODES = (GARDER, EXCLURE)

BOITE = "boite"
SPHERE = "sphere"
FORMES = (BOITE, SPHERE)


class PriorInvalide(Exception):
    """Description de prior incohérente."""


@dataclass(frozen=True)
class Volume:
    """Une région de l'espace, décrite par la matrice d'un objet Blender.

    `matrice` transforme le cube unité `[-1, 1]³` (ou la sphère unité) vers sa
    place dans la scène. C'est exactement `object.matrix_world` d'un cube
    Blender de taille 2, donc l'aller-retour avec l'addon est direct.
    """

    matrice: tuple[tuple[float, ...], ...]
    mode: str = GARDER
    forme: str = BOITE
    nom: str = ""

    def __post_init__(self) -> None:
        if self.mode not in MODES:
            raise PriorInvalide(f"mode {self.mode!r} ; attendus : {', '.join(MODES)}")
        if self.forme not in FORMES:
            raise PriorInvalide(f"forme {self.forme!r} ; attendues : {', '.join(FORMES)}")
        if len(self.matrice) != 4 or any(len(ligne) != 4 for ligne in self.matrice):
            raise PriorInvalide("la matrice doit être 4x4")

    def contient(self, points, torch):
        """Masque booléen : quels points sont dans ce volume.

        Le test se fait dans l'espace **local** du volume, où la région est le
        cube ou la sphère unité. Passer par l'inverse de la matrice gère
        rotation et échelle non uniforme sans cas particulier.
        """
        matrice = torch.tensor(
            self.matrice, dtype=points.dtype, device=points.device
        )
        inverse = torch.linalg.inv(matrice)
        homogenes = torch.cat(
            [points, torch.ones(len(points), 1, dtype=points.dtype, device=points.device)],
            dim=1,
        )
        locaux = (inverse @ homogenes.T).T[:, :3]

        if self.forme == SPHERE:
            return locaux.norm(dim=1) <= 1.0
        return (locaux.abs() <= 1.0).all(dim=1)

    def en_dictionnaire(self) -> dict[str, Any]:
        return {
            "nom": self.nom,
            "mode": self.mode,
            "forme": self.forme,
            "matrice": [list(ligne) for ligne in self.matrice],
        }

    @classmethod
    def depuis_dictionnaire(cls, donnees: dict[str, Any]) -> Volume:
        return cls(
            matrice=tuple(tuple(float(v) for v in ligne) for ligne in donnees["matrice"]),
            mode=donnees.get("mode", GARDER),
            forme=donnees.get("forme", BOITE),
            nom=donnees.get("nom", ""),
        )


@dataclass
class GrilleSdf:
    """Distance signée à une surface, échantillonnée sur une grille régulière.

    Construite une fois depuis le mesh proxy, puis interrogée par interpolation
    trilinéaire à chaque itération. Recalculer la distance exacte à chaque pas
    coûterait plus cher que l'entraînement lui-même.
    """

    valeurs: Any  # tenseur [D, H, W], en unités de scène
    origine: tuple[float, float, float]
    pas: float

    def echantillonner(self, points, torch):
        """Distance signée aux points, par interpolation trilinéaire."""
        import torch.nn.functional as F

        grille = self.valeurs
        dimensions = torch.tensor(
            grille.shape[::-1], dtype=points.dtype, device=points.device
        )  # (W, H, D)
        origine = torch.tensor(self.origine, dtype=points.dtype, device=points.device)

        # grid_sample attend des coordonnées normalisées dans [-1, 1].
        indices = (points - origine) / self.pas
        normalisees = 2.0 * indices / (dimensions - 1).clamp_min(1) - 1.0

        echantillons = F.grid_sample(
            grille[None, None].to(points.dtype),
            normalisees[None, None, None],
            mode="bilinear",
            padding_mode="border",
            align_corners=True,
        )
        return echantillons.reshape(-1)


@dataclass
class PriorGeometrique:
    """Ce que la géométrie fournie impose à l'entraînement."""

    volumes: list[Volume] = field(default_factory=list)
    sdf: GrilleSdf | None = None
    poids_sdf: float = 0.0
    marge_sdf: float = 0.0
    elaguer_tous_les: int = 100
    elaguer_a_partir_de: int = 500

    @property
    def actif(self) -> bool:
        return bool(self.volumes) or (self.sdf is not None and self.poids_sdf > 0.0)

    # --- (b) le volume d'exclusion, la brique qui n'existe nulle part --------

    def masque_a_supprimer(self, points, torch):
        """Quelles gaussiennes doivent disparaître, au vu des volumes.

        Une gaussienne est supprimée si elle est **hors de tous** les volumes à
        garder, ou **dans l'un** des volumes à exclure. Sans volume `garder`,
        seuls les `exclure` s'appliquent — on ne veut pas qu'un utilisateur qui
        pose une seule boîte d'exclusion vide toute sa scène.
        """
        a_supprimer = torch.zeros(len(points), dtype=torch.bool, device=points.device)

        gardes = [v for v in self.volumes if v.mode == GARDER]
        if gardes:
            dedans = torch.zeros_like(a_supprimer)
            for volume in gardes:
                dedans |= volume.contient(points, torch)
            a_supprimer |= ~dedans

        for volume in (v for v in self.volumes if v.mode == EXCLURE):
            a_supprimer |= volume.contient(points, torch)

        return a_supprimer

    def elaguer(self, parametres, optimiseurs, etat, etape: int, torch) -> int:
        """Retire les gaussiennes hors volume. Renvoie combien ont disparu.

        Appelé toutes les N itérations plutôt qu'à chaque pas : la densification
        en recrée en permanence, et les supprimer à chaque itération coûterait
        plus que ça ne rapporte.
        """
        if not self.volumes or etape < self.elaguer_a_partir_de:
            return 0
        if etape % self.elaguer_tous_les != 0:
            return 0

        from gsplat.strategy.ops import remove

        masque = self.masque_a_supprimer(parametres["means"].detach(), torch)
        nombre = int(masque.sum())
        # Ne jamais tout supprimer : un volume mal placé viderait la scène et
        # ferait planter la suite sur un tenseur vide.
        if nombre == 0 or nombre >= len(masque):
            return 0

        # `ops.remove` découpe **tous** les tenseurs de l'état avec des indices
        # de gaussiennes. Or l'état de MCMCStrategy contient `binoms`, une table
        # 51x51 de coefficients binomiaux qui n'a rien de per-gaussienne : la
        # découper déclenche une assertion CUDA d'indice hors bornes, très loin
        # de sa cause. `remove` a été écrit pour DefaultStrategy, dont l'état
        # est bien indexé par gaussienne.
        #
        # On ne lui confie donc que les tenseurs dont la première dimension
        # correspond au nombre de gaussiennes, et on recopie le résultat.
        total = len(masque)
        par_gaussienne = {
            cle: valeur
            for cle, valeur in etat.items()
            if isinstance(valeur, torch.Tensor) and valeur.shape[:1] == (total,)
        }
        remove(parametres, optimiseurs, par_gaussienne, masque)
        etat.update(par_gaussienne)
        return nombre

    # --- (c) la contrainte vers une surface fournie --------------------------

    def penalite(self, points, torch):
        """Pénalise les gaussiennes éloignées de la surface proxy.

        `marge_sdf` laisse une épaisseur gratuite : une surface reconstruite
        n'est jamais exactement le mesh modelé à la main, et pénaliser dès le
        premier millimètre empêcherait le splat de rendre l'épaisseur réelle
        des choses.
        """
        if self.sdf is None or self.poids_sdf <= 0.0:
            return None
        distances = self.sdf.echantillonner(points, torch).abs()
        return self.poids_sdf * (distances - self.marge_sdf).clamp_min(0.0).mean()

    # --- Persistance ---------------------------------------------------------

    def en_dictionnaire(self) -> dict[str, Any]:
        return {
            "volumes": [v.en_dictionnaire() for v in self.volumes],
            "poids_sdf": self.poids_sdf,
            "marge_sdf": self.marge_sdf,
            "elaguer_tous_les": self.elaguer_tous_les,
            "elaguer_a_partir_de": self.elaguer_a_partir_de,
        }

    def ecrire(self, racine: Path) -> Path:
        chemin = Path(racine) / NOM_FICHIER
        chemin.write_text(
            json.dumps(self.en_dictionnaire(), indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        return chemin


def charger(racine: Path | str) -> PriorGeometrique | None:
    """Lit `prior.json` d'un projet, ou None s'il n'y en a pas.

    L'absence de prior n'est pas une erreur : c'est le cas nominal d'un premier
    run, celui dont on extraira justement le mesh proxy.
    """
    chemin = Path(racine) / NOM_FICHIER
    if not chemin.is_file():
        return None

    donnees = json.loads(chemin.read_text(encoding="utf-8"))
    return PriorGeometrique(
        volumes=[Volume.depuis_dictionnaire(v) for v in donnees.get("volumes", [])],
        poids_sdf=float(donnees.get("poids_sdf", 0.0)),
        marge_sdf=float(donnees.get("marge_sdf", 0.0)),
        elaguer_tous_les=int(donnees.get("elaguer_tous_les", 100)),
        elaguer_a_partir_de=int(donnees.get("elaguer_a_partir_de", 500)),
    )


# --- Construction de la grille SDF depuis un mesh ----------------------------


def sdf_depuis_mesh(chemin_mesh: Path | str, resolution: int = 128, marge: float = 0.1):
    """Échantillonne la distance signée à un mesh sur une grille régulière.

    Open3D fait le calcul exact ; on ne le refait pas à la main. La grille est
    étendue d'une marge relative autour du mesh, sinon les gaussiennes qui en
    sortent tombent hors grille et voient une distance constante.
    """
    import numpy as np
    import open3d as o3d
    import torch

    mesh = o3d.io.read_triangle_mesh(str(chemin_mesh))
    if len(mesh.triangles) == 0:
        raise PriorInvalide(f"mesh vide ou illisible : {chemin_mesh}")

    boite = mesh.get_axis_aligned_bounding_box()
    minimum = np.asarray(boite.min_bound)
    maximum = np.asarray(boite.max_bound)
    etendue = maximum - minimum
    minimum = minimum - etendue * marge
    maximum = maximum + etendue * marge

    pas = float((maximum - minimum).max() / (resolution - 1))
    axes = [
        np.arange(minimum[i], minimum[i] + pas * resolution, pas)[:resolution]
        for i in range(3)
    ]
    grille_x, grille_y, grille_z = np.meshgrid(*axes, indexing="ij")
    requetes = np.stack(
        [grille_x.ravel(), grille_y.ravel(), grille_z.ravel()], axis=1
    ).astype(np.float32)

    scene = o3d.t.geometry.RaycastingScene()
    scene.add_triangles(o3d.t.geometry.TriangleMesh.from_legacy(mesh))
    distances = scene.compute_signed_distance(requetes).numpy()

    # grid_sample lit l'axe le plus rapide en dernier : (D, H, W) = (z, y, x).
    valeurs = torch.from_numpy(
        distances.reshape(resolution, resolution, resolution).transpose(2, 1, 0).copy()
    )
    return GrilleSdf(valeurs=valeurs, origine=tuple(float(v) for v in minimum), pas=pas)


def volume_englobant(points, marge: float = 0.05) -> Volume:
    """Boîte alignée sur les axes qui contient tous les points, plus une marge.

    Utile comme garde-fou par défaut : même sans blockout, exclure ce qui sort
    franchement du nuage d'initialisation supprime déjà les floaters lointains.
    """
    import numpy as np

    tableau = np.asarray(points, dtype=np.float64)
    if tableau.size == 0:
        raise PriorInvalide("nuage vide")

    minimum, maximum = tableau.min(axis=0), tableau.max(axis=0)
    centre = (minimum + maximum) / 2.0
    demi = (maximum - minimum) / 2.0 * (1.0 + marge)
    demi = np.maximum(demi, 1e-6)

    matrice = np.eye(4)
    matrice[:3, :3] = np.diag(demi)
    matrice[:3, 3] = centre
    return Volume(
        matrice=tuple(tuple(float(v) for v in ligne) for ligne in matrice),
        mode=GARDER,
        forme=BOITE,
        nom="englobant",
    )
