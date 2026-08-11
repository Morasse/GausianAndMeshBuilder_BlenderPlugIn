# SPDX-License-Identifier: Apache-2.0
"""Outillage commun aux tests.

Le point delicat : plusieurs modules de l'addon (`client`, `lanceur`, `state`)
sont volontairement ecrits sans `bpy` pour rester testables hors Blender. Mais
ils vivent dans un paquet dont le `__init__.py`, lui, importe `bpy`. Les
importer normalement echouerait donc en CI.

On les charge par chemin, sans passer par le paquet. Si un de ces modules
venait a importer `bpy` un jour, le test correspondant casserait — ce qui est
exactement le signal voulu.
"""

import importlib.util
import sys
from pathlib import Path

import pytest

RACINE_DEPOT = Path(__file__).resolve().parents[2]
DOSSIER_ADDON = RACINE_DEPOT / "addon" / "gausian_and_mesh_builder"


def charger_module_addon(nom: str):
    """Charge un module de l'addon isolement, hors de son paquet."""
    chemin = DOSSIER_ADDON / f"{nom}.py"
    specification = importlib.util.spec_from_file_location(f"_addon_{nom}", chemin)
    if specification is None or specification.loader is None:
        raise ImportError(f"module d'addon introuvable : {chemin}")
    module = importlib.util.module_from_spec(specification)
    sys.modules[specification.name] = module
    specification.loader.exec_module(module)
    return module


@pytest.fixture(scope="session")
def client_addon():
    return charger_module_addon("client")


@pytest.fixture(scope="session")
def lanceur_addon():
    return charger_module_addon("lanceur")
