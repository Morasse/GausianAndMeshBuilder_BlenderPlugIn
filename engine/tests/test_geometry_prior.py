# SPDX-License-Identifier: Apache-2.0
"""Gardes sur le prior géométrique — le cœur du projet.

La recherche du 2026-08-11 a montré que la brique (b) — **interdire les
gaussiennes hors d'un volume pendant l'entraînement** — n'existe dans aucun
outil : gsplat, splatfacto, Postshat et Brush ne proposent que du recadrage
après coup. C'est donc le seul code de ce dépôt qui n'a pas d'équivalent
ailleurs, et celui qui mérite le plus de tests.

Deux garde-fous comptent particulièrement :

- `test_un_volume_qui_supprimerait_tout_ne_fait_rien` : un volume mal placé
  viderait la scène et ferait planter la suite sur des tenseurs vides.
- `test_sans_volume_a_garder_seuls_les_exclure_comptent` : poser une seule
  boîte d'exclusion ne doit pas vider tout le reste.
"""

import json

import pytest

from gamb_engine.train import geometry_prior as prior

torch = pytest.importorskip("torch")


def _cube(centre=(0.0, 0.0, 0.0), demi=1.0, mode=prior.GARDER, forme=prior.BOITE):
    matrice = [
        [demi, 0.0, 0.0, centre[0]],
        [0.0, demi, 0.0, centre[1]],
        [0.0, 0.0, demi, centre[2]],
        [0.0, 0.0, 0.0, 1.0],
    ]
    return prior.Volume(
        matrice=tuple(tuple(ligne) for ligne in matrice), mode=mode, forme=forme
    )


# --- Le volume ---------------------------------------------------------------


def test_le_cube_unite_contient_ce_qu_il_doit():
    volume = _cube(demi=1.0)
    points = torch.tensor([[0.0, 0.0, 0.0], [0.9, 0.9, 0.9], [1.5, 0.0, 0.0]])

    assert volume.contient(points, torch).tolist() == [True, True, False]


def test_un_volume_translate_et_mis_a_l_echelle():
    volume = _cube(centre=(10.0, 0.0, 0.0), demi=2.0)
    points = torch.tensor([[10.0, 0.0, 0.0], [11.9, 0.0, 0.0], [12.5, 0.0, 0.0]])

    assert volume.contient(points, torch).tolist() == [True, True, False]


def test_la_sphere_n_est_pas_le_cube():
    """Le coin du cube est hors de la sphère inscrite — c'est tout l'intérêt."""
    coin = torch.tensor([[0.9, 0.9, 0.9]])

    assert _cube(forme=prior.BOITE).contient(coin, torch).item() is True
    assert _cube(forme=prior.SPHERE).contient(coin, torch).item() is False


def test_une_forme_ou_un_mode_inconnu_est_refuse():
    with pytest.raises(prior.PriorInvalide):
        _cube(mode="peut_etre")
    with pytest.raises(prior.PriorInvalide):
        _cube(forme="cylindre")


def test_une_matrice_qui_n_est_pas_4x4_est_refusee():
    with pytest.raises(prior.PriorInvalide, match="4x4"):
        prior.Volume(matrice=((1.0, 0.0), (0.0, 1.0)))


# --- Le masque de suppression ------------------------------------------------


def test_ce_qui_est_hors_du_volume_a_garder_est_supprime():
    contrainte = prior.PriorGeometrique(volumes=[_cube(demi=1.0)])
    points = torch.tensor([[0.0, 0.0, 0.0], [5.0, 0.0, 0.0]])

    assert contrainte.masque_a_supprimer(points, torch).tolist() == [False, True]


def test_ce_qui_est_dans_un_volume_a_exclure_est_supprime():
    contrainte = prior.PriorGeometrique(
        volumes=[_cube(demi=10.0), _cube(centre=(5.0, 0.0, 0.0), demi=1.0, mode=prior.EXCLURE)]
    )
    points = torch.tensor([[0.0, 0.0, 0.0], [5.0, 0.0, 0.0]])

    assert contrainte.masque_a_supprimer(points, torch).tolist() == [False, True]


def test_plusieurs_volumes_a_garder_s_additionnent():
    """Deux régions distinctes : être dans l'une suffit."""
    contrainte = prior.PriorGeometrique(
        volumes=[_cube(demi=1.0), _cube(centre=(10.0, 0.0, 0.0), demi=1.0)]
    )
    points = torch.tensor([[0.0, 0.0, 0.0], [10.0, 0.0, 0.0], [5.0, 0.0, 0.0]])

    assert contrainte.masque_a_supprimer(points, torch).tolist() == [False, False, True]


