# SPDX-License-Identifier: Apache-2.0
"""Gardes sur la table de nommage.

Ces tests ne verifient pas du code : ils verifient que personne — humain,
agent ou outil de refactoring — n'a normalise une chaine de nom en passant.
C'est le risque n°1 identifie dans la spec, et c'est le seul endroit du projet
ou une faute d'orthographe est la bonne reponse.
"""

from pathlib import Path

from gamb_engine import naming

REPO_ROOT = Path(__file__).resolve().parents[2]
ENGINE_COPY = REPO_ROOT / "engine" / "gamb_engine" / "naming.py"
ADDON_COPY = REPO_ROOT / "addon" / "gausian_and_mesh_builder" / "naming.py"

# Recopie litterale de la table de nommage. Volontairement dupliquee ici :
# si le test importait les valeurs, il validerait n'importe quoi.
VALEURS_ATTENDUES = {
    "REPO_NAME": "GausianAndMeshBuilder_BlenderPlugIn",
    "REPO_URL": "https://github.com/Morasse/GausianAndMeshBuilder_BlenderPlugIn",
    "EXTENSION_ID": "gausian_and_mesh_builder",
    "EXTENSION_NAME": "Gausian And Mesh Builder",
    "ACRONYM": "GAMB",
    "NPANEL_TAB": "GAMB",
    "ENGINE_PACKAGE": "gamb_engine",
    "ENGINE_DISTRIBUTION": "gamb-engine",
    "CLI_COMMAND": "gamb",
    "OPERATOR_PREFIX": "gamb",
    "PROJECT_MANIFEST_FILENAME": "gamb.json",
}


def test_les_deux_copies_existent():
    assert ENGINE_COPY.is_file(), f"copie moteur absente : {ENGINE_COPY}"
    assert ADDON_COPY.is_file(), f"copie addon absente : {ADDON_COPY}"


def test_les_deux_copies_sont_identiques_octet_pour_octet():
    """Le miroir addon ne doit jamais deriver de la copie moteur."""
    assert ENGINE_COPY.read_bytes() == ADDON_COPY.read_bytes(), (
        "Les deux copies de naming.py ont diverge. Recopie l'une sur l'autre "
        "au lieu de les editer separement."
    )


def test_valeurs_exactes():
    for attribut, attendu in VALEURS_ATTENDUES.items():
        obtenu = getattr(naming, attribut)
        assert obtenu == attendu, f"{attribut} vaut {obtenu!r}, attendu {attendu!r}"


def test_aucune_autocorrection_orthographique():
    """« Gausian » prend un seul « s », et le depot dit « Builder »."""
    for chemin in (ENGINE_COPY, ADDON_COPY):
        texte = chemin.read_text(encoding="utf-8")
        assert "Gaussian" not in texte, (
            f"{chemin.name} contient l'orthographe standard 'Gaussian'. "
            "Le nom du projet prend un seul 's' — annule la correction."
        )
        assert "Buidler" not in texte, (
            f"{chemin.name} contient 'Buidler', l'orthographe de l'ancienne "
            "spec. Le depot fait foi : c'est 'Builder'."
        )


def test_le_module_de_nommage_reste_sans_dependance():
    """L'addon Blender n'a droit qu'a la bibliotheque standard."""
    for chemin in (ENGINE_COPY, ADDON_COPY):
        for numero, ligne in enumerate(chemin.read_text(encoding="utf-8").splitlines(), 1):
            assert not ligne.startswith(("import ", "from ")), (
                f"{chemin.name}:{numero} introduit un import. Ce module doit "
                "rester chargeable dans le Python de Blender sans rien tirer."
            )


def test_operator_id():
    assert naming.operator_id("start_training") == "gamb.start_training"
