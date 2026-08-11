# SPDX-License-Identifier: Apache-2.0
"""Boucle d'entraînement 3D Gaussian Splatting, sur gsplat.

**Pourquoi une boucle à nous plutôt qu'un appel à un outil existant.** Postshot
enchaîne SfM et entraînement en une commande, LichtFeld est très avancé, Brush
est propre — mais tous ferment leur boucle. Or le différenciateur du projet est
d'intervenir *dedans* : élaguer les gaussiennes hors d'un volume à chaque N
itérations, pénaliser la distance à une surface fournie, masquer la loss. Aucune
CLI externe ne le permet. C'est la seule raison de garder gsplat comme
bibliothèque au lieu d'une boîte noire.

Les hyperparamètres reprennent ceux du `simple_trainer.py` de gsplat, à la
valeur près, pour que l'écart mesuré ne vienne pas d'un réglage différent.

`torch` et `gsplat` sont importés **dans** les fonctions : le sidecar sert
`/health` et les fiches d'options sans payer l'import CUDA, et le CI teste tout
le reste sans GPU.
"""

from __future__ import annotations

import json
import math
import time
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from gamb_engine import options
from gamb_engine.poses import colmap
from gamb_engine.project import Projet
from gamb_engine.train import geometry_prior

# Une vue sur huit est mise de côté et n'est jamais vue par l'optimisation.
# C'est la convention du domaine, et c'est surtout le seul chiffre honnête :
# le PSNR d'entraînement mesure la capacité à mémoriser, celui de test mesure
# la reconstruction.
PERIODE_TEST = 8

# Facteur de conversion RGB vers le terme constant des harmoniques sphériques.
_C0 = 0.28209479177387814


@dataclass
class Configuration:
    """Configuration **complète** d'un run, jamais un diff.

    C'est ce qui rend deux runs comparables : chacun porte l'intégralité de ses
    réglages, y compris ceux qu'on n'a pas touchés.
    """

    iterations: int = 30000
    cap_max: int = 1000000
    degre_sh: int = 3
    resolution: int = 1
    poids_ssim: float = 0.2

    # Repris du simple_trainer, valeur pour valeur — et précisément de son
    # preset `mcmc`, pas de son preset `default`. Les deux diffèrent sur
    # l'initialisation et la régularisation, et mélanger la stratégie MCMC avec
    # les défauts de `default` fausse toute comparaison.
    lr_positions: float = 1.6e-4
    lr_echelles: float = 5e-3
    lr_opacites: float = 5e-2
    lr_quaternions: float = 1e-3
    lr_sh0: float = 2.5e-3
    lr_shN: float = 2.5e-3 / 20
    opacite_initiale: float = 0.5
    echelle_initiale: float = 0.1
    reg_opacite: float = 0.01
    reg_echelle: float = 0.01
    bruit_mcmc: float = 5e5
    raffiner_a_partir_de: int = 500
    raffiner_jusqu_a: int = 25000
    raffiner_tous_les: int = 100
    opacite_minimale: float = 0.005
    graine: int = 0

    @classmethod
    def depuis_preset(cls, nom: str | None = None, **surcharges: Any) -> Configuration:
        valeurs = options.resoudre(nom, **surcharges)
        return cls(**valeurs)


@dataclass
class Metriques:
    psnr_entrainement: float = 0.0
    psnr_test: float = 0.0
    ssim_test: float = 0.0
    nombre_gaussiennes: int = 0
    duree_s: float = 0.0
    # Combien de gaussiennes le prior géométrique a retirées sur tout le run.
    # C'est la moitié du critère d'acceptation de P4.
    gaussiennes_elaguees: int = 0
    prior_actif: bool = False
    historique: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class Resultat:
    dossier: Path
    configuration: Configuration
    metriques: Metriques
    ply: Path


# --- Utilitaires numériques --------------------------------------------------


def _fenetre_gaussienne(taille: int, sigma: float, torch):
    axe = torch.arange(taille, dtype=torch.float32) - taille // 2
    noyau = torch.exp(-(axe**2) / (2 * sigma**2))
    return (noyau / noyau.sum()).unsqueeze(0)


