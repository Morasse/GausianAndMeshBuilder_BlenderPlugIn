# SPDX-License-Identifier: GPL-3.0-or-later
"""Verification de bout en bout : Blender -> addon -> HTTP -> sidecar -> GPU.

Ce que le CI ne peut pas faire. Les tests de `engine/tests` couvrent chaque
morceau isolement ; celui-ci verifie qu'ils se parlent, dans le vrai Python de
Blender, contre un vrai sidecar qui tourne.

Usage — le moteur doit ecouter d'abord :

    gamb serve
    blender --background --factory-startup --python scripts/verifier_dans_blender.py

Sortie attendue : `RESULTAT: TOUT VERT`, et la ligne exacte que le panneau
affiche.
"""

import sys
import traceback
from pathlib import Path

RACINE_DEPOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE_DEPOT / "addon"))

import bpy  # noqa: E402

echecs: list[str] = []


def verifier(condition: bool, message: str) -> None:
    print(f"  {'OK  ' if condition else 'ECHEC'} {message}")
    if not condition:
        echecs.append(message)


class ReglagesFactices:
    """Un addon importe a la main n'a pas d'entree dans les preferences."""

    hote = "127.0.0.1"
    port = 8765
    chemin_moteur = ""
    chemin_python = ""


try:
    import gausian_and_mesh_builder as gamb

    gamb.register()
    gamb.prefs.obtenir = lambda _context: ReglagesFactices()

    print("Python de Blender :", ".".join(str(n) for n in sys.version_info[:3]))

    resultat = bpy.ops.gamb.rafraichir_etat()
    verifier(resultat == {"FINISHED"}, f"operateur rafraichir_etat -> {resultat}")

    etat = gamb.state.etat
    verifier(etat.en_ligne, "l'addon voit le moteur en ligne")
    verifier(etat.statut == "online", f"statut = {etat.statut!r}")

    charge = etat.charge or {}
    gpu = charge.get("gpu")
    verifier(gpu is not None, "le GPU remonte jusqu'a l'addon")
    if gpu:
        verifier(gpu["vram_totale_go"] > 0, f"VRAM totale = {gpu['vram_totale_go']} Go")
        verifier(gpu["vram_libre_go"] > 0, f"VRAM libre  = {gpu['vram_libre_go']} Go")

    ligne = gamb.client.resume(charge)
    print(f"\n  >>> PANNEAU : {ligne}\n")
    verifier("VRAM" in ligne, "la ligne du panneau est exploitable")

    # La decision d'architecture n°1, verifiee la ou elle compte vraiment.
    lourds = [m for m in ("torch", "numpy", "scipy", "cv2") if m in sys.modules]
    verifier(not lourds, f"aucune dependance lourde dans le processus Blender (vu : {lourds})")

    gamb.unregister()

except Exception:
    traceback.print_exc()
    echecs.append("exception")

print("RESULTAT:", "TOUT VERT" if not echecs else f"{len(echecs)} ECHEC(S)")
if echecs:
    sys.exit(1)
