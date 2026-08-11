# SPDX-License-Identifier: Apache-2.0
"""Appels de sondes externes, avec les deux garde-fous qui comptent sous Windows.

Ce module existe pour deux raisons, toutes deux apprises a la dure :

- **Pas de console noire.** Un `subprocess` lance depuis Blender ouvre une
  fenetre de console a chaque appel si on ne passe pas `CREATE_NO_WINDOW`.
- **Pas de blocage.** Un interpreteur casse, un `nvidia-smi` qui pend sur un
  driver en vrac : sans delai de garde, c'est Blender qui gele. Toute sonde a
  donc un timeout, et une sonde qui echoue renvoie None au lieu de lever.
"""

from __future__ import annotations

import subprocess
import sys

# Genereux pour un demarrage a froid de nvidia-smi, court devant la patience
# d'un utilisateur qui vient de cliquer.
DELAI_SONDE_S = 10


def options_subprocess() -> dict:
    """Options de creation de processus a passer a subprocess sous Windows."""
    if sys.platform == "win32":
        return {"creationflags": getattr(subprocess, "CREATE_NO_WINDOW", 0)}
    return {}


def executer(commande: list[str], delai_s: float = DELAI_SONDE_S) -> str | None:
    """Lance une sonde et renvoie sa sortie standard nettoyee.

    Renvoie None si la commande est absente, echoue, ou depasse le delai — un
    appelant n'a jamais a envelopper cet appel dans un try.
    """
    try:
        resultat = subprocess.run(
            commande,
            capture_output=True,
            text=True,
            timeout=delai_s,
            check=False,
            **options_subprocess(),
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if resultat.returncode != 0:
        return None
    return resultat.stdout.strip()
