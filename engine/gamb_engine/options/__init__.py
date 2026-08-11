# SPDX-License-Identifier: Apache-2.0
"""Fiches d'options et presets — §14.

Deux règles, et la seconde est mécanique :

1. **Aucun libellé ni tooltip en dur dans le code de l'addon.** Tout vient des
   fiches YAML, servies au panneau Blender par le sidecar. Un artiste qui
   demande « à quoi sert ce curseur » doit trouver la réponse dans l'interface,
   pas dans le dépôt.

2. **Tout paramètre d'un preset doit avoir sa fiche.** Vérifié par
   `verifier_coherence()`, appelé par un test. Sans ça, la §14 se dégrade
   silencieusement : on ajoute un paramètre, on oublie sa fiche, et six mois
   plus tard personne ne sait plus ce que fait la moitié des réglages.

Les valeurs par défaut vivent dans les fiches, pas dans le code : une valeur
par défaut est une décision de produit, pas une constante d'implémentation.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

DOSSIER = Path(__file__).resolve().parent
FICHES = DOSSIER / "fiches"
PRESETS = DOSSIER / "presets"

CHAMPS_FICHE = ("libelle", "effet", "monter_quand", "baisser_quand", "cout", "defaut")


class OptionInconnue(Exception):
    """Un preset référence un paramètre qui n'a pas de fiche."""


class PresetIntrouvable(Exception):
    """Aucun preset de ce nom."""


@dataclass(frozen=True)
class Fiche:
    """Ce qu'un utilisateur doit savoir avant de toucher à un réglage."""

    cle: str
    libelle: str
    effet: str
    monter_quand: str
    baisser_quand: str
    cout: str
    defaut: Any

    def en_dictionnaire(self) -> dict[str, Any]:
        return {
            "cle": self.cle,
            "libelle": self.libelle,
            "effet": self.effet.strip(),
            "monter_quand": self.monter_quand,
            "baisser_quand": self.baisser_quand,
            "cout": self.cout,
            "defaut": self.defaut,
        }


@dataclass(frozen=True)
class Preset:
    nom: str
    description: str
    parametres: dict[str, Any]


def _charger_yaml(chemin: Path) -> dict[str, Any]:
    return yaml.safe_load(chemin.read_text(encoding="utf-8")) or {}


@lru_cache(maxsize=1)
def fiches() -> dict[str, Fiche]:
    """Toutes les fiches, indexées par clé de paramètre."""
    trouvees: dict[str, Fiche] = {}
    for chemin in sorted(FICHES.glob("*.yaml")):
        for cle, contenu in _charger_yaml(chemin).items():
            manquants = [champ for champ in CHAMPS_FICHE if champ not in contenu]
            if manquants:
                raise OptionInconnue(
                    f"la fiche {cle!r} de {chemin.name} n'a pas : {', '.join(manquants)}"
                )
            trouvees[cle] = Fiche(cle=cle, **{champ: contenu[champ] for champ in CHAMPS_FICHE})
    return trouvees


@lru_cache(maxsize=1)
def presets() -> dict[str, Preset]:
    trouves: dict[str, Preset] = {}
    for chemin in sorted(PRESETS.glob("*.yaml")):
        contenu = _charger_yaml(chemin)
        nom = contenu.get("nom", chemin.stem)
        trouves[nom] = Preset(
            nom=nom,
            description=str(contenu.get("description", "")).strip(),
            parametres=dict(contenu.get("parametres", {})),
        )
    return trouves


def preset(nom: str) -> Preset:
    disponibles = presets()
    if nom not in disponibles:
        raise PresetIntrouvable(f"preset {nom!r} inconnu ; disponibles : {', '.join(disponibles)}")
    return disponibles[nom]


def valeurs_par_defaut() -> dict[str, Any]:
    """Les défauts, tels que déclarés dans les fiches."""
    return {cle: fiche.defaut for cle, fiche in fiches().items()}


def resoudre(nom_preset: str | None = None, **surcharges: Any) -> dict[str, Any]:
    """Défauts des fiches, puis preset, puis surcharges explicites.

    Renvoie toujours l'ensemble complet des paramètres — un run doit porter sa
    configuration **complète**, pas un diff, sinon les comparaisons A/B mentent.
    """
    valeurs = valeurs_par_defaut()
    if nom_preset:
        valeurs.update(preset(nom_preset).parametres)

    inconnues = set(surcharges) - set(fiches())
    if inconnues:
        raise OptionInconnue(
            f"paramètre(s) sans fiche : {', '.join(sorted(inconnues))}. "
            "Écris la fiche avant d'exposer le réglage — c'est la règle §14."
        )
    valeurs.update({cle: valeur for cle, valeur in surcharges.items() if valeur is not None})
    return valeurs


def verifier_coherence() -> None:
    """Tout paramètre de preset a-t-il sa fiche ? Appelé par un test."""
    connues = set(fiches())
    for nom, contenu in presets().items():
        orphelins = set(contenu.parametres) - connues
        if orphelins:
            raise OptionInconnue(
                f"le preset {nom!r} référence des paramètres sans fiche : "
                f"{', '.join(sorted(orphelins))}"
            )
