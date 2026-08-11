# SPDX-License-Identifier: Apache-2.0
"""Decouverte de l'interpreteur Python du sidecar.

Regle du module, dans cet ordre et jamais l'inverse :

    1. decouvrir  -- uv, registre PEP 514, lanceur py, PATH, emplacements connus
    2. valider    -- version, architecture, module venv reellement utilisable
    3. annoncer   -- ce qui a ete trouve et ce qui va se passer
    4. provisionner -- seulement si rien ne convient

La raison d'etre de ce module tient dans un fait mesure : sur la machine de
developpement, les Python 3.11 et 3.12 etaient installes et geres par uv, donc
totalement invisibles du PATH, du registre Windows *et* de `py --list-paths`.
Trois inventaires, trois reponses differentes. Un installateur qui n'en
interroge qu'un conclut « il faut installer » et pose un doublon a l'utilisateur.
"""

from __future__ import annotations

import os
import re
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path

from gamb_engine.proc import executer

# Fenetre de versions du sidecar. Borne haute exclue : 3.13 est le Python de
# Blender, et les wheels CUDA pour cp313 sur Windows sont inegales.
VERSION_MIN = (3, 11)
VERSION_MAX_EXCLUE = (3, 13)

_SCRIPT_SONDE = (
    "import struct,sys;"
    "print(sys.version_info[0],sys.version_info[1],sys.version_info[2],struct.calcsize('P')*8)"
)


@dataclass(frozen=True)
class Interpreteur:
    """Un candidat interpreteur, retenu ou rejete, avec la raison."""

    chemin: Path
    version: tuple[int, int, int]
    bits: int
    origine: str
    rejet: str | None = None

    @property
    def convient(self) -> bool:
        return self.rejet is None

    @property
    def version_str(self) -> str:
        return ".".join(str(n) for n in self.version)

    def __str__(self) -> str:
        etat = "ok" if self.convient else f"rejete — {self.rejet}"
        entete = f"Python {self.version_str} ({self.bits} bits, {self.origine})"
        return f"{entete} [{etat}] {self.chemin}"


# --- Exclusions dures --------------------------------------------------------
#
# Ces deux familles sont ecartees *avant* toute execution, et l'ordre compte :
# executer un stub du Microsoft Store ouvre le Store a l'utilisateur.


def raison_exclusion(chemin: Path) -> str | None:
    """Renvoie la raison d'ecarter ce chemin sans meme le lancer, ou None."""
    parties = [p.lower() for p in chemin.parts]

    if "windowsapps" in parties:
        return "stub du Microsoft Store (ouvre le Store au lieu de lancer Python)"

    if any("blender" in p for p in parties):
        return "Python embarque de Blender (le sidecar doit vivre hors du processus Blender)"

    return None


# --- Etape 1 : decouvrir -----------------------------------------------------


def _candidats_uv() -> list[tuple[Path, str]]:
    """uv est interroge en premier : c'est lui qui voit ce que les autres ratent."""
    trouves: list[tuple[Path, str]] = []

    uv = shutil.which("uv")
    if uv:
        borne_basse = f"{VERSION_MIN[0]}.{VERSION_MIN[1]}"
        borne_haute = f"{VERSION_MAX_EXCLUE[0]}.{VERSION_MAX_EXCLUE[1]}"
        sortie = executer([uv, "python", "find", f">={borne_basse},<{borne_haute}"])
        if sortie:
            trouves.append((Path(sortie), "uv"))

    # Repli : uv absent du PATH, ou une version trop ancienne pour `python find`.
    racine = Path(os.environ.get("APPDATA", "")) / "uv" / "python"
    if racine.is_dir():
        for dossier in racine.glob("cpython-*"):
            for nom in ("python.exe", "bin/python3", "bin/python"):
                executable = dossier / nom
                if executable.is_file():
                    trouves.append((executable, "uv"))
                    break

    return trouves


