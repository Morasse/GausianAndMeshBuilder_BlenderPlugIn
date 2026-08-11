# SPDX-License-Identifier: GPL-3.0-or-later
"""Preferences de l'extension : ou trouver le moteur, et sur quelle adresse.

Ne pas ajouter `from __future__ import annotations` dans ce module. Blender
enregistre les proprietes en lisant `__annotations__`, et cet import futur les
transforme en chaines de caracteres jamais evaluees : les proprietes
disparaissent silencieusement et l'extension s'active sans rien afficher.
"""

from pathlib import Path

import bpy

from . import client


def _moteur_par_defaut() -> str:
    """Devine le dossier du moteur dans une copie de travail du depot.

    Vrai dans un clone (`<depot>/engine`), faux une fois l'extension installee
    depuis un ZIP — d'ou le repli sur une chaine vide plutot qu'un chemin
    invente qui donnerait une erreur incomprehensible.
    """
    candidat = Path(__file__).resolve().parents[2] / "engine"
    return str(candidat) if (candidat / "pyproject.toml").is_file() else ""


class GAMB_AddonPreferences(bpy.types.AddonPreferences):
    bl_idname = __package__

    chemin_moteur: bpy.props.StringProperty(
        name="Dossier du moteur",
        description="Dossier engine/ du depot. uv y trouvera l'environnement et les dependances",
        subtype="DIR_PATH",
        default=_moteur_par_defaut(),
    )

    chemin_python: bpy.props.StringProperty(
        name="Python (optionnel)",
        description=(
            "Interpreteur a utiliser explicitement. Laisser vide pour laisser uv choisir "
            "dans la fenetre 3.11-3.12"
        ),
        subtype="FILE_PATH",
        default="",
    )

    hote: bpy.props.StringProperty(name="Hote", default=client.HOTE_DEFAUT)

    port: bpy.props.IntProperty(name="Port", default=client.PORT_DEFAUT, min=1, max=65535)

    def draw(self, _context):
        colonne = self.layout.column()
        colonne.prop(self, "chemin_moteur")
        colonne.prop(self, "chemin_python")
        ligne = colonne.row(align=True)
        ligne.prop(self, "hote")
        ligne.prop(self, "port")
        colonne.label(text="Le moteur ecoute en local et n'a pas d'authentification.")


def obtenir(context):
    """Les preferences de cette extension, depuis n'importe quel operateur."""
    return context.preferences.addons[__package__].preferences
