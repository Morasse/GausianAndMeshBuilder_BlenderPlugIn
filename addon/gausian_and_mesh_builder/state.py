# SPDX-License-Identifier: GPL-3.0-or-later
"""Miroir de l'etat du moteur, cote addon.

**Ce module n'importe pas bpy.** L'etat vit ici plutot que dans un
PropertyGroup pour une raison precise : il est ecrit par un timer, pas par
l'utilisateur. Le passer par les proprietes Blender obligerait a ecrire dans
les donnees depuis un contexte de timer, ce qui est exactement le genre de
chose qui marque la scene comme modifiee sans que personne n'ait rien touche.

Le panneau lit cet objet ; le timer l'ecrit. C'est un miroir en lecture seule
de ce que dit le sidecar, jamais une source de verite.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

HORS_LIGNE = "hors ligne"
EN_LIGNE = "online"
DEMARRAGE = "demarrage"


@dataclass
class EtatMoteur:
    """Derniere reponse connue du moteur."""

    statut: str = HORS_LIGNE
    charge: dict[str, Any] | None = None
    detail: str | None = None
    journal: str | None = None
    demarrage_demande: bool = False
    tentatives: int = field(default=0)

    @property
    def en_ligne(self) -> bool:
        return self.charge is not None

    def hors_ligne(self, detail: str | None = None) -> None:
        self.statut = DEMARRAGE if self.demarrage_demande else HORS_LIGNE
        self.charge = None
        self.detail = detail

    def en_ligne_avec(self, charge: dict[str, Any]) -> None:
        self.statut = str(charge.get("statut", EN_LIGNE))
        self.charge = charge
        self.detail = None
        self.demarrage_demande = False
        self.tentatives = 0


# Instance unique lue par le panneau et ecrite par le timer.
etat = EtatMoteur()
