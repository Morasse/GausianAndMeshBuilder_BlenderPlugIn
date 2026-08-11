# SPDX-License-Identifier: GPL-3.0-or-later
"""Demarrage du sidecar depuis l'addon.

**Ce module n'importe pas bpy** — la construction de la commande est une
fonction pure, donc testable hors Blender, et c'est la partie qui merite le
plus d'etre testee.

Le lancement passe par `uv run` quand uv est disponible, et ce n'est pas un
detail de commodite : uv choisit l'interpreteur dans la fenetre de versions,
cree l'environnement s'il manque et installe les dependances verrouillees. Tout
ce que l'utilisateur n'a pas a faire a la main est ce qu'il ne peut pas rater.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

DELAI_ARRET_S = 5


def _options_subprocess() -> dict:
    """Pas de console noire qui surgit devant Blender a chaque demarrage."""
    if sys.platform == "win32":
        return {"creationflags": getattr(subprocess, "CREATE_NO_WINDOW", 0)}
    return {}


def commande_demarrage(
    chemin_moteur: Path,
    hote: str,
    port: int,
    chemin_python: Path | None = None,
) -> list[str] | None:
    """Construit la commande de demarrage, ou None si rien n'est utilisable.

    Deux voies, dans cet ordre :

    1. `uv run --project <moteur> gamb serve` — uv resout l'interpreteur et
       l'environnement tout seul.
    2. `<python> -m gamb_engine.cli serve` — repli explicite quand l'utilisateur
       a designe un interpreteur a la main.
    """
    adresse = ["serve", "--hote", hote, "--port", str(port)]

    if chemin_python is not None and Path(chemin_python).is_file():
        return [str(chemin_python), "-m", "gamb_engine.cli", *adresse]

    uv = shutil.which("uv")
    if uv is not None and Path(chemin_moteur).is_dir():
        return [uv, "run", "--project", str(chemin_moteur), "gamb", *adresse]

    return None


def demarrer(commande: list[str], chemin_journal: Path | None = None) -> subprocess.Popen:
    """Lance le moteur en arriere-plan. Ne bloque jamais l'appelant."""
    if chemin_journal is not None:
        chemin_journal.parent.mkdir(parents=True, exist_ok=True)
        flux = chemin_journal.open("w", encoding="utf-8", errors="replace")
        sortie: object = flux
    else:
        sortie = subprocess.DEVNULL

    return subprocess.Popen(
        commande,
        stdout=sortie,
        stderr=subprocess.STDOUT,
        stdin=subprocess.DEVNULL,
        **_options_subprocess(),
    )


def arreter(processus: subprocess.Popen | None) -> None:
    """Arret propre, puis brutal si le moteur ne coopere pas."""
    if processus is None or processus.poll() is not None:
        return
    processus.terminate()
    try:
        processus.wait(timeout=DELAI_ARRET_S)
    except subprocess.TimeoutExpired:
        processus.kill()
