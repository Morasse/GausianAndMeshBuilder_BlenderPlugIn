# SPDX-License-Identifier: Apache-2.0
"""Tout le code source doit être suivi par git.

Ce test existe à cause d'un bug réel. Le `.gitignore` ignore `**/poses/` pour
écarter les données de projet — motif récursif, qui a donc aussi attrapé
`engine/gamb_engine/poses/`, un paquet du moteur. Git l'a ignoré **sans un
mot** : `git add -A` l'a sauté, le commit est passé, le CI est resté vert, et
seul le prochain clone aurait été cassé.

Un fichier source ignoré ne provoque aucune erreur là où il est écrit. C'est
exactement le genre de panne qui se paie loin de sa cause, et la seule défense
est de demander à git lui-même ce qu'il voit.

Les collisions connues avec la spec : `poses/`, `mesh/`, `light/`.
"""

import subprocess
from pathlib import Path

import pytest

RACINE_DEPOT = Path(__file__).resolve().parents[2]
ARBRES_DE_CODE = ("engine/gamb_engine", "addon", "scripts")


def _git(*arguments: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-C", str(RACINE_DEPOT), *arguments],
        capture_output=True,
        text=True,
        check=False,
    )


def _depot_disponible() -> bool:
    return _git("rev-parse", "--git-dir").returncode == 0


def test_aucun_fichier_source_n_est_ignore():
    if not _depot_disponible():
        pytest.skip("hors dépôt git")

    sources = []
    for arbre in ARBRES_DE_CODE:
        dossier = RACINE_DEPOT / arbre
        if dossier.is_dir():
            sources.extend(
                chemin
                for chemin in dossier.rglob("*.py")
                if "__pycache__" not in chemin.parts
            )

    assert sources, "aucun fichier source trouvé — le test ne vérifie rien"

    relatifs = [str(c.relative_to(RACINE_DEPOT)).replace("\\", "/") for c in sources]

    # `check-ignore` liste ceux que git écarterait. On veut une liste vide.
    resultat = _git("check-ignore", "--no-index", *relatifs)
    ignores = [ligne for ligne in resultat.stdout.splitlines() if ligne.strip()]

    assert not ignores, (
        "des fichiers source sont ignorés par .gitignore :\n  "
        + "\n  ".join(ignores)
        + "\n\nAjoute une exception `!chemin/` dans .gitignore. Sans ça, ils ne "
        "seront jamais poussés et le prochain clone sera cassé."
    )


def test_chaque_dossier_du_moteur_est_un_vrai_paquet():
    """Un dossier sans `__init__.py` devient un paquet-espace-de-noms implicite.

    Ça marche en développement — l'arborescence est sur le disque — et casse une
    fois installé en wheel, parce que le backend de build ne l'inclut pas. La
    panne arrive donc au plus mauvais moment : chez l'utilisateur.
    """
    moteur = RACINE_DEPOT / "engine" / "gamb_engine"
    sans_init = []

    for dossier in moteur.rglob("*"):
        if not dossier.is_dir() or "__pycache__" in dossier.parts:
            continue
        # Un dossier de données (fiches, presets) n'a pas à être un paquet.
        if not any(chemin.suffix == ".py" for chemin in dossier.iterdir()):
            continue
        if not (dossier / "__init__.py").is_file():
            sans_init.append(str(dossier.relative_to(RACINE_DEPOT)))

    assert not sans_init, (
        "dossiers Python sans __init__.py :\n  " + "\n  ".join(sans_init)
    )
