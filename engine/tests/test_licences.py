# SPDX-License-Identifier: Apache-2.0
"""Toute dependance verrouillee doit avoir sa ligne dans LICENSES.md.

Le risque n°3 de la spec — « LICENSES.md a jour, en continu » — est une bonne
intention tant qu'il repose sur la vigilance de quelqu'un. Ce test le rend
mecanique : une dependance ajoutee sans sa ligne de licence casse le build.

Il ne s'agit pas d'un scrupule theorique. Quand P1 a introduit FastAPI et
uvicorn, le resolveur a epingle 24 paquets tiers, dont **18 n'etaient
documentes nulle part** — des transitives que personne n'a choisies mais que
l'on distribue quand meme. C'est ce controle qui les a trouvees.

Ce que le test verifie : la presence d'une ligne. Pas son exactitude — ca,
seule une lecture a la source primaire le donne, et c'est un travail humain.
"""

import re
import tomllib
from pathlib import Path

RACINE_DEPOT = Path(__file__).resolve().parents[2]
CHEMIN_LOCK = RACINE_DEPOT / "engine" / "uv.lock"
CHEMIN_LICENCES = RACINE_DEPOT / "LICENSES.md"

# Le projet lui-meme n'est pas une dependance tierce.
IGNORES = {"gamb-engine"}


def _normaliser(nom: str) -> str:
    """PyPI considere `-`, `_` et `.` equivalents, et la casse non signifiante."""
    return re.sub(r"[-_.]+", "-", nom).lower()


def _paquets_verrouilles() -> set[str]:
    contenu = tomllib.loads(CHEMIN_LOCK.read_text(encoding="utf-8"))
    return {p["name"] for p in contenu.get("package", [])} - IGNORES


def test_le_lockfile_est_versionne():
    """Sans lui, personne ne peut reproduire l'environnement — ni auditer ce qu'il contient."""
    assert CHEMIN_LOCK.is_file(), (
        f"{CHEMIN_LOCK} absent. Lance `uv lock --project engine` et versionne le resultat."
    )


def test_chaque_dependance_verrouillee_est_documentee():
    licences = _normaliser(CHEMIN_LICENCES.read_text(encoding="utf-8"))

    absents = sorted(
        paquet for paquet in _paquets_verrouilles() if _normaliser(paquet) not in licences
    )

    assert not absents, (
        f"{len(absents)} dependance(s) verrouillee(s) sans ligne dans LICENSES.md : "
        f"{', '.join(absents)}.\n"
        "Lis leur licence a la source primaire — le fichier LICENSE du depot, le champ "
        "License de PyPI pour la version exacte epinglee — puis ajoute la ligne. "
        "Une ligne « A VERIFIER » est acceptable ; une ligne devinee ne l'est pas."
    )
