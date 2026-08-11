# SPDX-License-Identifier: GPL-3.0-or-later
"""Operateurs de pilotage du moteur.

Regle absolue de tout l'addon : **aucun appel bloquant dans un operateur.**
Un `wait()`, un `sleep()` ou une requete sans delai de garde gele Blender, et
un Blender gele est indiscernable d'un Blender plante pour l'utilisateur. Les
operateurs d'ici ne font que declencher ; c'est le timer de `__init__` qui
observe le resultat.
"""

import subprocess
from pathlib import Path

import bpy

from . import client, lanceur, naming
from . import prefs as preferences
from .state import etat

# Handle du sidecar lance par cette session de Blender. None si le moteur
# tourne deja par ailleurs (demarre a la main, en CLI) — auquel cas l'addon s'y
# connecte sans chercher a le controler.
_processus: subprocess.Popen | None = None


def _chemin_journal() -> Path:
    dossier = bpy.utils.user_resource("CONFIG", path=naming.EXTENSION_ID, create=True)
    return Path(dossier) / "moteur.log"


def moteur_lance_ici() -> bool:
    return _processus is not None and _processus.poll() is None


class GAMB_OT_demarrer_moteur(bpy.types.Operator):
    bl_idname = naming.operator_id("demarrer_moteur")
    bl_label = "Demarrer le moteur"
    bl_description = "Lance le sidecar en arriere-plan, sans bloquer Blender"

    def execute(self, context):
        global _processus

        if etat.en_ligne:
            self.report({"INFO"}, "Le moteur repond deja.")
            return {"CANCELLED"}

        reglages = preferences.obtenir(context)
        commande = lanceur.commande_demarrage(
            Path(bpy.path.abspath(reglages.chemin_moteur)),
            reglages.hote,
            reglages.port,
            Path(bpy.path.abspath(reglages.chemin_python)) if reglages.chemin_python else None,
        )

        if commande is None:
            self.report(
                {"ERROR"},
                "Moteur introuvable : renseigne le dossier engine/ dans les preferences, "
                "ou installe uv.",
            )
            return {"CANCELLED"}

        journal = _chemin_journal()
        try:
            _processus = lanceur.demarrer(commande, journal)
        except OSError as erreur:
            self.report({"ERROR"}, f"Demarrage impossible : {erreur}")
            return {"CANCELLED"}

        etat.demarrage_demande = True
        etat.journal = str(journal)
        etat.hors_ligne("demarrage en cours")
        self.report({"INFO"}, f"Moteur lance. Journal : {journal}")
        return {"FINISHED"}


class GAMB_OT_arreter_moteur(bpy.types.Operator):
    bl_idname = naming.operator_id("arreter_moteur")
    bl_label = "Arreter le moteur"
    bl_description = "Arrete le sidecar lance depuis Blender"

    @classmethod
    def poll(cls, _context):
        return moteur_lance_ici()

    def execute(self, _context):
        global _processus

        lanceur.arreter(_processus)
        _processus = None
        etat.demarrage_demande = False
        etat.hors_ligne("arrete")
        self.report({"INFO"}, "Moteur arrete.")
        return {"FINISHED"}


class GAMB_OT_rafraichir_etat(bpy.types.Operator):
    bl_idname = naming.operator_id("rafraichir_etat")
    bl_label = "Rafraichir"
    bl_description = "Interroge le moteur immediatement, sans attendre le prochain cycle"

    def execute(self, context):
        reglages = preferences.obtenir(context)
        charge, raison = client.sante(reglages.hote, reglages.port)
        if charge is None:
            etat.hors_ligne(raison)
            self.report({"WARNING"}, f"Moteur injoignable — {raison}")
        else:
            etat.en_ligne_avec(charge)
            self.report({"INFO"}, client.resume(charge))
        return {"FINISHED"}


CLASSES = (
    GAMB_OT_demarrer_moteur,
    GAMB_OT_arreter_moteur,
    GAMB_OT_rafraichir_etat,
)


def arreter_a_la_fermeture() -> None:
    """Appele au desenregistrement : ne pas laisser un moteur orphelin derriere soi."""
    global _processus
    lanceur.arreter(_processus)
    _processus = None
