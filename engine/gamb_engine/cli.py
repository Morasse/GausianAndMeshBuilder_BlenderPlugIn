# SPDX-License-Identifier: Apache-2.0
"""CLI du sidecar.

Regle permanente du projet : **tout ce que fait l'addon doit etre faisable
ici, sans Blender.** C'est ce qui rend le moteur testable, scriptable en batch,
et utilisable sur une machine sans interface graphique. Une capacite ajoutee au
moteur sans entree CLI est une capacite a moitie livree.

    gamb doctor    ce que la machine sait faire, et ce qui manque
    gamb serve     demarre le serveur
    gamb health    interroge un serveur deja demarre
    gamb ingest    fait entrer des images dans un projet
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

from gamb_engine import bootstrap, machine, naming, project
from gamb_engine.ingest import images as ingest_images
from gamb_engine.server import HOTE_DEFAUT, PORT_DEFAUT, VERSION


def _ajouter_options_adresse(analyseur: argparse.ArgumentParser) -> None:
    analyseur.add_argument("--hote", default=HOTE_DEFAUT, help=f"defaut : {HOTE_DEFAUT}")
    analyseur.add_argument("--port", type=int, default=PORT_DEFAUT, help=f"defaut : {PORT_DEFAUT}")


def commande_doctor(_: argparse.Namespace) -> int:
    """Inventaire de la machine. Ne modifie rien, n'installe rien."""
    print("=== Interpreteur Python ===")
    print(bootstrap.rapport())

    print()
    print("=== GPU ===")
    trouves = machine.gpus()
    if not trouves:
        print("  aucun GPU NVIDIA detecte (nvidia-smi absent ou muet)")
        print("  -> le moteur ne pourra pas entrainer")
    else:
        for gpu in trouves:
            print(f"  {gpu}  (driver {gpu.driver})")

    print()
    print("=== Chaine de compilation CUDA ===")
    chaine = machine.chaine_compilation()
    print(f"  nvcc : {chaine.nvcc or 'absent'}")
    if sys.platform == "win32":
        print(f"  MSVC : {chaine.msvc or 'absent'}")
    if chaine.complete:
        print("  -> gsplat pourra compiler ses kernels au besoin")
    else:
        print(f"  -> manquant : {', '.join(chaine.manquant)}")
        print("     gsplat echouera s'il doit compiler plutot qu'utiliser une wheel")

    return 0


def commande_serve(arguments: argparse.Namespace) -> int:
    from gamb_engine.server import servir

    print(f"{naming.ENGINE_DISTRIBUTION} {VERSION} -> http://{arguments.hote}:{arguments.port}")
    servir(arguments.hote, arguments.port)
    return 0


def commande_health(arguments: argparse.Namespace) -> int:
    url = f"http://{arguments.hote}:{arguments.port}/health"
    try:
        with urllib.request.urlopen(url, timeout=5) as reponse:
            charge = json.loads(reponse.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, OSError) as erreur:
        print(f"moteur injoignable sur {url} — {erreur}", file=sys.stderr)
        return 1

    print(json.dumps(charge, indent=2, ensure_ascii=False))
    return 0


def commande_ingest(arguments: argparse.Namespace) -> int:
    source = Path(arguments.source)

    if not arguments.sur_place and not arguments.projet:
        print("il faut --projet <racine>, ou --sur-place si la source est deja un projet",
              file=sys.stderr)
        return 1

    if arguments.sur_place:
        # La source EST la racine du projet ; ses images sont deja en place.
        racine, dossier_images, copier = source, source / "images", False
        if not dossier_images.is_dir():
            print(f"{dossier_images} n'existe pas — un projet attend ses images la.",
                  file=sys.stderr)
            return 1
    else:
        racine, dossier_images, copier = Path(arguments.projet), source, True

    if project.existe(racine):
        projet = project.charger(racine)
        try:
            projet.figer(
                espace_colorimetrique=arguments.espace,
                axes=arguments.axes,
                unites=arguments.unites,
            )
        except project.DecisionFigee as refus:
            print(f"decision figee : {refus}", file=sys.stderr)
            return 1
        print(f"projet existant : {projet.nom}")
    else:
        projet = project.creer(
            racine,
            espace_colorimetrique=arguments.espace,
            axes=arguments.axes,
            unites=arguments.unites,
        )
        print(f"projet cree : {projet.manifeste}")

    rapport = ingest_images.ingerer(dossier_images, projet, copier=copier)
    print(rapport.resume())
    return 0


def construire_analyseur() -> argparse.ArgumentParser:
    analyseur = argparse.ArgumentParser(
        prog=naming.CLI_COMMAND,
        description=f"{naming.EXTENSION_NAME} — moteur, utilisable sans Blender",
    )
    analyseur.add_argument("--version", action="version", version=VERSION)
    sous = analyseur.add_subparsers(dest="commande", required=True)

    doctor = sous.add_parser("doctor", help="inventorie la machine, n'installe rien")
    doctor.set_defaults(fonction=commande_doctor)

    serve = sous.add_parser("serve", help="demarre le serveur")
    _ajouter_options_adresse(serve)
    serve.set_defaults(fonction=commande_serve)

    health = sous.add_parser("health", help="interroge un serveur deja demarre")
    _ajouter_options_adresse(health)
    health.set_defaults(fonction=commande_health)

    ingest = sous.add_parser("ingest", help="fait entrer des images dans un projet")
    ingest.add_argument("source", help="dossier d'images, ou racine du projet avec --sur-place")
    ingest.add_argument("--projet", help="racine du projet a creer ou completer")
    ingest.add_argument(
        "--sur-place",
        action="store_true",
        help="la source est deja la racine du projet ; ne copie rien",
    )
    ingest.add_argument(
        "--espace",
        default="sRGB",
        choices=project.ESPACES_COLORIMETRIQUES,
        help="espace colorimetrique — decision figee (defaut : sRGB)",
    )
    ingest.add_argument(
        "--axes",
        default="z_up_droite",
        choices=tuple(project.AXES),
        help="convention d'axes — decision figee (defaut : z_up_droite, celle de Blender)",
    )
    ingest.add_argument(
        "--unites",
        default="metre",
        choices=project.UNITES,
        help="unites — decision figee (defaut : metre)",
    )
    ingest.set_defaults(fonction=commande_ingest)

    return analyseur


def main(argv: list[str] | None = None) -> int:
    arguments = construire_analyseur().parse_args(argv)
    return arguments.fonction(arguments)


if __name__ == "__main__":
    raise SystemExit(main())