def test_sans_volume_a_garder_seuls_les_exclure_comptent():
    """Poser une seule boîte d'exclusion ne doit pas vider toute la scène."""
    contrainte = prior.PriorGeometrique(
        volumes=[_cube(centre=(5.0, 0.0, 0.0), demi=1.0, mode=prior.EXCLURE)]
    )
    points = torch.tensor([[0.0, 0.0, 0.0], [100.0, 0.0, 0.0], [5.0, 0.0, 0.0]])

    assert contrainte.masque_a_supprimer(points, torch).tolist() == [False, False, True]


def test_un_prior_sans_volume_ni_sdf_est_inactif():
    assert prior.PriorGeometrique().actif is False
    assert prior.PriorGeometrique(volumes=[_cube()]).actif is True


# --- L'élagage ---------------------------------------------------------------


class _FauxOptimiseur:
    """Assez d'API pour que gsplat.strategy.ops.remove fonctionne."""

    def __init__(self, parametre):
        self.param_groups = [{"params": [parametre]}]
        self.state = {parametre: {}}


def _contexte(points):
    parametres = {"means": torch.nn.Parameter(points)}
    return parametres, {"means": _FauxOptimiseur(parametres["means"])}, {}


def test_l_elagage_retire_ce_qui_sort(monkeypatch):
    pytest.importorskip("gsplat")
    contrainte = prior.PriorGeometrique(
        volumes=[_cube(demi=1.0)], elaguer_tous_les=1, elaguer_a_partir_de=0
    )
    parametres, optimiseurs, etat = _contexte(
        torch.tensor([[0.0, 0.0, 0.0], [9.0, 0.0, 0.0], [0.5, 0.5, 0.5]])
    )

    retirees = contrainte.elaguer(parametres, optimiseurs, etat, 0, torch)

    assert retirees == 1
    assert parametres["means"].shape[0] == 2


def test_l_etat_non_indexe_par_gaussienne_survit_a_l_elagage():
    """Piège réel de gsplat, payé une fois par une assertion CUDA.

    `ops.remove` découpe **tous** les tenseurs de l'état avec des indices de
    gaussiennes. Or `MCMCStrategy` y range `binoms`, une table 51x51 de
    coefficients binomiaux : la découper avec des centaines de milliers
    d'indices déclenche un `index out of bounds` côté CUDA, très loin de sa
    cause. `remove` a été écrit pour `DefaultStrategy`, dont l'état est bien
    per-gaussienne.
    """
    pytest.importorskip("gsplat")
    contrainte = prior.PriorGeometrique(
        volumes=[_cube(demi=1.0)], elaguer_tous_les=1, elaguer_a_partir_de=0
    )
    parametres, optimiseurs, _ = _contexte(
        torch.tensor([[0.0, 0.0, 0.0], [9.0, 0.0, 0.0], [0.5, 0.5, 0.5]])
    )
    binoms = torch.ones(51, 51)
    etat = {"binoms": binoms, "par_gaussienne": torch.arange(3.0)}

    contrainte.elaguer(parametres, optimiseurs, etat, 0, torch)

    assert etat["binoms"].shape == (51, 51), "binoms a été découpé — assertion CUDA garantie"
    assert etat["par_gaussienne"].shape == (2,), "l'état per-gaussienne doit suivre l'élagage"


def test_un_volume_qui_supprimerait_tout_ne_fait_rien():
    """Un volume mal placé viderait la scène et planterait la suite."""
    contrainte = prior.PriorGeometrique(
        volumes=[_cube(centre=(1000.0, 0.0, 0.0), demi=1.0)],
        elaguer_tous_les=1,
        elaguer_a_partir_de=0,
    )
    parametres, optimiseurs, etat = _contexte(torch.tensor([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0]]))

    assert contrainte.elaguer(parametres, optimiseurs, etat, 0, torch) == 0
    assert parametres["means"].shape[0] == 2


