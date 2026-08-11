# SPDX-License-Identifier: Apache-2.0
"""Gardes sur la decouverte de l'interpreteur.

Le test qui compte le plus ici est `test_le_stub_du_store_est_exclu` : le stub
Python du Microsoft Store **ouvre le Store** quand on l'execute. Il doit donc
etre ecarte sur son chemin, avant toute execution. Un jour ou quelqu'un
« optimisera » la decouverte en sondant d'abord et filtrant ensuite, ce test
est ce qui l'arretera.
"""

from pathlib import Path

from gamb_engine import bootstrap
from gamb_engine.bootstrap import Interpreteur


def _interpreteur(version, rejet=None, chemin="/faux/python"):
    return Interpreteur(Path(chemin), version, 64, "test", rejet)


def test_le_stub_du_store_est_exclu_sans_etre_execute():
    chemin = Path("C:/Users/x/AppData/Local/Microsoft/WindowsApps/python.exe")
    raison = bootstrap.raison_exclusion(chemin)
    assert raison is not None
    assert "Store" in raison


def test_le_python_de_blender_est_exclu():
    chemin = Path("C:/Program Files/Blender Foundation/Blender 5.2/5.2/python/bin/python.exe")
    raison = bootstrap.raison_exclusion(chemin)
    assert raison is not None
    assert "Blender" in raison


def test_un_python_ordinaire_nest_pas_exclu():
    assert bootstrap.raison_exclusion(Path("C:/Python312/python.exe")) is None


def test_la_fenetre_de_versions_exclut_le_python_de_blender():
    """3.13 est la version de Blender : elle ne doit jamais servir au sidecar."""
    assert bootstrap.VERSION_MAX_EXCLUE == (3, 13)
    assert bootstrap.VERSION_MIN == (3, 11)


def test_selectionner_prend_la_version_la_plus_recente_utilisable():
    candidats = [
        _interpreteur((3, 11, 14)),
        _interpreteur((3, 12, 11)),
        _interpreteur((3, 13, 7), rejet="trop recent"),
    ]
    choisi = bootstrap.selectionner(candidats)
    assert choisi is not None
    assert choisi.version == (3, 12, 11)


def test_selectionner_ne_renvoie_rien_si_tout_est_rejete():
    candidats = [_interpreteur((3, 13, 7), rejet="trop recent")]
    assert bootstrap.selectionner(candidats) is None


def test_le_rapport_dit_quoi_installer_quand_rien_ne_convient():
    rapport = bootstrap.rapport([_interpreteur((3, 10, 0), rejet="trop ancien")])
    assert "uv python install" in rapport


def test_le_rapport_dit_de_ne_rien_installer_quand_un_python_convient():
    rapport = bootstrap.rapport([_interpreteur((3, 12, 11))])
    assert "Rien a installer" in rapport
    assert "uv python install" not in rapport


def test_la_decouverte_reelle_nexplose_pas():
    """Sur n'importe quelle machine, y compris un runner CI sans Python installe."""
    candidats = bootstrap.decouvrir()
    assert isinstance(candidats, list)
    for candidat in candidats:
        assert isinstance(candidat, Interpreteur)
