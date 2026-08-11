# SPDX-License-Identifier: Apache-2.0
"""Gardes sur le loss masking.

La spec le dit : « comment les masques remontent en 3D, c'est le vrai travail
d'ingé, pas SAM ». Le producteur des masques est interchangeable — SAM 3, SAM 2,
un rendu Blender, un coup de pinceau — mais l'exclusion dans la loss ne l'est
pas. Elle se teste donc **sans aucun modèle**, ce qui est heureux : les poids de
SAM 3 sont sous approbation manuelle.
"""

import numpy as np
import pytest
from PIL import Image

from gamb_engine import project
from gamb_engine.train import gsplat_runner

torch = pytest.importorskip("torch")


def _masque(dossier, nom, largeur, hauteur, exclu):
    """Écrit un masque : blanc là où il faut ignorer."""
    dossier.mkdir(parents=True, exist_ok=True)
    donnees = np.zeros((hauteur, largeur), dtype=np.uint8)
    donnees[exclu] = 255
    Image.fromarray(donnees).save(dossier / f"{nom}.png")


def test_sans_dossier_masks_il_n_y_a_pas_de_poids(tmp_path):
    """Le cas nominal : la plupart des projets n'ont aucun masque."""
    projet = project.creer(tmp_path / "scan")
    assert gsplat_runner.charger_masques(projet, ["a.png"], (4, 4), torch) is None


def test_un_dossier_masks_vide_ne_produit_pas_de_poids(tmp_path):
    projet = project.creer(tmp_path / "scan")
    (projet.racine / "masks").mkdir()
    assert gsplat_runner.charger_masques(projet, ["a.png"], (4, 4), torch) is None


def test_le_masque_met_a_zero_les_pixels_exclus(tmp_path):
    projet = project.creer(tmp_path / "scan")
    _masque(projet.racine / "masks" / "vitre", "a", 4, 4, np.s_[0:2, :])

    poids = gsplat_runner.charger_masques(projet, ["a.png"], (4, 4), torch)

    assert poids.shape == (1, 4, 4)
    assert poids[0, 0].tolist() == [0.0, 0.0, 0.0, 0.0]
    assert poids[0, 3].tolist() == [1.0, 1.0, 1.0, 1.0]


def test_plusieurs_classes_s_additionnent(tmp_path):
    """Les classes sont des raisons d'exclure, pas des poids à composer."""
    projet = project.creer(tmp_path / "scan")
    _masque(projet.racine / "masks" / "vitre", "a", 4, 4, np.s_[0:1, :])
    _masque(projet.racine / "masks" / "ciel", "a", 4, 4, np.s_[3:4, :])

    poids = gsplat_runner.charger_masques(projet, ["a.png"], (4, 4), torch)

    assert poids[0, 0].sum() == 0.0
    assert poids[0, 3].sum() == 0.0
    assert poids[0, 1].sum() == 4.0


def test_une_vue_sans_masque_garde_tous_ses_pixels(tmp_path):
    projet = project.creer(tmp_path / "scan")
    _masque(projet.racine / "masks" / "vitre", "a", 4, 4, np.s_[0:2, :])

    poids = gsplat_runner.charger_masques(projet, ["a.png", "b.png"], (4, 4), torch)

    assert poids[1].sum() == 16.0, "la vue b n'a pas de masque : rien ne doit être exclu"


def test_un_masque_de_taille_differente_est_redimensionne(tmp_path):
    """Les masques peuvent venir d'un modèle qui travaille en basse résolution."""
    projet = project.creer(tmp_path / "scan")
    _masque(projet.racine / "masks" / "vitre", "a", 2, 2, np.s_[0:1, :])

    poids = gsplat_runner.charger_masques(projet, ["a.png"], (8, 8), torch)

    assert poids.shape == (1, 8, 8)
    assert poids[0, 0].sum() == 0.0
    assert poids[0, 7].sum() == 8.0


def test_la_loss_masquee_est_une_moyenne_ponderee():
    """Diviser par le nombre de pixels ferait compter moins une vue masquée.

    C'est le piège : une vue dont la moitié est masquée verrait sa loss divisée
    par deux, donc pèserait deux fois moins dans l'optimisation — exactement
    l'inverse de ce qu'on veut.
    """
    rendu = torch.zeros(1, 4, 4, 3)
    verite = torch.ones(1, 4, 4, 3)
    poids = torch.ones(1, 4, 4)
    poids[0, 0:2, :] = 0.0  # la moitié est ignorée

    ponderee = ((rendu - verite).abs() * poids.unsqueeze(-1)).sum()
    ponderee = ponderee / poids.sum().clamp_min(1.0) / 3.0

    # L'erreur vaut 1 partout : la moyenne pondérée doit valoir 1, pas 0,5.
    assert abs(float(ponderee) - 1.0) < 1e-6