def _candidats_registre() -> list[tuple[Path, str]]:
    """Registre PEP 514. Ne voit que les installeurs officiels, pas uv."""
    if sys.platform != "win32":
        return []

    # Importe ici et pas en tete : winreg n'existe pas sous Linux, ou tourne le CI.
    import winreg

    trouves: list[tuple[Path, str]] = []
    for ruche, chemin_cle in (
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Python\PythonCore"),
        (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Python\PythonCore"),
    ):
        try:
            with winreg.OpenKey(ruche, chemin_cle) as cle:
                index = 0
                while True:
                    try:
                        version = winreg.EnumKey(cle, index)
                    except OSError:
                        break
                    index += 1
                    try:
                        with winreg.OpenKey(cle, rf"{version}\InstallPath") as cle_chemin:
                            base = winreg.QueryValue(cle_chemin, None)
                    except OSError:
                        continue
                    executable = Path(base) / "python.exe"
                    if executable.is_file():
                        trouves.append((executable, "registre"))
        except OSError:
            continue
    return trouves


def _candidats_lanceur_py() -> list[tuple[Path, str]]:
    if sys.platform != "win32" or not shutil.which("py"):
        return []
    sortie = executer(["py", "--list-paths"])
    if not sortie:
        return []
    trouves: list[tuple[Path, str]] = []
    for ligne in sortie.splitlines():
        correspondance = re.search(r"(\S+python(?:\.exe)?)\s*$", ligne.strip())
        if correspondance:
            executable = Path(correspondance.group(1))
            if executable.is_file():
                trouves.append((executable, "lanceur py"))
    return trouves


def _candidats_path() -> list[tuple[Path, str]]:
    trouves: list[tuple[Path, str]] = []
    for nom in ("python3.12", "python3.11", "python3", "python"):
        chemin = shutil.which(nom)
        if chemin:
            trouves.append((Path(chemin), "PATH"))
    return trouves


def _candidats_emplacements_connus() -> list[tuple[Path, str]]:
    motifs = [
        Path("C:/Program Files") / "Python*",
        Path("C:/") / "Python*",
        Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Python" / "*",
    ]
    trouves: list[tuple[Path, str]] = []
    for motif in motifs:
        parent, nom = motif.parent, motif.name
        if not parent.is_dir():
            continue
        for dossier in parent.glob(nom):
            executable = dossier / "python.exe"
            if executable.is_file():
                trouves.append((executable, "emplacement connu"))
    return trouves


def decouvrir() -> list[Interpreteur]:
    """Inventorie tous les candidats, retenus comme rejetes, sans doublon."""
    bruts: list[tuple[Path, str]] = []
    for source in (
        _candidats_uv,
        _candidats_registre,
        _candidats_lanceur_py,
        _candidats_path,
        _candidats_emplacements_connus,
    ):
        bruts.extend(source())

    vus: set[str] = set()
    resultats: list[Interpreteur] = []

    for chemin, origine in bruts:
        try:
            resolu = chemin.resolve()
        except OSError:
            continue
        cle = str(resolu).lower()
        if cle in vus:
            continue
        vus.add(cle)

        exclusion = raison_exclusion(resolu)
        if exclusion is not None:
            # Jamais execute : c'est tout l'interet de filtrer sur le chemin.
            resultats.append(Interpreteur(resolu, (0, 0, 0), 0, origine, exclusion))
            continue

        sonde = executer([str(resolu), "-c", _SCRIPT_SONDE])
        if not sonde:
            resultats.append(Interpreteur(resolu, (0, 0, 0), 0, origine, "ne repond pas"))
            continue

        try:
            majeur, mineur, correctif, bits = (int(n) for n in sonde.split())
        except ValueError:
            resultats.append(Interpreteur(resolu, (0, 0, 0), 0, origine, "sonde illisible"))
            continue

        version = (majeur, mineur, correctif)
        resultats.append(
            Interpreteur(resolu, version, bits, origine, _raison_invalidite(version, bits, resolu))
        )

    return resultats


# --- Etape 2 : valider -------------------------------------------------------


def _raison_invalidite(version: tuple[int, int, int], bits: int, chemin: Path) -> str | None:
    if version[:2] < VERSION_MIN:
        return f"trop ancien (< {VERSION_MIN[0]}.{VERSION_MIN[1]})"
    if version[:2] >= VERSION_MAX_EXCLUE:
        return f"trop recent (>= {VERSION_MAX_EXCLUE[0]}.{VERSION_MAX_EXCLUE[1]})"
    if bits != 64:
        return f"{bits} bits, il en faut 64"
    if executer([str(chemin), "-c", "import venv"]) is None:
        return "module venv indisponible"
    return None


def selectionner(candidats: list[Interpreteur] | None = None) -> Interpreteur | None:
    """Le meilleur interpreteur utilisable, ou None s'il faut en provisionner un.

    A egalite de validite, la version la plus recente de la fenetre gagne.
    """
    if candidats is None:
        candidats = decouvrir()
    retenus = [c for c in candidats if c.convient]
    if not retenus:
        return None
    return max(retenus, key=lambda c: c.version)


# --- Etape 3 : annoncer ------------------------------------------------------


def rapport(candidats: list[Interpreteur] | None = None) -> str:
    """Rapport lisible : ce qui a ete trouve, ce qui a ete ecarte et pourquoi."""
    if candidats is None:
        candidats = decouvrir()

    lignes = [
        f"Fenetre requise : >={VERSION_MIN[0]}.{VERSION_MIN[1]}, "
        f"<{VERSION_MAX_EXCLUE[0]}.{VERSION_MAX_EXCLUE[1]}",
        "",
    ]

    retenus = [c for c in candidats if c.convient]
    ecartes = [c for c in candidats if not c.convient]

    lignes.append(f"Interpreteurs utilisables ({len(retenus)}) :")
    lignes.extend(f"  {c}" for c in retenus)
    if not retenus:
        lignes.append("  aucun")

    lignes.append("")
    lignes.append(f"Ecartes ({len(ecartes)}) :")
    lignes.extend(f"  {c}" for c in ecartes)
    if not ecartes:
        lignes.append("  aucun")

    lignes.append("")
    choisi = selectionner(candidats)
    if choisi is None:
        lignes.append("Aucun interpreteur ne convient. A provisionner :")
        lignes.append(f"    uv python install {VERSION_MIN[0]}.{VERSION_MIN[1]}")
    else:
        lignes.append(f"Retenu : {choisi.chemin}  (Python {choisi.version_str}, {choisi.origine})")
        lignes.append("Rien a installer.")

    return "\n".join(lignes)
