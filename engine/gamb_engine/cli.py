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
    gamb build     applique le correctif gsplat et compile ses kernels CUDA
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

from gamb_engine import bootstrap, build, machine, naming, project
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
        vcvars = build.trouver_vcvars()
        print(f"  vcvars64.bat : {vcvars or 'INTROUVABLE'}")
    if chaine.complete:
        print("  -> gsplat pourra compiler ses kernels au besoin")
    else:
        print(f"  -> manquant : {', '.join(chaine.manquant)}")
        print("     gsplat echouera s'il doit compiler plutot qu'utiliser une wheel")

    print()
    print("=== gsplat ===")
    if not build.submodule_present():
        print(f"  submodule absent : {build.SUBMODULE_GSPLAT}")
        print("  -> git submodule update --init --recursive")
    else:
        print(f"  submodule present, v{build.GSPLAT_VERSION} attendu")
        if build.glm_present():
            print("  glm (submodule imbrique) : present")
        else:
            print("  glm (submodule imbrique) : ABSENT — la compilation echouera")
            print("  -> git submodule update --init --recursive")
        etat = "applique" if build.patch_applique() else "PAS applique"
        print(f"  correctif MSVC : {etat}")
        if not build.patch_applique():
            print("  -> gamb build")

    return 0


def commande_build(arguments: argparse.Namespace) -> int:
    """Applique le correctif et declenche la compilation CUDA de gsplat."""
    try:
        pose = build.appliquer_patch()
    except build.PreparationImpossible as probleme:
        print(f"preparation impossible : {probleme}", file=sys.stderr)
        return 1

    print(f"correctif MSVC : {'applique maintenant' if pose else 'deja en place'}")

    outils = build.outillage()
    if not outils.complet:
        print(f"outillage incomplet : {', '.join(outils.manquant)}", file=sys.stderr)
        return 1

    if arguments.correctif_seulement:
        return 0

    try:
        environnement = build.environnement_execution()
    except build.PreparationImpossible as probleme:
        print(f"environnement de compilation indisponible : {probleme}", file=sys.stderr)
        return 1

    print("compilation des kernels CUDA (plusieurs dizaines de secondes au premier run)...")
    resultat = subprocess.run(
        [sys.executable, "-c", "from gsplat.cuda._backend import _C; print(_C.__name__)"],
        env=environnement,
        capture_output=True,
        text=True,
        check=False,
    )
    if resultat.returncode != 0:
        print(resultat.stdout[-3000:], file=sys.stderr)
        print(resultat.stderr[-3000:], file=sys.stderr)
        return 1

    print("kernels CUDA disponibles.")
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


def commande_options(_: argparse.Namespace) -> int:
    """Les fiches, en clair. C'est la meme source que celle servie a l'addon."""
    from gamb_engine import options

    print("=== Presets ===")
    for preset in options.presets().values():
        print(f"\n  {preset.nom}")
        print(f"    {preset.description}")
        for cle, valeur in sorted(preset.parametres.items()):
            print(f"      {cle} = {valeur}")

    print("\n=== Fiches d'options ===")
    for fiche in options.fiches().values():
        print(f"\n  {fiche.cle} — {fiche.libelle}  (defaut : {fiche.defaut})")
        print(f"    {fiche.effet.strip()}")
        print(f"    monter quand  : {fiche.monter_quand}")
        print(f"    baisser quand : {fiche.baisser_quand}")
        print(f"    cout          : {fiche.cout}")
    return 0


