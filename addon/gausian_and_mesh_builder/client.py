# SPDX-License-Identifier: GPL-3.0-or-later
"""Client HTTP du sidecar.

**Ce module n'importe pas bpy.** Deux consequences voulues : il est testable
hors Blender, et il ne peut pas etre tente d'aller lire l'etat de la scene.

Il n'utilise que la bibliotheque standard. C'est une contrainte dure de tout le
dossier `addon/` : les wheels d'une extension Blender partagent le namespace de
modules global, donc embarquer une dependance ici, c'est entrer en conflit avec
tout autre addon qui embarque la meme.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any

# Doit rester identique a gamb_engine.server. Le test test_client_addon.py
# compare les deux valeurs et casse le CI si elles divergent.
HOTE_DEFAUT = "127.0.0.1"
PORT_DEFAUT = 8765

# Court volontairement : cet appel est declenche par un timer d'interface. Une
# seconde d'attente est deja perceptible, et le moteur repond en millisecondes
# quand il est la.
DELAI_DEFAUT_S = 1.0


def url_base(hote: str = HOTE_DEFAUT, port: int = PORT_DEFAUT) -> str:
    return f"http://{hote}:{port}"


def sante(
    hote: str = HOTE_DEFAUT,
    port: int = PORT_DEFAUT,
    delai_s: float = DELAI_DEFAUT_S,
) -> tuple[dict[str, Any] | None, str | None]:
    """Interroge /health.

    Renvoie `(charge, None)` si le moteur repond, `(None, raison)` sinon.
    Ne leve jamais : l'appelant est un timer d'interface, une exception qui
    remonte la desactiverait silencieusement.
    """
    url = f"{url_base(hote, port)}/health"
    try:
        with urllib.request.urlopen(url, timeout=delai_s) as reponse:
            brut = reponse.read().decode("utf-8")
    except urllib.error.HTTPError as erreur:
        return None, f"HTTP {erreur.code}"
    except (urllib.error.URLError, TimeoutError, OSError):
        # Cas nominal quand le moteur n'est pas demarre : ce n'est pas une
        # erreur a signaler bruyamment.
        return None, "hors ligne"
    except Exception as erreur:  # pragma: no cover - filet pour le timer
        return None, str(erreur)

    try:
        return json.loads(brut), None
    except json.JSONDecodeError:
        return None, "reponse illisible"


def resume(charge: dict[str, Any] | None) -> str:
    """Ligne d'etat affichable dans le panneau Blender."""
    if charge is None:
        return "hors ligne"

    morceaux = [str(charge.get("statut", "?"))]
    gpu = charge.get("gpu")
    if gpu:
        morceaux.append(f"VRAM {gpu['vram_libre_go']} / {gpu['vram_totale_go']} Go libres")
    else:
        morceaux.append("aucun GPU detecte")
    return ", ".join(morceaux)
