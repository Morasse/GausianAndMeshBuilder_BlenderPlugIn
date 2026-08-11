# SPDX-License-Identifier: Apache-2.0
"""Le projet sur disque — la source de vérité du pipeline.

Le fichier `.blend` **n'est pas** la source de vérité, le dossier projet l'est.
C'est ce qui permet la reprise après crash, le traitement par lot sans Blender,
et des comparaisons A/B honnêtes.

Le manifeste porte trois champs qui coûtent une ligne aujourd'hui et un bug
silencieux plus tard :

- `format_version` — rend toute migration détectable et scriptable plutôt que
  découverte au moment où un ancien projet s'ouvre de travers.
- `espace_colorimetrique` — sans objet tant que l'entrée est du JPEG ou du PNG,
  qui sont en sRGB par construction. Mais le jour où le DNG revient, la décision
  « linéaire ou sRGB » doit être **écrite** et non supposée : mélanger les deux
  dans un même dataset est une cause de bug silencieux.
- `axes` et `unites` — Blender est Z-up main droite, Godot Y-up main droite,
  Unreal Z-up main gauche en centimètres. La transformation vit **à l'export**,
  jamais en interne, et elle ne peut être juste que si la convention d'origine
  est écrite quelque part.

Ces trois-là sont des **décisions figées** : les changer après coup invalide
tout ce que le projet contient déjà, donc le code refuse de le faire en
silence.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

FORMAT_VERSION = 1

NOM_MANIFESTE = "gamb.json"

# --- Valeurs admises pour les décisions figées -------------------------------

ESPACES_COLORIMETRIQUES = ("sRGB", "lineaire")

# Conventions d'axes, nommées par leur hôte pour éviter toute ambiguïté.
AXES = {
    "z_up_droite": "Z vers le haut, main droite (Blender, COLMAP)",
    "y_up_droite": "Y vers le haut, main droite (Godot, glTF)",
    "z_up_gauche": "Z vers le haut, main gauche (Unreal)",
}

UNITES = ("metre", "centimetre")

# Les champs qu'on ne change pas sans invalider ce qui existe déjà.
DECISIONS_FIGEES = ("espace_colorimetrique", "axes", "unites")

# Sous-dossiers créés à la création du projet. Les autres (`masks/`,
# `curation/`, `raw/`) sont créés par la phase qui les remplit — un dossier vide
# qui traîne fait croire qu'une étape a été tentée.
SOUS_DOSSIERS = ("images", "poses", "runs")


class DecisionFigee(Exception):
    """Tentative de changer une décision déjà écrite dans le manifeste."""


class ProjetIntrouvable(Exception):
    """Aucun manifeste à l'emplacement demandé."""


class FormatIncompatible(Exception):
    """Le manifeste vient d'une version du format que ce code ne sait pas lire."""


def _maintenant() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


