# SPDX-License-Identifier: Apache-2.0
"""Preparation de gsplat : correctif Windows et environnement de compilation.

gsplat ne publie aucun binaire — sa wheel PyPI est `py3-none-any`, sans aucun
kernel. La compilation CUDA se declenche au **premier appel de rasterisation**,
sur la machine de l'utilisateur, via ninja. Ce module rend cette compilation
possible sous Windows, ou elle echoue sans lui pour deux raisons distinctes :

1. **Les drapeaux du compilateur hote sont ecrits pour GCC.** `_backend.py`
   passe `-O3` et `-Wno-attributes` sans branche par plateforme ; `cl.exe`
   repond `D8021: invalid numeric argument`. D'ou le correctif versionne dans
   `third_party/patches/`, applique au submodule et proposable en amont.

2. **`cl.exe` n'existe que dans un « Developer Command Prompt ».** Blender
   lancera le sidecar par `subprocess` depuis un environnement ordinaire, ou il
   est introuvable. Il faut donc localiser `vcvars64.bat` et injecter soi-meme
   les variables — sinon le premier entrainement echoue chez l'utilisateur au
   milieu de centaines de lignes de log nvcc.
"""

from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from gamb_engine.proc import executer

# Version de gsplat epinglee par le submodule, et testee avec cette stack.
GSPLAT_VERSION = "1.5.3"
TORCH_VERSION = "2.8.0"
TORCH_INDEX = "https://download.pytorch.org/whl/cu128"

RACINE_DEPOT = Path(__file__).resolve().parents[2]
SUBMODULE_GSPLAT = RACINE_DEPOT / "third_party" / "gsplat"
PATCH_MSVC = RACINE_DEPOT / "third_party" / "patches" / "0001-gsplat-msvc-flags.patch"


class PreparationImpossible(Exception):
    """Un prerequis manque et l'utilisateur doit agir."""


# --- Le correctif ------------------------------------------------------------


# gsplat a lui-meme un sous-submodule : glm, dont dependent tous ses kernels.
GLM = SUBMODULE_GSPLAT / "gsplat" / "cuda" / "csrc" / "third_party" / "glm"
GLM_ENTETE = GLM / "glm" / "glm.hpp"


def submodule_present() -> bool:
    """Un clone sans `--recurse-submodules` donne un dossier vide."""
    return (SUBMODULE_GSPLAT / "gsplat" / "cuda" / "_backend.py").is_file()


def glm_present() -> bool:
    """glm est un submodule **imbrique** dans gsplat.

    Sans lui, la compilation part quand meme et echoue au dixieme fichier sur
    des en-tetes manquantes, dans plusieurs milliers de lignes de log nvcc. Le
    verifier avant de compiler transforme une soiree perdue en une phrase.
    """
    return GLM_ENTETE.is_file()


def _git_gsplat(*arguments: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-C", str(SUBMODULE_GSPLAT), *arguments],
        capture_output=True,
        text=True,
        check=False,
    )


def patch_applique() -> bool:
    """Vrai si le correctif est deja en place.

    Teste en demandant a git s'il peut appliquer le patch **a l'envers** : c'est
    le seul test fiable, et il est idempotent.
    """
    if not PATCH_MSVC.is_file():
        return False
    resultat = _git_gsplat("apply", "--reverse", "--check", str(PATCH_MSVC))
    return resultat.returncode == 0


def appliquer_patch() -> bool:
    """Applique le correctif MSVC au submodule. Idempotent.

    Renvoie True si le correctif a ete pose maintenant, False s'il y etait deja.
    """
    if not submodule_present():
        raise PreparationImpossible(
            f"{SUBMODULE_GSPLAT} est vide — lance "
            "`git submodule update --init --recursive`"
        )
    if not glm_present():
        raise PreparationImpossible(
            "glm est absent — c'est un submodule imbrique dans gsplat, et tous ses "
            "kernels en dependent. Lance `git submodule update --init --recursive` "
            "AVANT d'appliquer le correctif : une fois le correctif pose, le "
            "submodule est modifie et git refuse de le mettre a jour.\n"
            f"Attendu : {GLM_ENTETE}"
        )
    if not PATCH_MSVC.is_file():
        raise PreparationImpossible(f"correctif introuvable : {PATCH_MSVC}")

    if patch_applique():
        return False

    resultat = _git_gsplat("apply", str(PATCH_MSVC))
    if resultat.returncode != 0:
        raise PreparationImpossible(
            f"le correctif ne s'applique pas sur ce commit de gsplat :\n{resultat.stderr}\n"
            "Le submodule a probablement bouge ; il faut regenerer le patch."
        )
    return True


