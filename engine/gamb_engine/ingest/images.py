# SPDX-License-Identifier: Apache-2.0
"""Ingestion d'images déjà développées.

**Aucune dépendance.** Lire deux en-têtes — PNG et JPEG — ne justifie pas une
wheel binaire de plusieurs mégaoctets qui embarque libjpeg-turbo, zlib, libtiff
et freetype, cette dernière exigeant en plus un crédit en documentation. Pillow
arrivera à la curation, quand il faudra vraiment décoder des pixels, et il aura
sa ligne dans LICENSES.md ce jour-là.

Une dimension illisible n'est pas une erreur : le fichier est ingéré quand
même, avec `dimensions = None`. Refuser un format exotique à l'entrée du
pipeline coûterait plus cher que de l'accepter sans le mesurer.
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass, field
from pathlib import Path

from gamb_engine.project import Projet

# Extensions acceptées. Les deux premières sont mesurables sans dépendance ;
# les autres passent, mais sans dimensions.
EXTENSIONS = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".webp", ".bmp"}

_SIGNATURE_PNG = b"\x89PNG\r\n\x1a\n"

# Marqueurs SOF du JPEG — ceux qui portent les dimensions. Les SOF4/8/12
# (0xC4, 0xC8, 0xCC) n'en sont pas : ce sont DHT, JPG et DAC.
_MARQUEURS_SOF = frozenset(
    {0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF}
)

# Marqueurs sans charge utile : ils ne sont pas suivis d'une longueur.
_MARQUEURS_SANS_CHARGE = frozenset({0x01, *range(0xD0, 0xDA)})


@dataclass
class Rapport:
    """Ce qui est entré, ce qui a été écarté, et ce qui mérite un avertissement."""

    destination: Path
    ingerees: list[Path] = field(default_factory=list)
    ignorees: list[Path] = field(default_factory=list)
    resolutions: dict[tuple[int, int], int] = field(default_factory=dict)
    illisibles: list[Path] = field(default_factory=list)

    @property
    def nombre(self) -> int:
        return len(self.ingerees)

    @property
    def resolutions_multiples(self) -> bool:
        return len(self.resolutions) > 1

    def resume(self) -> str:
        lignes = [f"{self.nombre} image(s) → {self.destination}"]
        for (largeur, hauteur), compte in sorted(
            self.resolutions.items(), key=lambda paire: -paire[1]
        ):
            lignes.append(f"  {largeur}x{hauteur} : {compte}")
        if self.illisibles:
            lignes.append(f"  dimensions non mesurées : {len(self.illisibles)}")
        if self.ignorees:
            lignes.append(f"  ignoré(s), extension non reconnue : {len(self.ignorees)}")
        if self.resolutions_multiples:
            lignes.append(
                "  ⚠ résolutions hétérogènes — la plupart des entraîneurs supposent "
                "une résolution unique par dataset"
            )
        return "\n".join(lignes)


# --- Mesure des dimensions, sans dépendance ----------------------------------


def _dimensions_png(donnees: bytes) -> tuple[int, int] | None:
    # Signature (8) + longueur (4) + "IHDR" (4), puis largeur et hauteur.
    if len(donnees) < 24 or donnees[12:16] != b"IHDR":
        return None
    return (
        int.from_bytes(donnees[16:20], "big"),
        int.from_bytes(donnees[20:24], "big"),
    )


def _dimensions_jpeg(fichier) -> tuple[int, int] | None:
    fichier.seek(2)  # après le SOI
    while True:
        octet = fichier.read(1)
        if not octet:
            return None
        if octet[0] != 0xFF:
            continue  # octet de bourrage entre segments

        # Une suite de 0xFF est légale ; le marqueur est le premier octet différent.
        code = 0xFF
        while code == 0xFF:
            suivant = fichier.read(1)
            if not suivant:
                return None
            code = suivant[0]

        if code in _MARQUEURS_SANS_CHARGE:
            continue

        if code in _MARQUEURS_SOF:
            fichier.read(3)  # longueur (2) + précision (1)
            hauteur = int.from_bytes(fichier.read(2), "big")
            largeur = int.from_bytes(fichier.read(2), "big")
            return (largeur, hauteur) if largeur and hauteur else None

        longueur = int.from_bytes(fichier.read(2), "big")
        if longueur < 2:
            return None
        fichier.seek(longueur - 2, 1)


def dimensions(chemin: Path) -> tuple[int, int] | None:
    """Largeur et hauteur, ou None si le format n'est pas mesurable ici."""
    try:
        with chemin.open("rb") as fichier:
            entete = fichier.read(24)
            if entete.startswith(_SIGNATURE_PNG):
                return _dimensions_png(entete)
            if entete[:2] == b"\xff\xd8":
                return _dimensions_jpeg(fichier)
    except OSError:
        return None
    return None


# --- Découverte et ingestion -------------------------------------------------


def trouver(dossier: Path) -> tuple[list[Path], list[Path]]:
    """Sépare les images des autres fichiers. Ordre déterministe."""
    retenus: list[Path] = []
    ecartes: list[Path] = []
    for chemin in sorted(p for p in dossier.iterdir() if p.is_file()):
        (retenus if chemin.suffix.lower() in EXTENSIONS else ecartes).append(chemin)
    return retenus, ecartes


def ingerer(source: Path | str, projet: Projet, copier: bool = True) -> Rapport:
    """Fait entrer un dossier d'images dans un projet.

    `copier=False` indexe les images là où elles sont, sans les dupliquer —
    utile quand le dossier est déjà à sa place, ou volumineux.
    """
    source = Path(source)
    if not source.is_dir():
        raise NotADirectoryError(f"{source} n'est pas un dossier")

    trouvees, ecartees = trouver(source)
    destination = projet.images
    if copier:
        destination.mkdir(parents=True, exist_ok=True)

    rapport = Rapport(destination=destination if copier else source, ignorees=ecartees)

    for chemin in trouvees:
        cible = destination / chemin.name if copier else chemin
        if copier and chemin.resolve() != cible.resolve():
            shutil.copy2(chemin, cible)

        taille = dimensions(cible)
        if taille is None:
            rapport.illisibles.append(cible)
        else:
            rapport.resolutions[taille] = rapport.resolutions.get(taille, 0) + 1
        rapport.ingerees.append(cible)

    projet.journaliser(
        "ingestion_images",
        source=str(source),
        copiees=copier,
        nombre=rapport.nombre,
        resolutions={f"{larg}x{haut}": n for (larg, haut), n in rapport.resolutions.items()},
        ignorees=len(ecartees),
    )
    projet.ecrire()
    return rapport
