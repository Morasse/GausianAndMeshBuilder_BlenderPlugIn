# SPDX-License-Identifier: Apache-2.0
"""Ce que la machine peut faire : GPU, VRAM, et chaine de compilation CUDA.

**Aucune dependance, et surtout pas torch.** Interroger la VRAM en important
torch couterait plusieurs secondes de chargement et quelques centaines de Mo
resident, pour une information que `nvidia-smi` donne en un appel. Le sidecar
doit pouvoir repondre `/health` avant meme d'avoir charge le moindre modele —
c'est tout l'interet du panneau d'etat cote Blender.

La chaine de compilation est sondee parce que gsplat compile des kernels CUDA a
l'installation ou au premier run. Sur une machine sans `nvcc` ni compilateur
C++, ca echoue au milieu d'un `pip install` avec des centaines de lignes de log.
Autant le dire avant.
"""

from __future__ import annotations

import shutil
import sys
from dataclasses import dataclass
from pathlib import Path

from gamb_engine.proc import executer

_REQUETE_GPU = "name,driver_version,memory.total,memory.free"


@dataclass(frozen=True)
class Gpu:
    """Etat d'un GPU NVIDIA vu par nvidia-smi."""

    nom: str
    driver: str
    vram_totale_mo: int
    vram_libre_mo: int

    @property
    def vram_totale_go(self) -> float:
        return round(self.vram_totale_mo / 1024, 1)

    @property
    def vram_libre_go(self) -> float:
        return round(self.vram_libre_mo / 1024, 1)

    def __str__(self) -> str:
        return f"{self.nom} — {self.vram_libre_go} Go libres sur {self.vram_totale_go} Go"


@dataclass(frozen=True)
class ChaineCompilation:
    """De quoi gsplat aura besoin s'il doit compiler ses kernels."""

    nvcc: str | None
    msvc: str | None

    @property
    def complete(self) -> bool:
        # Sous Linux, gcc suffit et est suppose present ; MSVC n'est exige que
        # sous Windows.
        if sys.platform == "win32":
            return self.nvcc is not None and self.msvc is not None
        return self.nvcc is not None

    @property
    def manquant(self) -> list[str]:
        absents = []
        if self.nvcc is None:
            absents.append("CUDA Toolkit (nvcc)")
        if sys.platform == "win32" and self.msvc is None:
            absents.append("Visual Studio / outils VC++")
        return absents


def gpus() -> list[Gpu]:
    """Les GPU NVIDIA visibles. Liste vide si nvidia-smi est absent ou muet."""
    if shutil.which("nvidia-smi") is None:
        return []

    sortie = executer(
        ["nvidia-smi", f"--query-gpu={_REQUETE_GPU}", "--format=csv,noheader,nounits"]
    )
    if not sortie:
        return []

    trouves: list[Gpu] = []
    for ligne in sortie.splitlines():
        champs = [c.strip() for c in ligne.split(",")]
        if len(champs) != 4:
            continue
        nom, driver, total, libre = champs
        try:
            trouves.append(Gpu(nom, driver, int(total), int(libre)))
        except ValueError:
            continue
    return trouves


def gpu_principal() -> Gpu | None:
    """Le GPU sur lequel le moteur travaillera — un seul job GPU a la fois."""
    trouves = gpus()
    return trouves[0] if trouves else None


def _msvc() -> str | None:
    """Detecte Visual Studio via vswhere, l'outil officiel prevu pour ca."""
    if sys.platform != "win32":
        return None
    vswhere = Path("C:/Program Files (x86)/Microsoft Visual Studio/Installer/vswhere.exe")
    if not vswhere.is_file():
        return None
    sortie = executer(
        [
            str(vswhere),
            "-latest",
            "-products",
            "*",
            "-requires",
            "Microsoft.VisualStudio.Component.VC.Tools.x86.x64",
            "-property",
            "installationPath",
        ]
    )
    return sortie or None


def chaine_compilation() -> ChaineCompilation:
    """De quoi compiler du CUDA, ou la liste de ce qui manque."""
    nvcc = shutil.which("nvcc")
    version_nvcc = None
    if nvcc:
        sortie = executer([nvcc, "--version"]) or ""
        for ligne in sortie.splitlines():
            if "release" in ligne:
                version_nvcc = ligne.strip()
                break
        version_nvcc = version_nvcc or nvcc
    return ChaineCompilation(nvcc=version_nvcc, msvc=_msvc())
