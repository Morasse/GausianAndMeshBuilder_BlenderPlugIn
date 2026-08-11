# SPDX-License-Identifier: Apache-2.0
"""Gardes sur le runner d'entraînement, hors GPU.

Le CI n'a pas de carte : ces tests couvrent tout ce qui peut l'être sans elle —
la configuration, le format de sortie, et surtout la règle qui protège le temps
de démarrage du sidecar.
"""

import struct

import pytest

from gamb_engine.train import gsplat_runner


def test_le_module_n_importe_pas_torch_au_chargement():
    """Le sidecar doit répondre /health sans payer trois secondes d'import CUDA.

    Vérifié dans un **sous-processus** neuf. Inspecter `sys.modules` depuis le
    test lui-même ne prouverait rien : il suffirait qu'un autre fichier de la
    suite ait importé torch avant pour que le résultat dépende de l'ordre
    d'exécution — dans un sens comme dans l'autre.
    """
    import subprocess
    import sys

    resultat = subprocess.run(
        [
            sys.executable,
            "-c",
            "import sys, gamb_engine.train.gsplat_runner; "
            "print('torch' in sys.modules)",
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    assert resultat.stdout.strip() == "False", (
        "importer gamb_engine.train.gsplat_runner charge torch. Les imports "
        "lourds doivent rester dans les fonctions."
    )


def test_la_configuration_par_defaut_suit_le_preset_mcmc_du_simple_trainer():
    """Un écart de réglage rendrait la comparaison de PSNR sans valeur.

    Piège attrapé une fois : le preset `mcmc` de gsplat n'a **pas** les mêmes
    défauts que son preset `default`. Utiliser la stratégie MCMC avec les
    valeurs de `default` donne un entraîneur qui n'est comparable à rien.
    """
    configuration = gsplat_runner.Configuration()

    assert configuration.lr_positions == 1.6e-4
    assert configuration.lr_echelles == 5e-3
    assert configuration.lr_opacites == 5e-2
    assert configuration.lr_quaternions == 1e-3
    assert configuration.lr_sh0 == 2.5e-3
    assert configuration.poids_ssim == 0.2
    assert configuration.degre_sh == 3
    # Spécifiques au preset mcmc :
    assert configuration.opacite_initiale == 0.5
    assert configuration.echelle_initiale == 0.1
    assert configuration.reg_opacite == 0.01
    assert configuration.reg_echelle == 0.01


def test_la_configuration_vient_des_presets():
    configuration = gsplat_runner.Configuration.depuis_preset("apercu")
    assert configuration.iterations == 3000
    assert configuration.degre_sh == 1


def test_une_surcharge_explicite_gagne():
    configuration = gsplat_runner.Configuration.depuis_preset("apercu", iterations=7)
    assert configuration.iterations == 7


def test_une_vue_sur_huit_est_mise_de_cote():
    """Le PSNR d'entraînement mesure la mémorisation ; seul celui de test compte."""
    assert gsplat_runner.PERIODE_TEST == 8


def test_le_ply_est_au_format_3dgs_conventionnel(tmp_path):
    """C'est ce format que lit l'importeur natif de Blender et SuperSplat."""
    torch = pytest.importorskip("torch")
    pytest.importorskip("numpy")

    nombre, bandes_sh = 5, 15
    parametres = {
        "means": torch.zeros(nombre, 3),
        "sh0": torch.zeros(nombre, 1, 3),
        "shN": torch.zeros(nombre, bandes_sh, 3),
        "opacities": torch.zeros(nombre),
        "scales": torch.zeros(nombre, 3),
        "quats": torch.zeros(nombre, 4),
    }
    chemin = tmp_path / "point_cloud.ply"
    gsplat_runner.ecrire_ply(chemin, parametres, torch)

    brut = chemin.read_bytes()
    entete, _, corps = brut.partition(b"end_header\n")
    texte = entete.decode("ascii")

    assert texte.startswith("ply\nformat binary_little_endian 1.0")
    assert f"element vertex {nombre}" in texte
    for attendu in ("property float x", "property float f_dc_0", "property float opacity",
                    "property float scale_0", "property float rot_3"):
        assert attendu in texte
    assert "property float f_rest_44" in texte, "SH de degré 3 : 45 coefficients attendus"

    # 3 + 3 normales + 3 sh0 + 45 shN + 1 opacité + 3 échelles + 4 quaternions
    colonnes = 3 + 3 + 3 + bandes_sh * 3 + 1 + 3 + 4
    assert len(corps) == nombre * colonnes * 4
    assert struct.unpack("<f", corps[:4])[0] == 0.0


def test_la_duree_estimee_croit_avec_les_iterations():
    courte = gsplat_runner.Configuration(iterations=1000)
    longue = gsplat_runner.Configuration(iterations=30000)
    assert gsplat_runner.duree_estimee(longue) > gsplat_runner.duree_estimee(courte)


def test_le_psnr_est_infini_pour_une_prediction_exacte():
    torch = pytest.importorskip("torch")
    image = torch.rand(1, 8, 8, 3)
    assert gsplat_runner.psnr(image, image, torch) > 100


def test_le_ssim_vaut_un_pour_une_prediction_exacte():
    torch = pytest.importorskip("torch")
    image = torch.rand(1, 3, 32, 32)
    assert abs(float(gsplat_runner.ssim(image, image, torch)) - 1.0) < 1e-4


def test_les_distances_aux_voisins_sont_positives():
    torch = pytest.importorskip("torch")
    points = torch.rand(50, 3)
    distances = gsplat_runner._distance_moyenne_voisins(points, torch, k=3)

    assert distances.shape == (50,)
    assert float(distances.min()) > 0.0
