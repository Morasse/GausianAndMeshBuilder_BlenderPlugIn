# SPDX-License-Identifier: GPL-3.0-or-later
"""Extension Blender de GAMB.

Ce paquet n'importe **rien** de lourd : ni torch, ni numpy, ni requests. Tout
le travail vit dans le sidecar, joint par HTTP. C'est la decision d'architecture
n°1 du projet, et elle se tient a cet endroit precis : le jour ou un import
lourd apparait ici, un autre addon qui embarque la meme bibliotheque entrera en
conflit avec celui-ci, et un plantage CUDA fera tomber Blender avec la scene.

Les metadonnees de l'extension sont dans `blender_manifest.toml`, pas dans un
`bl_info` — c'est le format des extensions Blender 4.2+.
"""

import bpy

from . import client, ops, prefs, ui
from .state import etat

# Cadence du sondage de /health. Assez lent pour etre invisible en charge,
# assez vif pour qu'un demarrage paraisse instantane.
PERIODE_SONDAGE_S = 2.0

_CLASSES = (prefs.GAMB_AddonPreferences, *ops.CLASSES, *ui.CLASSES)


def _reglages():
    """Les preferences, ou None si l'extension est en cours de desactivation."""
    try:
        return prefs.obtenir(bpy.context)
    except (KeyError, AttributeError):
        return None


def _redessiner_panneaux() -> None:
    for fenetre in bpy.context.window_manager.windows:
        for zone in fenetre.screen.areas:
            if zone.type == "VIEW_3D":
                zone.tag_redraw()


def _sonder_moteur() -> float:
    """Timer de sondage.

    Tourne dans le fil principal de Blender : il ne doit donc jamais bloquer.
    Le delai de garde du client est d'une seconde, et `client.sante` ne leve
    jamais — une exception ici desenregistrerait le timer en silence, et le
    panneau resterait fige sur un etat perime sans que personne ne le sache.
    """
    reglages = _reglages()
    if reglages is None:
        return PERIODE_SONDAGE_S

    etait_en_ligne = etat.en_ligne
    charge, raison = client.sante(reglages.hote, reglages.port)
    if charge is None:
        etat.hors_ligne(raison)
    else:
        etat.en_ligne_avec(charge)

    if etat.en_ligne != etait_en_ligne:
        _redessiner_panneaux()

    return PERIODE_SONDAGE_S


def register() -> None:
    for classe in _CLASSES:
        bpy.utils.register_class(classe)

    if not bpy.app.timers.is_registered(_sonder_moteur):
        bpy.app.timers.register(_sonder_moteur, first_interval=1.0, persistent=True)


def unregister() -> None:
    if bpy.app.timers.is_registered(_sonder_moteur):
        bpy.app.timers.unregister(_sonder_moteur)

    # Ne pas laisser un sidecar orphelin tourner apres desactivation.
    ops.arreter_a_la_fermeture()

    for classe in reversed(_CLASSES):
        bpy.utils.unregister_class(classe)