def test_l_elagage_respecte_sa_cadence_et_son_demarrage():
    contrainte = prior.PriorGeometrique(
        volumes=[_cube(demi=1.0)], elaguer_tous_les=100, elaguer_a_partir_de=500
    )
    parametres, optimiseurs, etat = _contexte(torch.tensor([[9.0, 0.0, 0.0], [0.0, 0.0, 0.0]]))

    assert contrainte.elaguer(parametres, optimiseurs, etat, 100, torch) == 0  # trop tôt
    assert contrainte.elaguer(parametres, optimiseurs, etat, 550, torch) == 0  # hors cadence


def test_la_passe_finale_ignore_la_cadence():
    """Sans elle, le PLY livré contient encore ce que l'utilisateur a exclu.

    La densification tourne jusqu'au dernier pas : les gaussiennes créées après
    le dernier élagage périodique survivraient jusque dans le fichier de sortie.
    """
    pytest.importorskip("gsplat")
    contrainte = prior.PriorGeometrique(
        volumes=[_cube(demi=1.0)], elaguer_tous_les=100, elaguer_a_partir_de=500
    )
    parametres, optimiseurs, etat = _contexte(torch.tensor([[9.0, 0.0, 0.0], [0.0, 0.0, 0.0]]))

    assert contrainte.elaguer(parametres, optimiseurs, etat, 7, torch, final=True) == 1
    assert parametres["means"].shape[0] == 1


# --- La pénalité SDF ---------------------------------------------------------


def test_sans_sdf_il_n_y_a_pas_de_penalite():
    assert prior.PriorGeometrique().penalite(torch.zeros(3, 3), torch) is None


def test_la_penalite_croit_avec_l_eloignement():
    # Grille 1D triviale : distance = |x|, échantillonnée sur [-2, 2].
    axe = torch.linspace(-2.0, 2.0, 5)
    grille = axe.abs()[None, None, :].expand(5, 5, 5).contiguous()
    sdf = prior.GrilleSdf(valeurs=grille, origine=(-2.0, -2.0, -2.0), pas=1.0)
    contrainte = prior.PriorGeometrique(sdf=sdf, poids_sdf=1.0)

    proche = contrainte.penalite(torch.tensor([[0.0, 0.0, 0.0]]), torch)
    loin = contrainte.penalite(torch.tensor([[2.0, 0.0, 0.0]]), torch)

    assert float(loin) > float(proche)


def test_la_marge_annule_la_penalite_pres_de_la_surface():
    axe = torch.linspace(-2.0, 2.0, 5)
    grille = axe.abs()[None, None, :].expand(5, 5, 5).contiguous()
    sdf = prior.GrilleSdf(valeurs=grille, origine=(-2.0, -2.0, -2.0), pas=1.0)
    contrainte = prior.PriorGeometrique(sdf=sdf, poids_sdf=1.0, marge_sdf=5.0)

    assert float(contrainte.penalite(torch.tensor([[2.0, 0.0, 0.0]]), torch)) == 0.0


# --- Persistance -------------------------------------------------------------


def test_aller_retour_sur_disque(tmp_path):
    contrainte = prior.PriorGeometrique(
        volumes=[_cube(demi=3.0), _cube(centre=(1.0, 2.0, 3.0), mode=prior.EXCLURE)],
        poids_sdf=0.5,
        marge_sdf=0.01,
    )
    contrainte.ecrire(tmp_path)
    recharge = prior.charger(tmp_path)

    assert len(recharge.volumes) == 2
    assert recharge.volumes[1].mode == prior.EXCLURE
    assert recharge.poids_sdf == 0.5
    assert json.loads((tmp_path / prior.NOM_FICHIER).read_text(encoding="utf-8"))["volumes"]


def test_l_absence_de_prior_n_est_pas_une_erreur(tmp_path):
    """C'est le cas nominal du premier run, celui dont on extraira le proxy."""
    assert prior.charger(tmp_path) is None


def test_le_volume_englobant_contient_le_nuage():
    points = [[0.0, 0.0, 0.0], [1.0, 2.0, 3.0], [-1.0, -2.0, -3.0]]
    volume = prior.volume_englobant(points, marge=0.0)

    assert volume.contient(torch.tensor(points), torch).all()
    assert volume.mode == prior.GARDER


def test_le_volume_englobant_exclut_ce_qui_est_loin():
    volume = prior.volume_englobant([[0.0, 0.0, 0.0], [1.0, 1.0, 1.0]], marge=0.05)
    assert not volume.contient(torch.tensor([[50.0, 0.0, 0.0]]), torch).item()
