# SPDX-License-Identifier: Apache-2.0
"""Gardes sur la préparation de gsplat.

Le test qui porte tout est `test_le_correctif_s_applique_sur_le_commit_epingle` :
il demande à git de vérifier le patch **sans l'appliquer**. Le jour où quelqu'un
fait avancer le submodule sans régénérer le correctif, le CI casse ici — au lieu
de laisser découvrir le problème au milieu d'une compilation CUDA de 77 secondes
sur la machine de quelqu'un d'autre.

Aucun test de ce fichier ne modifie le submodule.
"""

import subprocess

import pytest

from gamb_engine import build


def _sauter_si_submodule_absent():
    if not build.submodule_present():
        pytest.skip("submodule gsplat non initialisé (git submodule update --init)")


def test_le_correctif_est_versionne():
    assert build.PATCH_MSVC.is_file(), (
        f"correctif absent : {build.PATCH_MSVC}. Sans lui, gsplat ne compile pas sous Windows."
    )


def test_le_correctif_cible_le_bon_fichier():
    texte = build.PATCH_MSVC.read_text(encoding="utf-8")
    assert "gsplat/cuda/_backend.py" in texte
    # Le hunk qui porte tout : MSVC refuse ces deux drapeaux GCC.
    assert "-Wno-attributes" in texte
    assert "/O2" in texte


def test_le_correctif_s_applique_sur_le_commit_epingle():
    """Vérifié sans muter le submodule — `--check` ne fait qu'essayer."""
    _sauter_si_submodule_absent()

    if build.patch_applique():
        pytest.skip("le correctif est déjà appliqué dans cette copie de travail")

    resultat = subprocess.run(
        ["git", "-C", str(build.SUBMODULE_GSPLAT), "apply", "--check", str(build.PATCH_MSVC)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert resultat.returncode == 0, (
        f"le correctif ne s'applique plus sur ce commit de gsplat :\n{resultat.stderr}\n"
        "Le submodule a bougé ; régénère le patch."
    )


def test_les_versions_epinglees_sont_celles_du_spike():
    """Prendre « la dernière version » est précisément ce qui a cassé le spike."""
    assert build.GSPLAT_VERSION == "1.5.3"
    assert build.TORCH_VERSION == "2.8.0"
    assert "cu128" in build.TORCH_INDEX


def test_l_outillage_se_sonde_sans_lever():
    outils = build.outillage()
    assert isinstance(outils.manquant, list)
    assert isinstance(outils.complet, bool)


def test_la_racine_cuda_se_deduit_de_nvcc(monkeypatch, tmp_path):
    """Beaucoup d'extensions CUDA exigent CUDA_HOME et échouent sans rien expliquer.

    gsplat s'en passe — torch déduit le chemin depuis nvcc — mais d'autres non,
    et le message « CUDA_HOME environment variable is not set » ne dit pas où
    regarder.
    """
    faux_nvcc = tmp_path / "v12.8" / "bin" / "nvcc.exe"
    faux_nvcc.parent.mkdir(parents=True)
    faux_nvcc.write_text("", encoding="utf-8")
    monkeypatch.setattr("shutil.which", lambda nom: str(faux_nvcc) if nom == "nvcc" else None)

    assert build.racine_cuda() == faux_nvcc.resolve().parent.parent


def test_la_racine_cuda_vaut_none_sans_nvcc(monkeypatch):
    monkeypatch.setattr("shutil.which", lambda _: None)
    assert build.racine_cuda() is None


def test_patch_applique_repond_sans_lever():
    _sauter_si_submodule_absent()
    assert isinstance(build.patch_applique(), bool)


def test_appliquer_le_correctif_sans_submodule_le_dit(monkeypatch):
    """Un clone sans --recurse-submodules donne un dossier vide et une erreur illisible."""
    monkeypatch.setattr(build, "submodule_present", lambda: False)

    with pytest.raises(build.PreparationImpossible, match="submodule update"):
        build.appliquer_patch()
