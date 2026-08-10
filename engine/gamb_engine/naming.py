# SPDX-License-Identifier: Apache-2.0 OR GPL-3.0-or-later
#
# Table de nommage de GAMB — source de verite unique du projet.
#
# ┌───────────────────────────────────────────────────────────────────────────┐
# │ CE FICHIER EXISTE EN DEUX EXEMPLAIRES, IDENTIQUES OCTET POUR OCTET :      │
# │     engine/gamb_engine/naming.py                                          │
# │     addon/gausian_and_mesh_builder/naming.py                              │
# │                                                                           │
# │ engine/tests/test_naming.py compare leurs empreintes et casse le CI a la  │
# │ moindre divergence. Toute modification se fait dans les deux a la fois.   │
# └───────────────────────────────────────────────────────────────────────────┘
#
# ┌───────────────────────────────────────────────────────────────────────────┐
# │ « Gausian » s'ecrit avec UN SEUL « s ». Ce n'est pas une faute de frappe. │
# │ Ne le « corrige » pas, ni ici, ni ailleurs, ni en passant.                │
# │                                                                           │
# │ Le danger n'est pas l'orthographe : c'est qu'une normalisation partielle  │
# │ casse les imports, l'URL du remote et l'id de l'extension Blender d'une   │
# │ facon particulierement penible a debugger. Si le nom doit changer, ca se  │
# │ decide ici et nulle part ailleurs.                                        │
# └───────────────────────────────────────────────────────────────────────────┘
#
# Deux licences parce que ce fichier vit dans deux sous-arbres de licences
# differentes (addon/ en GPL-3.0, engine/ en Apache-2.0) tout en devant rester
# identique. Voir LICENSING.md.
#
# Aucun import : ce module est charge par l'addon Blender, qui n'a le droit
# d'utiliser que la bibliotheque standard. Ne jamais ajouter de dependance ici.

# --- Depot -------------------------------------------------------------------

REPO_NAME = "GausianAndMeshBuilder_BlenderPlugIn"
REPO_URL = "https://github.com/Morasse/GausianAndMeshBuilder_BlenderPlugIn"

# --- Extension Blender -------------------------------------------------------

# `id` du blender_manifest.toml, et nom du dossier de l'addon.
EXTENSION_ID = "gausian_and_mesh_builder"

# `name` du manifeste, affiche dans l'UI de Blender.
EXTENSION_NAME = "Gausian And Mesh Builder"

# --- Marque ------------------------------------------------------------------

ACRONYM = "GAMB"

# Onglet du N-panel dans le 3D Viewport (bl_category).
NPANEL_TAB = "GAMB"

# --- Sidecar -----------------------------------------------------------------

# Package Python importable.
ENGINE_PACKAGE = "gamb_engine"

# Nom de distribution (pip / pyproject).
ENGINE_DISTRIBUTION = "gamb-engine"

# Commande CLI. Tout ce que fait l'addon doit etre faisable par ce binaire,
# sans Blender.
CLI_COMMAND = "gamb"

# --- Conventions -------------------------------------------------------------

# Prefixe des bl_idname des operateurs, ex. "gamb.start_training".
OPERATOR_PREFIX = "gamb"

# Manifeste du projet sur disque. C'est lui la source de verite du pipeline,
# pas le fichier .blend.
PROJECT_MANIFEST_FILENAME = "gamb.json"


def operator_id(name: str) -> str:
    """Construit le `bl_idname` d'un operateur GAMB.

    `operator_id("start_training")` renvoie `"gamb.start_training"`.
    """
    return f"{OPERATOR_PREFIX}.{name}"