@dataclass
class Projet:
    """Un dossier projet GAMB, et son manifeste."""

    racine: Path
    nom: str
    espace_colorimetrique: str = "sRGB"
    axes: str = "z_up_droite"
    unites: str = "metre"
    format_version: int = FORMAT_VERSION
    cree_le: str = field(default_factory=_maintenant)
    historique: list[dict[str, Any]] = field(default_factory=list)

    # --- chemins ------------------------------------------------------------

    @property
    def manifeste(self) -> Path:
        return self.racine / NOM_MANIFESTE

    @property
    def images(self) -> Path:
        return self.racine / "images"

    @property
    def poses(self) -> Path:
        return self.racine / "poses"

    @property
    def runs(self) -> Path:
        return self.racine / "runs"

    # --- journal ------------------------------------------------------------

    def journaliser(self, action: str, **details: Any) -> None:
        """Ajoute une entrée au journal. C'est la matière première d'une doc RS&DE."""
        self.historique.append({"date": _maintenant(), "action": action, **details})

    # --- sérialisation ------------------------------------------------------

    def en_dictionnaire(self) -> dict[str, Any]:
        return {
            "format_version": self.format_version,
            "nom": self.nom,
            "cree_le": self.cree_le,
            "espace_colorimetrique": self.espace_colorimetrique,
            "axes": self.axes,
            "unites": self.unites,
            "historique": self.historique,
        }

    def ecrire(self) -> Path:
        self.racine.mkdir(parents=True, exist_ok=True)
        contenu = json.dumps(self.en_dictionnaire(), indent=2, ensure_ascii=False)
        self.manifeste.write_text(contenu + "\n", encoding="utf-8")
        return self.manifeste

    # --- décisions figées ---------------------------------------------------

    def figer(self, **decisions: str) -> None:
        """Écrit une décision, ou refuse si elle contredit ce qui est déjà écrit.

        Refuser bruyamment est le seul comportement acceptable : un projet dont
        la moitié des images est en linéaire et l'autre en sRGB ne se détecte
        qu'au moment où l'entraînement produit des couleurs fausses, longtemps
        après la cause.
        """
        for champ, valeur in decisions.items():
            if champ not in DECISIONS_FIGEES:
                raise ValueError(f"{champ!r} n'est pas une décision figée")

            _valider(champ, valeur)
            actuelle = getattr(self, champ)

            if actuelle != valeur:
                raise DecisionFigee(
                    f"{champ} vaut déjà {actuelle!r} dans ce projet ; refus de le passer à "
                    f"{valeur!r}. Tout ce que le projet contient a été produit sous "
                    f"{actuelle!r} — crée un nouveau projet plutôt que de mélanger."
                )


def _valider(champ: str, valeur: str) -> None:
    admis = {
        "espace_colorimetrique": ESPACES_COLORIMETRIQUES,
        "axes": tuple(AXES),
        "unites": UNITES,
    }[champ]
    if valeur not in admis:
        raise ValueError(f"{champ} = {valeur!r} ; valeurs admises : {', '.join(admis)}")


# --- création et chargement --------------------------------------------------


def creer(
    racine: Path | str,
    nom: str | None = None,
    espace_colorimetrique: str = "sRGB",
    axes: str = "z_up_droite",
    unites: str = "metre",
) -> Projet:
    """Crée un dossier projet et son manifeste."""
    racine = Path(racine)
    for champ, valeur in (
        ("espace_colorimetrique", espace_colorimetrique),
        ("axes", axes),
        ("unites", unites),
    ):
        _valider(champ, valeur)

    projet = Projet(
        racine=racine,
        nom=nom or racine.name,
        espace_colorimetrique=espace_colorimetrique,
        axes=axes,
        unites=unites,
    )
    for sous_dossier in SOUS_DOSSIERS:
        (racine / sous_dossier).mkdir(parents=True, exist_ok=True)

    projet.journaliser("creation", format_version=FORMAT_VERSION)
    projet.ecrire()
    return projet


def charger(racine: Path | str) -> Projet:
    """Charge un projet existant.

    Accepte la racine du projet ou le chemin du manifeste lui-même.
    """
    chemin = Path(racine)
    manifeste = chemin if chemin.name == NOM_MANIFESTE else chemin / NOM_MANIFESTE

    if not manifeste.is_file():
        raise ProjetIntrouvable(f"aucun {NOM_MANIFESTE} dans {manifeste.parent}")

    donnees = json.loads(manifeste.read_text(encoding="utf-8"))
    version = donnees.get("format_version")

    if version is None:
        raise FormatIncompatible(f"{manifeste} n'a pas de format_version")
    if version > FORMAT_VERSION:
        raise FormatIncompatible(
            f"{manifeste} est en format_version {version}, ce moteur lit jusqu'à "
            f"{FORMAT_VERSION}. Mets GAMB à jour plutôt que d'ouvrir le projet de force."
        )

    return Projet(
        racine=manifeste.parent,
        nom=donnees.get("nom", manifeste.parent.name),
        espace_colorimetrique=donnees.get("espace_colorimetrique", "sRGB"),
        axes=donnees.get("axes", "z_up_droite"),
        unites=donnees.get("unites", "metre"),
        format_version=version,
        cree_le=donnees.get("cree_le", ""),
        historique=donnees.get("historique", []),
    )


def existe(racine: Path | str) -> bool:
    return (Path(racine) / NOM_MANIFESTE).is_file()
