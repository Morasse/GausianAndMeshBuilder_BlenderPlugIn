# SPDX-License-Identifier: Apache-2.0
"""Gardes sur le manifeste de projet.

Le test qui compte le plus est `test_une_decision_figee_ne_se_change_pas` : un
projet dont la moitié des images est en linéaire et l'autre en sRGB ne se
détecte qu'au moment où l'entraînement produit des couleurs fausses, très loin
de la cause. Le manifeste doit refuser bruyamment plutôt que de laisser faire.
"""

import json

import pytest

from gamb_engine import project


def test_creer_ecrit_un_manifeste_et_les_sous_dossiers(tmp_path):
    projet = project.creer(tmp_path / "scan")

    assert projet.manifeste.is_file()
    for sous_dossier in project.SOUS_DOSSIERS:
        assert (projet.racine / sous_dossier).is_dir()


def test_le_manifeste_porte_les_trois_champs_qui_coutent_cher_plus_tard(tmp_path):
    projet = project.creer(tmp_path / "scan")
    donnees = json.loads(projet.manifeste.read_text(encoding="utf-8"))

    assert donnees["format_version"] == project.FORMAT_VERSION
    assert donnees["espace_colorimetrique"] in project.ESPACES_COLORIMETRIQUES
    assert donnees["axes"] in project.AXES
    assert donnees["unites"] in project.UNITES


def test_aller_retour(tmp_path):
    project.creer(tmp_path / "scan", espace_colorimetrique="lineaire", axes="y_up_droite")
    recharge = project.charger(tmp_path / "scan")

    assert recharge.espace_colorimetrique == "lineaire"
    assert recharge.axes == "y_up_droite"
    assert recharge.nom == "scan"


def test_charger_accepte_le_chemin_du_manifeste(tmp_path):
    projet = project.creer(tmp_path / "scan")
    assert project.charger(projet.manifeste).nom == "scan"


def test_une_decision_figee_ne_se_change_pas(tmp_path):
    projet = project.creer(tmp_path / "scan", espace_colorimetrique="sRGB")

    with pytest.raises(project.DecisionFigee):
        projet.figer(espace_colorimetrique="lineaire")


def test_refiger_la_meme_valeur_est_sans_effet(tmp_path):
    projet = project.creer(tmp_path / "scan", espace_colorimetrique="sRGB")
    projet.figer(espace_colorimetrique="sRGB", axes="z_up_droite", unites="metre")


def test_une_valeur_hors_liste_est_refusee(tmp_path):
    with pytest.raises(ValueError):
        project.creer(tmp_path / "scan", espace_colorimetrique="ProPhoto")

    with pytest.raises(ValueError):
        project.creer(tmp_path / "autre", axes="y_up_gauche_inverse")


def test_un_format_futur_est_refuse_plutot_qu_ouvert_de_force(tmp_path):
    projet = project.creer(tmp_path / "scan")
    donnees = json.loads(projet.manifeste.read_text(encoding="utf-8"))
    donnees["format_version"] = project.FORMAT_VERSION + 1
    projet.manifeste.write_text(json.dumps(donnees), encoding="utf-8")

    with pytest.raises(project.FormatIncompatible):
        project.charger(tmp_path / "scan")


def test_un_manifeste_sans_version_est_refuse(tmp_path):
    racine = tmp_path / "scan"
    racine.mkdir()
    (racine / project.NOM_MANIFESTE).write_text('{"nom": "x"}', encoding="utf-8")

    with pytest.raises(project.FormatIncompatible):
        project.charger(racine)


def test_projet_absent(tmp_path):
    with pytest.raises(project.ProjetIntrouvable):
        project.charger(tmp_path / "nulle_part")


def test_le_journal_garde_la_trace_de_la_creation(tmp_path):
    projet = project.creer(tmp_path / "scan")
    assert any(entree["action"] == "creation" for entree in projet.historique)
    assert all("date" in entree for entree in projet.historique)


def test_le_defaut_est_la_convention_de_blender(tmp_path):
    """L'hôte est Blender : son repère est le repère interne, les autres sont des exports."""
    projet = project.creer(tmp_path / "scan")
    assert projet.axes == "z_up_droite"
    assert projet.unites == "metre"