def ssim(prediction, verite, torch, taille: int = 11, sigma: float = 1.5) -> float:
    """SSIM standard, fenêtre gaussienne 11x11.

    Réimplémenté plutôt que tiré de `torchmetrics` : celui-ci arrive avec une
    dizaine de dépendances transitives à auditer, pour trente lignes de calcul.
    """
    import torch.nn.functional as F

    canaux = prediction.shape[1]
    noyau_1d = _fenetre_gaussienne(taille, sigma, torch).to(prediction.device)
    noyau = (noyau_1d.T @ noyau_1d).expand(canaux, 1, taille, taille).contiguous()

    def flou(image):
        return F.conv2d(image, noyau, padding=taille // 2, groups=canaux)

    mu_p, mu_v = flou(prediction), flou(verite)
    mu_p2, mu_v2, mu_pv = mu_p * mu_p, mu_v * mu_v, mu_p * mu_v
    sigma_p = flou(prediction * prediction) - mu_p2
    sigma_v = flou(verite * verite) - mu_v2
    sigma_pv = flou(prediction * verite) - mu_pv

    c1, c2 = 0.01**2, 0.03**2
    carte = ((2 * mu_pv + c1) * (2 * sigma_pv + c2)) / (
        (mu_p2 + mu_v2 + c1) * (sigma_p + sigma_v + c2)
    )
    return carte.mean()


def psnr(prediction, verite, torch) -> float:
    erreur = ((prediction - verite) ** 2).mean()
    return float(-10.0 * torch.log10(erreur.clamp_min(1e-12)))


def _distance_moyenne_voisins(points, torch, k: int = 3, taille_bloc: int = 4096):
    """Distance moyenne aux k plus proches voisins, par blocs.

    Le calcul par blocs n'est pas une optimisation prématurée : une matrice de
    distances complète sur un nuage de 100 000 points demanderait 40 Go.
    """
    nombre = points.shape[0]
    distances = torch.empty(nombre, device=points.device)
    for debut in range(0, nombre, taille_bloc):
        bloc = points[debut : debut + taille_bloc]
        ecarts = torch.cdist(bloc, points)
        # Le plus proche est le point lui-même, à distance nulle : on le saute.
        plus_proches = ecarts.topk(k + 1, largest=False).values[:, 1:]
        distances[debut : debut + taille_bloc] = plus_proches.mean(dim=-1)
    return distances.clamp_min(1e-7)


# --- Dataset -----------------------------------------------------------------


@dataclass
class Dataset:
    images: Any  # [N, H, W, 3] en float 0..1
    matrices_vue: Any  # [N, 4, 4] monde vers caméra, convention COLMAP
    intrinseques: Any  # [N, 3, 3]
    largeur: int
    hauteur: int
    points: Any
    couleurs: Any
    echelle_scene: float
    indices_entrainement: list[int]
    indices_test: list[int]


def charger_dataset(projet: Projet, configuration: Configuration, appareil) -> Dataset:
    import numpy as np
    import torch
    from PIL import Image

    modele = colmap.lire(projet.racine)
    dossier_images = projet.images

    images, matrices, intrinseques = [], [], []
    for vue in modele.vues:
        chemin = dossier_images / vue.nom
        if not chemin.is_file():
            raise FileNotFoundError(f"vue absente du projet : {chemin}")

        image = Image.open(chemin).convert("RGB")
        camera = modele.camera_de(vue)
        facteur = max(1, int(configuration.resolution))
        if facteur > 1:
            image = image.resize(
                (camera.largeur // facteur, camera.hauteur // facteur), Image.LANCZOS
            )

        images.append(torch.from_numpy(np.asarray(image, dtype=np.float32) / 255.0))
        matrices.append(torch.tensor(vue.matrice_vue(), dtype=torch.float32))

        k = torch.tensor(camera.matrice_k, dtype=torch.float32)
        k[:2] /= facteur
        intrinseques.append(k)

    images = torch.stack(images).to(appareil)
    matrices_vue = torch.stack(matrices).to(appareil)
    intrinseques = torch.stack(intrinseques).to(appareil)

    # Échelle de la scène : rayon du nuage de caméras, comme dans le
    # simple_trainer. Elle conditionne le pas d'apprentissage des positions.
    rotations = matrices_vue[:, :3, :3]
    translations = matrices_vue[:, :3, 3]
    centres = -torch.bmm(rotations.transpose(1, 2), translations.unsqueeze(-1)).squeeze(-1)
    echelle_scene = float((centres - centres.mean(dim=0)).norm(dim=-1).max()) * 1.1

    points = torch.tensor(modele.points, dtype=torch.float32, device=appareil)
    couleurs = torch.tensor(modele.couleurs, dtype=torch.float32, device=appareil) / 255.0

    tous = list(range(len(modele.vues)))
    indices_test = tous[::PERIODE_TEST]
    indices_entrainement = [i for i in tous if i not in set(indices_test)]

    return Dataset(
        images=images,
        matrices_vue=matrices_vue,
        intrinseques=intrinseques,
        largeur=images.shape[2],
        hauteur=images.shape[1],
        points=points,
        couleurs=couleurs,
        echelle_scene=echelle_scene,
        indices_entrainement=indices_entrainement,
        indices_test=indices_test,
    )


# --- Initialisation ----------------------------------------------------------


def initialiser_splats(dataset: Dataset, configuration: Configuration, appareil):
    import torch

    points = dataset.points
    nombre = points.shape[0]
    if nombre == 0:
        raise ValueError(
            "nuage d'initialisation vide — un entraînement partant de rien converge mal. "
            "Vérifie points3D.txt."
        )

    distances = _distance_moyenne_voisins(points, torch)
    echelles = torch.log(distances * configuration.echelle_initiale).unsqueeze(-1).repeat(1, 3)

    quaternions = torch.zeros(nombre, 4, device=appareil)
    quaternions[:, 0] = 1.0

    opacites = torch.logit(
        torch.full((nombre,), configuration.opacite_initiale, device=appareil)
    )

    nombre_sh = (configuration.degre_sh + 1) ** 2
    sh0 = ((dataset.couleurs - 0.5) / _C0).unsqueeze(1)  # [N, 1, 3]
    shN = torch.zeros(nombre, nombre_sh - 1, 3, device=appareil)

    parametres = {
        "means": torch.nn.Parameter(points.clone()),
        "scales": torch.nn.Parameter(echelles),
        "quats": torch.nn.Parameter(quaternions),
        "opacities": torch.nn.Parameter(opacites),
        "sh0": torch.nn.Parameter(sh0),
        "shN": torch.nn.Parameter(shN),
    }

    # Le pas des positions est mis à l'échelle de la scène : un déplacement de
    # 1e-4 n'a pas le même sens sur une figurine et sur un quartier.
    pas = {
        "means": configuration.lr_positions * dataset.echelle_scene,
        "scales": configuration.lr_echelles,
        "quats": configuration.lr_quaternions,
        "opacities": configuration.lr_opacites,
        "sh0": configuration.lr_sh0,
        "shN": configuration.lr_shN,
    }
    optimiseurs = {
        cle: torch.optim.Adam([parametres[cle]], lr=valeur, eps=1e-15)
        for cle, valeur in pas.items()
    }
    return parametres, optimiseurs


# --- Rendu -------------------------------------------------------------------


def _rendre(parametres, dataset: Dataset, indices, degre_sh_courant: int, torch):
    from gsplat import rasterization

    couleurs = torch.cat([parametres["sh0"], parametres["shN"]], dim=1)
    rendus, _, info = rasterization(
        means=parametres["means"],
        quats=parametres["quats"],
        scales=torch.exp(parametres["scales"]),
        opacities=torch.sigmoid(parametres["opacities"]),
        colors=couleurs,
        viewmats=dataset.matrices_vue[indices],
        Ks=dataset.intrinseques[indices],
        width=dataset.largeur,
        height=dataset.hauteur,
        sh_degree=degre_sh_courant,
        packed=False,
    )
    return rendus.clamp(0.0, 1.0), info


# --- Entraînement ------------------------------------------------------------


def entrainer(
    projet: Projet,
    configuration: Configuration | None = None,
    progression: Callable[[int, int, float], None] | None = None,
    prior: geometry_prior.PriorGeometrique | None = None,
) -> Resultat:
    """Entraîne un splat et écrit un run immuable dans `runs/`.

    Si le projet contient un `prior.json`, ou si un prior est passé
    explicitement, la géométrie fournie contraint l'entraînement : les
    gaussiennes hors volume sont élaguées périodiquement, et une pénalité les
    rappelle vers la surface.
    """
    import torch
    from gsplat.strategy import MCMCStrategy

    configuration = configuration or Configuration()
    if prior is None:
        prior = geometry_prior.charger(projet.racine)
    if not torch.cuda.is_available():
        raise RuntimeError(
            "aucun GPU CUDA visible — l'entraînement 3DGS n'a pas de repli CPU utilisable."
        )

    torch.manual_seed(configuration.graine)
    appareil = torch.device("cuda")

    depart = time.time()
    dataset = charger_dataset(projet, configuration, appareil)
    parametres, optimiseurs = initialiser_splats(dataset, configuration, appareil)

    strategie = MCMCStrategy(
        cap_max=configuration.cap_max,
        noise_lr=configuration.bruit_mcmc,
        refine_start_iter=configuration.raffiner_a_partir_de,
        refine_stop_iter=min(configuration.raffiner_jusqu_a, configuration.iterations),
        refine_every=configuration.raffiner_tous_les,
        min_opacity=configuration.opacite_minimale,
        verbose=False,
    )
    etat = strategie.initialize_state()

    entrainement = torch.tensor(dataset.indices_entrainement, device=appareil)
    historique: list[dict[str, Any]] = []
    dernier_psnr = 0.0
    elaguees = 0

    for etape in range(configuration.iterations):
        # Le degré des SH monte par paliers : commencer au degré plein fait
        # apprendre la couleur dépendante de la vue avant la géométrie, et le
        # splat compense une mauvaise forme par de la couleur.
        degre = min(configuration.degre_sh, etape // 1000)

        indice = entrainement[torch.randint(len(entrainement), (1,), device=appareil)]
        rendu, info = _rendre(parametres, dataset, indice, degre, torch)
        verite = dataset.images[indice]

        l1 = (rendu - verite).abs().mean()
        similarite = ssim(
            rendu.permute(0, 3, 1, 2), verite.permute(0, 3, 1, 2), torch
        )
        perte = (1.0 - configuration.poids_ssim) * l1 + configuration.poids_ssim * (
            1.0 - similarite
        )
        # Régularisation propre à MCMC : sans elle, la stratégie densifie sans
        # frein et le nuage gonfle jusqu'au plafond sans gain de qualité.
        if configuration.reg_opacite > 0.0:
            perte = perte + configuration.reg_opacite * torch.sigmoid(
                parametres["opacities"]
            ).mean()
        if configuration.reg_echelle > 0.0:
            perte = perte + configuration.reg_echelle * torch.exp(parametres["scales"]).mean()

        # (c) rappel vers la surface fournie — vers un mesh **externe**, pas
        # vers une surface dérivée des gaussiennes elles-mêmes.
        if prior is not None:
            penalite = prior.penalite(parametres["means"], torch)
            if penalite is not None:
                perte = perte + penalite

        strategie.step_pre_backward(parametres, optimiseurs, etat, etape, info)
        perte.backward()

        for optimiseur in optimiseurs.values():
            optimiseur.step()
            optimiseur.zero_grad(set_to_none=True)

        strategie.step_post_backward(
            params=parametres,
            optimizers=optimiseurs,
            state=etat,
            step=etape,
            info=info,
            lr=configuration.lr_positions * dataset.echelle_scene,
        )

        # (b) l'élagage vient APRÈS la densification : la stratégie recrée des
        # gaussiennes en permanence, y compris hors volume. Élaguer avant la
        # laisserait les réintroduire à chaque pas.
        if prior is not None:
            elaguees += prior.elaguer(parametres, optimiseurs, etat, etape, torch)

        if etape % 100 == 0 or etape == configuration.iterations - 1:
            with torch.no_grad():
                dernier_psnr = psnr(rendu, verite, torch)
            historique.append(
                {
                    "etape": etape,
                    "perte": float(perte.detach()),
                    "psnr": dernier_psnr,
                    "gaussiennes": int(parametres["means"].shape[0]),
                }
            )
            if progression:
                progression(etape, configuration.iterations, dernier_psnr)

    # Passe finale : la densification tourne jusqu'au dernier pas, donc sans
    # elle le PLY livré contient encore des gaussiennes hors volume.
    if prior is not None:
        elaguees += prior.elaguer(
            parametres, optimiseurs, etat, configuration.iterations, torch, final=True
        )

    metriques = Metriques(
        psnr_entrainement=dernier_psnr,
        nombre_gaussiennes=int(parametres["means"].shape[0]),
        duree_s=time.time() - depart,
        gaussiennes_elaguees=elaguees,
        prior_actif=prior is not None and prior.actif,
        historique=historique,
    )
    _evaluer(parametres, dataset, configuration, metriques, torch)

    dossier = _ecrire_run(projet, configuration, metriques, parametres, torch)
    return Resultat(
        dossier=dossier,
        configuration=configuration,
        metriques=metriques,
        ply=dossier / "point_cloud.ply",
    )


def _evaluer(parametres, dataset, configuration, metriques, torch) -> None:
    """PSNR et SSIM sur les vues jamais vues par l'optimisation."""
    if not dataset.indices_test:
        return
    psnrs, ssims = [], []
    with torch.no_grad():
        for indice in dataset.indices_test:
            paquet = torch.tensor([indice], device=dataset.images.device)
            rendu, _ = _rendre(parametres, dataset, paquet, configuration.degre_sh, torch)
            verite = dataset.images[paquet]
            psnrs.append(psnr(rendu, verite, torch))
            ssims.append(
                float(ssim(rendu.permute(0, 3, 1, 2), verite.permute(0, 3, 1, 2), torch))
            )
    metriques.psnr_test = sum(psnrs) / len(psnrs)
    metriques.ssim_test = sum(ssims) / len(ssims)


# --- Écriture du run ---------------------------------------------------------


def _ecrire_run(projet, configuration, metriques, parametres, torch) -> Path:
    import yaml

    horodatage = time.strftime("%Y-%m-%d_%H%M%S")
    marque = "guide" if metriques.prior_actif else "libre"
    dossier = projet.runs / f"{horodatage}_{marque}_{metriques.nombre_gaussiennes}"
    dossier.mkdir(parents=True, exist_ok=True)

    (dossier / "config.yaml").write_text(
        yaml.safe_dump(asdict(configuration), sort_keys=True, allow_unicode=True),
        encoding="utf-8",
    )
    (dossier / "metrics.json").write_text(
        json.dumps(asdict(metriques), indent=2, ensure_ascii=False), encoding="utf-8"
    )
    ecrire_ply(dossier / "point_cloud.ply", parametres, torch)

    projet.journaliser(
        "entrainement",
        run=dossier.name,
        gaussiennes=metriques.nombre_gaussiennes,
        psnr_test=round(metriques.psnr_test, 3),
    )
    projet.ecrire()
    return dossier


def ecrire_ply(chemin: Path, parametres, torch) -> None:
    """PLY 3DGS conventionnel, valeurs **pré-activation**.

    C'est le format que lit l'importeur natif en préparation dans Blender, et
    celui que consomment SuperSplat et les addons existants. Les valeurs sont
    stockées avant activation — `scale` en log, `opacity` en logit — comme dans
    l'implémentation d'origine ; les relire en post-activation donne un nuage
    d'apparence correcte et de densité absurde.
    """
    import numpy as np

    with torch.no_grad():
        moyennes = parametres["means"].cpu().numpy()
        sh0 = parametres["sh0"].cpu().numpy().reshape(len(moyennes), -1)
        shN = parametres["shN"].cpu().numpy().transpose(0, 2, 1).reshape(len(moyennes), -1)
        opacites = parametres["opacities"].cpu().numpy().reshape(-1, 1)
        echelles = parametres["scales"].cpu().numpy()
        quaternions = parametres["quats"].cpu().numpy()

    colonnes = ["x", "y", "z", "nx", "ny", "nz"]
    colonnes += [f"f_dc_{i}" for i in range(sh0.shape[1])]
    colonnes += [f"f_rest_{i}" for i in range(shN.shape[1])]
    colonnes += ["opacity", "scale_0", "scale_1", "scale_2"]
    colonnes += ["rot_0", "rot_1", "rot_2", "rot_3"]

    normales = np.zeros_like(moyennes)
    donnees = np.concatenate(
        [moyennes, normales, sh0, shN, opacites, echelles, quaternions], axis=1
    ).astype(np.float32)

    entete = ["ply", "format binary_little_endian 1.0", f"element vertex {len(donnees)}"]
    entete += [f"property float {nom}" for nom in colonnes]
    entete.append("end_header")

    with chemin.open("wb") as fichier:
        fichier.write(("\n".join(entete) + "\n").encode("ascii"))
        fichier.write(donnees.tobytes())


def duree_estimee(configuration: Configuration) -> float:
    """Ordre de grandeur, pour l'interface. Volontairement grossier."""
    return configuration.iterations * 0.02 * math.sqrt(max(configuration.resolution, 1))
