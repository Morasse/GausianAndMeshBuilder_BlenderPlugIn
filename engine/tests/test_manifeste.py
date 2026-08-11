# SPDX-License-Identifier: Apache-2.0
"""Le manifeste Blender ne peut pas importer naming.py — donc on le verifie.

Un `blender_manifest.toml` est du TOML statique : impossible d'y importer la
table de nommage. La duplication est inevitable ; ce qui ne l'est pas, c'est
qu'elle derive en silence. Ces tests transforment une duplication subie en
duplication verifiee.

Le champ `license` merite une attention particuliere : c'est **lui** que Blender
lit pour declarer la licence de l'extension, pas le `/LICENSE` du depot. Les
voir diverger est exactement le defaut releve chez un autre addon 3DGS diffuse,
qui annonce trois licences contradictoires selon l'endroit ou on regarde.
"""

import tomllib
from pathlib import Path

from gamb_engine import naming

RACINE_DEPOT = Path(__file__).resolve().parents[2]
CHEMIN_MANIFESTE = (
    RACINE_DEPOT / "addon" / naming.EXTENSION_ID / "blender_manifest.toml"
)


def _manifeste() -> dict:
    return tomllib.loads(CHEMIN_MANIFESTE.read_text(encoding="utf-8"))


def test_le_manifeste_est_a_lemplacement_attendu():
    assert CHEMIN_MANIFESTE.is_file(), (
        f"manifeste absent de {CHEMIN_MANIFESTE} — le dossier de l'addon doit porter "
        f"l'id de l'extension ({naming.EXTENSION_ID})"
    )


def test_id_et_nom_suivent_la_table_de_nommage():
    manifeste = _manifeste()
    assert manifeste["id"] == naming.EXTENSION_ID
    assert manifeste["name"] == naming.EXTENSION_NAME


def test_licence_declaree_gpl3():
    """C'est ce champ que Blender lit, pas le /LICENSE du depot."""
    assert _manifeste()["license"] == ["SPDX:GPL-3.0-or-later"]


def test_plancher_de_version_blender():
    """5.0 embarque Python 3.11 et non 3.13 : le plancher ne doit pas descendre."""
    minimum = _manifeste()["blender_version_min"]
    majeur, mineur = (int(n) for n in minimum.split(".")[:2])
    assert (majeur, mineur) >= (5, 1), f"plancher trop bas : {minimum}"


def test_tagline_respecte_les_regles_de_blender():
    """64 caracteres maximum, et pas de ponctuation finale."""
    tagline = _manifeste()["tagline"]
    assert len(tagline) <= 64, f"{len(tagline)} caracteres"
    assert tagline[-1] not in ".!?,;:"


def test_le_type_est_bien_un_addon():
    assert _manifeste()["type"] == "add-on"