# --- L'environnement de compilation ------------------------------------------


@dataclass(frozen=True)
class Outillage:
    nvcc: str | None
    vcvars: Path | None

    @property
    def complet(self) -> bool:
        if sys.platform == "win32":
            return self.nvcc is not None and self.vcvars is not None
        return self.nvcc is not None

    @property
    def manquant(self) -> list[str]:
        absents = []
        if self.nvcc is None:
            absents.append("CUDA Toolkit (nvcc)")
        if sys.platform == "win32" and self.vcvars is None:
            absents.append("Visual Studio avec les outils VC++ (vcvars64.bat)")
        return absents


def trouver_vcvars() -> Path | None:
    """Localise `vcvars64.bat` via vswhere, l'outil officiel prevu pour ca."""
    if sys.platform != "win32":
        return None
    vswhere = Path("C:/Program Files (x86)/Microsoft Visual Studio/Installer/vswhere.exe")
    if not vswhere.is_file():
        return None
    installation = executer(
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
    if not installation:
        return None
    chemin = Path(installation) / "VC" / "Auxiliary" / "Build" / "vcvars64.bat"
    return chemin if chemin.is_file() else None


def outillage() -> Outillage:
    import shutil

    return Outillage(nvcc=shutil.which("nvcc"), vcvars=trouver_vcvars())


def environnement_msvc(base: dict[str, str] | None = None) -> dict[str, str]:
    """Renvoie un environnement ou `cl.exe` est joignable.

    Sous Linux il n'y a rien a faire. Sous Windows, on execute `vcvars64.bat`
    dans un `cmd` et on recupere les variables qu'il a posees — c'est la seule
    facon supportee par Microsoft d'obtenir cet environnement.
    """
    environnement = dict(base if base is not None else os.environ)
    if sys.platform != "win32":
        return environnement

    vcvars = trouver_vcvars()
    if vcvars is None:
        raise PreparationImpossible(
            "vcvars64.bat introuvable — installe Visual Studio avec les outils "
            "« Desktop development with C++ », ou gsplat ne pourra pas compiler."
        )

    # `shell=True` et non une liste : passer ["cmd", "/c", ...] fait requoter la
    # commande par subprocess, et cmd remange les guillemets du chemin. La
    # sortie de vcvars est jetee, mais **pas** son stderr — sinon un echec
    # arrive ici sans aucun message.
    resultat = subprocess.run(
        f'"{vcvars}" >nul && set',
        shell=True,
        capture_output=True,
        text=True,
        check=False,
    )
    if resultat.returncode != 0:
        detail = resultat.stderr.strip() or resultat.stdout.strip() or "aucun message"
        raise PreparationImpossible(f"vcvars64.bat a echoue :\n{detail}")

    for ligne in resultat.stdout.splitlines():
        cle, _, valeur = ligne.partition("=")
        if cle and valeur:
            environnement[cle] = valeur
    return environnement


def environnement_execution(base: dict[str, str] | None = None) -> dict[str, str]:
    """L'environnement sous lequel gsplat doit etre **importe**, pas seulement compile.

    Deux ajouts au `PATH`, pour deux raisons distinctes :

    - La chaine MSVC, parce que gsplat re-entre dans le chemin JIT a **chaque
      import**, meme quand les kernels sont deja compiles. Bonus non evident :
      `vcvars64.bat` place au passage le ninja embarque de Visual Studio.
    - Le dossier de l'interpreteur courant, parce que le `ninja` installe par
      pip y vit (`Scripts/` sous Windows, `bin/` ailleurs) et reste invisible
      quand on appelle `python.exe` directement, sans venv active. C'est le cas
      du sidecar lance par Blender.
    """
    environnement = environnement_msvc(base)
    dossier_interpreteur = str(Path(sys.executable).parent)
    environnement["PATH"] = dossier_interpreteur + os.pathsep + environnement.get("PATH", "")
    return environnement


def activer() -> None:
    """Applique l'environnement d'execution au processus courant. Idempotent.

    A appeler **avant** le premier import de gsplat. Le sidecar etant notre
    processus, le muter est plus simple et plus sur qu'un aller-retour par
    subprocess.
    """
    os.environ.update(environnement_execution())
