# SPDX-License-Identifier: Apache-2.0
"""Gardes sur les fiches d'options — §14.

Le test qui rend la règle tenable est
`test_tout_parametre_de_preset_a_sa_fiche` : sans lui, la §14 se dégrade en
silence. On ajoute un réglage, on oublie sa fiche, et six mois plus tard
personne ne sait plus ce que fait la moitié des curseurs — ce que le document
de référence résume par « la §14 ne se rattrape jamais ».
"""

import pytest
from fastapi.testclient import TestClient

from gamb_engine import options, server


def test_les_fiches_se_chargent():
    toutes = options.fiches()
    assert toutes, "aucune fiche chargée"
    assert "cap_max" in toutes


def test_chaque_fiche_repond_aux_quatre_questions():
    """Un tooltip d'une ligne ne dit jamais quand monter ni ce que ça coûte."""
    for cle, fiche in options.fiches().items():
        for champ in ("libelle", "effet", "monter_quand", "baisser_quand", "cout"):
            valeur = getattr(fiche, champ)
            assert valeur and str(valeur).strip(), f"{cle}.{champ} est vide"


def test_tout_parametre_de_preset_a_sa_fiche():
    options.verifier_coherence()


def test_les_trois_presets_existent():
    noms = set(options.presets())
    assert {"apercu", "production", "temps_reel"} <= noms


def test_le_preset_production_suit_le_simple_trainer():
    """C'est la référence du critère d'acceptation : il ne doit pas dériver."""
    parametres = options.preset("production").parametres
    assert parametres["iterations"] == 30000
    assert parametres["degre_sh"] == 3
    assert parametres["poids_ssim"] == 0.2
    assert parametres["resolution"] == 1


def test_le_preset_temps_reel_plafonne_ce_qui_coute_a_l_execution():
    parametres = options.preset("temps_reel").parametres
    production = options.preset("production").parametres
    assert parametres["cap_max"] < production["cap_max"]
    assert parametres["degre_sh"] < production["degre_sh"]


def test_resoudre_renvoie_la_configuration_complete():
    """Un run porte sa config entière, jamais un diff — sinon l'A/B ment."""
    valeurs = options.resoudre("apercu")
    assert set(valeurs) == set(options.fiches())


def test_l_ordre_de_precedence(monkeypatch):
    valeurs = options.resoudre("apercu", iterations=42)
    assert valeurs["iterations"] == 42  # la surcharge gagne
    assert valeurs["cap_max"] == options.preset("apercu").parametres["cap_max"]


def test_une_surcharge_nulle_ne_masque_pas_le_preset():
    """La CLI passe None pour les options non fournies."""
    valeurs = options.resoudre("apercu", iterations=None)
    assert valeurs["iterations"] == options.preset("apercu").parametres["iterations"]


def test_un_parametre_sans_fiche_est_refuse():
    with pytest.raises(options.OptionInconnue, match="règle §14"):
        options.resoudre("production", parametre_invente=3)


def test_un_preset_inconnu_liste_les_disponibles():
    with pytest.raises(options.PresetIntrouvable, match="production"):
        options.preset("nexiste_pas")


def test_la_route_options_sert_fiches_et_presets():
    with TestClient(server.creer_application()) as client:
        reponse = client.get("/options")

    assert reponse.status_code == 200
    charge = reponse.json()
    assert len(charge["fiches"]) == len(options.fiches())
    assert {p["nom"] for p in charge["presets"]} >= {"production", "temps_reel"}
    premiere = charge["fiches"][0]
    assert {"cle", "libelle", "effet", "monter_quand", "baisser_quand", "cout"} <= set(premiere)
