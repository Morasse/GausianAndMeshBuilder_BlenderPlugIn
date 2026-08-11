# SPDX-License-Identifier: GPL-3.0-or-later
"""Panneaux du N-panel.

A P1 il n'y a qu'un panneau, `Moteur`, et c'est deliberement le premier de la
pile : la spec veut qu'un utilisateur voie l'etat du sidecar et la VRAM libre
avant de lancer quoi que ce soit. Un panneau qui ment sur l'etat du moteur
coute plus cher qu'un panneau absent.

Les sous-panneaux par etape du pipeline viendront s'accrocher ici a partir de
P2, chacun avec son pastille d'etat.
"""

import bpy

from . import naming, ops
from .state import etat

# Pastilles d'etat, dans le vocabulaire de la spec : pas fait / en cours / fait.
_ICONE_PAR_STATUT = {
    "online": "CHECKMARK",
    "demarrage": "SORTTIME",
    "hors ligne": "X",
}


class GAMB_PT_moteur(bpy.types.Panel):
    bl_label = "Moteur"
    bl_idname = f"{naming.ACRONYM}_PT_moteur"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = naming.NPANEL_TAB

    def draw(self, context):
        disposition = self.layout

        entete = disposition.row(align=True)
        entete.label(text=etat.statut, icon=_ICONE_PAR_STATUT.get(etat.statut, "QUESTION"))
        entete.operator(ops.GAMB_OT_rafraichir_etat.bl_idname, text="", icon="FILE_REFRESH")

        charge = etat.charge
        if charge is not None:
            gpu = charge.get("gpu")
            boite = disposition.box().column(align=True)
            if gpu:
                boite.label(text=gpu["nom"], icon="SYSTEM")
                boite.label(
                    text=f"VRAM {gpu['vram_libre_go']} Go libres sur {gpu['vram_totale_go']} Go"
                )
            else:
                boite.label(text="Aucun GPU NVIDIA detecte", icon="ERROR")
            boite.label(text=f"{charge.get('moteur', '?')} {charge.get('version', '')}")
        elif etat.detail:
            disposition.label(text=etat.detail, icon="INFO")

        boutons = disposition.row(align=True)
        boutons.operator(ops.GAMB_OT_demarrer_moteur.bl_idname, icon="PLAY")
        boutons.operator(ops.GAMB_OT_arreter_moteur.bl_idname, icon="PAUSE")

        if etat.journal:
            disposition.label(text=f"Journal : {etat.journal}")


CLASSES = (GAMB_PT_moteur,)