def commande_train(arguments: argparse.Namespace) -> int:
    from gamb_engine import build, options
    from gamb_engine.train import gsplat_runner

    # gsplat re-entre dans son chemin JIT a chaque import : sans cet
    # environnement, l'import echoue sur ninja meme quand tout est compile.
    build.activer()

    try:
        projet = project.charger(arguments.projet)
    except (project.ProjetIntrouvable, project.FormatIncompatible) as probleme:
        print(f"projet illisible : {probleme}", file=sys.stderr)
        return 1

    try:
        configuration = gsplat_runner.Configuration.depuis_preset(
            arguments.preset,
            iterations=arguments.iterations,
            cap_max=arguments.cap_max,
            degre_sh=arguments.degre_sh,
            resolution=arguments.resolution,
            poids_ssim=arguments.poids_ssim,
        )
    except (options.PresetIntrouvable, options.OptionInconnue) as probleme:
        print(f"configuration refusee : {probleme}", file=sys.stderr)
        return 1

    print(f"projet : {projet.nom}  preset : {arguments.preset}")
    print(f"{configuration.iterations} iterations, cap_max {configuration.cap_max}")

    def avancement(etape: int, total: int, valeur_psnr: float) -> None:
        if etape % 1000 == 0:
            print(f"  {etape:>6}/{total}  psnr {valeur_psnr:.2f}", flush=True)

    try:
        resultat = gsplat_runner.entrainer(projet, configuration, avancement)
    except (RuntimeError, ValueError, FileNotFoundError) as probleme:
        print(f"entrainement interrompu : {probleme}", file=sys.stderr)
        return 1

    metriques = resultat.metriques
    print(f"\nrun : {resultat.dossier}")
    print(f"  gaussiennes    : {metriques.nombre_gaussiennes}")
    print(f"  PSNR entrainement : {metriques.psnr_entrainement:.2f} dB")
    print(f"  PSNR test         : {metriques.psnr_test:.2f} dB  (vues jamais vues)")
    print(f"  SSIM test         : {metriques.ssim_test:.4f}")
    print(f"  duree             : {metriques.duree_s:.0f} s")
    return 0


def commande_prior(arguments: argparse.Namespace) -> int:
    """Écrit un prior géométrique dans le projet.

    À P4 une seule source automatique : la boîte englobante du nuage
    d'initialisation. C'est le garde-fou minimal — il suffit déjà à interdire
    les floaters lointains, sans rien modéliser. Les volumes dessinés à la main
    dans Blender arriveront par l'addon, dans le même `prior.json`.
    """
    from gamb_engine.poses import colmap
    from gamb_engine.train import geometry_prior

    try:
        projet = project.charger(arguments.projet)
        modele = colmap.lire(projet.racine)
    except (project.ProjetIntrouvable, colmap.ModeleIllisible) as probleme:
        print(f"projet illisible : {probleme}", file=sys.stderr)
        return 1

    if not modele.points:
        print("aucun nuage d'initialisation — rien pour deduire un volume", file=sys.stderr)
        return 1

    volume = geometry_prior.volume_englobant(modele.points, marge=arguments.marge)
    prior = geometry_prior.PriorGeometrique(
        volumes=[volume],
        elaguer_tous_les=arguments.elaguer_tous_les,
    )
    chemin = prior.ecrire(projet.racine)

    demi = [volume.matrice[i][i] for i in range(3)]
    centre = [volume.matrice[i][3] for i in range(3)]
    print(f"prior ecrit : {chemin}")
    print(f"  volume englobant, marge {arguments.marge}")
    print(f"  centre      : {', '.join(f'{v:.2f}' for v in centre)}")
    print(f"  demi-dimensions : {', '.join(f'{v:.2f}' for v in demi)}")
    print(f"  elagage tous les {arguments.elaguer_tous_les} pas")
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

    construction = sous.add_parser(
        "build", help="applique le correctif gsplat et compile ses kernels CUDA"
    )
    construction.add_argument(
        "--correctif-seulement",
        action="store_true",
        help="pose le correctif sans lancer la compilation",
    )
    construction.set_defaults(fonction=commande_build)

    fiches = sous.add_parser("options", help="affiche les fiches d'options et les presets")
    fiches.set_defaults(fonction=commande_options)

    entrainement = sous.add_parser("train", help="entraine un splat sur un projet")
    entrainement.add_argument("projet", help="racine du projet")
    entrainement.add_argument("--preset", default="production", help="defaut : production")
    for cle in ("iterations", "cap-max", "degre-sh", "resolution"):
        entrainement.add_argument(f"--{cle}", type=int, default=None)
    entrainement.add_argument("--poids-ssim", type=float, default=None)
    entrainement.set_defaults(fonction=commande_train)

    prior = sous.add_parser("prior", help="ecrit un prior geometrique dans le projet")
    prior.add_argument("projet", help="racine du projet")
    prior.add_argument(
        "--marge", type=float, default=0.05, help="marge relative autour du nuage"
    )
    prior.add_argument("--elaguer-tous-les", type=int, default=100)
    prior.set_defaults(fonction=commande_prior)

    return analyseur


def main(argv: list[str] | None = None) -> int:
    arguments = construire_analyseur().parse_args(argv)
    return arguments.fonction(arguments)


if __name__ == "__main__":
    raise SystemExit(main())
