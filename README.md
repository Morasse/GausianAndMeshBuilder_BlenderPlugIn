# GausianAndMeshBuilder_BlenderPlugIn

**Pipeline 3D Gaussian Splatting complet, piloté depuis Blender : DNG → splat → mesh → relight → re-splat.**

Blender est l'interface unique. L'ingestion RAW, la curation d'images, les poses,
le training, l'extraction de mesh, la correction et le relighting se pilotent
depuis des panneaux du viewport. Aucun aller-retour vers une autre application.

> **État : P0.** Le dépôt, sa gouvernance et la table de nommage. Aucune logique
> métier n'est encore écrite. Voir [Phases](#phases).

---

## Le nom s'écrit comme ça

**`Gausian` prend un seul `s`.** Ce n'est pas une faute de frappe, et ce n'est
pas à corriger — ni ici, ni dans un import, ni « en passant » pendant un
refactoring.

Le risque n'est pas l'orthographe : c'est qu'une normalisation partielle casse
les imports, l'URL du remote et l'id de l'extension Blender d'une façon
particulièrement pénible à débugger. Le CI casse si la chaîne est corrigée
quelque part.

### Table de nommage

Toutes ces valeurs sont définies **une seule fois**, dans
[`engine/gamb_engine/naming.py`](engine/gamb_engine/naming.py), et importées
partout. Aucun nom en dur ailleurs dans le code.

| Contexte | Valeur exacte |
|---|---|
| Dépôt GitHub | `GausianAndMeshBuilder_BlenderPlugIn` |
| Racine du repo | `GausianAndMeshBuilder_BlenderPlugIn/` |
| Blender extension `id` + dossier de l'addon | `gausian_and_mesh_builder` |
| `name` du manifeste (affiché dans l'UI Blender) | `Gausian And Mesh Builder` |
| Onglet N-panel dans le viewport | `GAMB` |
| Package Python du sidecar | `gamb_engine` |
| Binaire / commande CLI | `gamb` |
| Préfixe des opérateurs Blender | `gamb.` (ex. `gamb.start_training`) |
| Manifeste du projet sur disque | `gamb.json` |

---

## Architecture

Deux décisions structurent tout le reste.

### 1. Sidecar — jamais PyTorch dans Blender

```
┌─────────────────────────────┐         ┌──────────────────────────────┐
│ addon Blender (GPL-3)       │  HTTP   │ gamb-engine (sidecar)        │
│ gausian_and_mesh_builder/   │◄───────►│ venv Python 3.11 ou 3.12     │
│  - panneaux N-panel         │   + WS  │  FastAPI + uvicorn           │
│  - opérateurs               │         │  torch / gsplat / SAM 3      │
│  - stdlib + urllib, rien de │         │  queue de jobs séquentielle  │
│    plus                     │         │  model manager (load/unload) │
└─────────────────────────────┘         └──────────────────────────────┘
                    │                                    │
                    └──────── projet sur disque ─────────┘
                             (source de vérité)
```

Pourquoi, en trois points :

- Les wheels d'une extension Blender **partagent le namespace de modules global**.
  Un autre addon qui embarque numpy ou torch entre en conflit avec le tien, et
  il n'existe pas de moyen pratique d'avoir deux versions résidentes.
- Un OOM CUDA ou un crash du rastériseur ferait tomber **Blender**, avec la
  scène non sauvegardée.
- Blender embarque Python 3.13, où les wheels CUDA Windows sont inégaux. Le
  moteur reste en 3.11/3.12, là où l'écosystème est stable.

**Le sidecar doit rester pilotable seul, en CLI.** C'est ce qui rend l'outil
testable sans Blender et scriptable en batch. Toute capacité ajoutée au moteur a
une entrée CLI *et* une route REST, jamais l'une sans l'autre.

### 2. Le mesh est la colonne vertébrale, pas un sous-produit

L'ordre habituel — entraîner, puis extraire un mesh du résultat — est inversé
ici : **géométrie proxy → training guidé → mesh raffiné → bake d'attributs →
export.**

Un seul et même mesh sert quatre besoins :

| Besoin | Rôle du mesh |
|---|---|
| Guider le training | Prior géométrique : init des gaussiennes sur la surface |
| Supprimer les floaters | Volumes *keep/kill*, pénalité SDF, loss masking |
| Rééclairer avec occlusion | Support des normales, de l'AO et des matériaux PBR |
| Animer (plus tard) | Cage de déformation liée à une armature |

Le proxy vient soit d'un **blockout manuel dans Blender** — zéro ML, contrôle
total, et la réponse la plus directe à « pas de splat là où je n'en veux pas » —
soit d'un run de training rapide. Les deux alimentent la même interface.

---

## Prérequis

| | |
|---|---|
| GPU | NVIDIA avec CUDA. Développé sur RTX 4080 **16 GB** |
| CPU / RAM | Ryzen 9 7950X, station de travail |
| OS | Windows (cible primaire), Linux pour le CI |
| Blender | **5.2 LTS** (Python 3.13) — `blender_version_min = "5.1.0"` au plus bas |
| Python moteur | **3.11 ou 3.12**, séparé de celui de Blender |

Le budget VRAM est une **config, pas une constante** : sur 16 GB, le plafond
pratique tourne autour de 4–5 M de gaussiennes, et bien moins si un autre modèle
est résident. D'où la règle non négociable du moteur : **un seul job GPU à la
fois**, et un model manager qui charge, exécute, libère.

---

## Phases

Chaque phase est livrable et testable seule. On ne passe pas à la suivante avant
que son critère soit vert.

| | Phase | Critère d'acceptation |
|---|---|---|
| **P0** | Dépôt, gouvernance, CI, nommage | clone frais + CI vert |
| P1 | Sidecar `/health` + addon qui l'affiche | le panneau montre « engine: online » |
| P2 | Ingestion DNG 16-bit linéaire, WB fixe | 200 DNG → `images/` cohérent |
| P3 | Curation : flou, similarité, clipping | les rejets = ceux d'un tri à l'œil |
| P4 | Poses COLMAP → caméras Blender | les caméras s'alignent sur la scène |
| P5 | Training gsplat de référence | PSNR à ±0.3 dB du CLI équivalent |
| P6 | Blockout manuel + proxy automatique | le trainer lit les volumes posés |
| P7 | **Prior géométrique** | **à PSNR égal : moins de gaussiennes, zéro floater hors volume** |
| P8 | Mesh raffiné + SAM 3 + masques | les floaters dans la vitre disparaissent |
| P9 | Bake d'attributs : PBR, AO, visibilité | le splat réagit à un changement d'éclairage |
| P10 | Splats animables : binding armature → gaussiennes | — |

**P7 est le cœur du projet** : son critère est mesurable, falsifiable, et valide
toute la thèse d'un coup.

### Portabilité moteur de jeu

L'export vers un moteur de jeu (Godot ou autre) viendra plus tard, mais rien ne
doit fermer cette porte entre-temps. Quatre contraintes permanentes :

- **Axes et unités figés** dans `gamb.json`, la transformation appliquée à
  l'export et jamais en interne.
- **Couche d'export isolée** du format interne : un nouveau moteur = un module,
  pas une refonte.
- **Matériaux en PBR metal-roughness façon glTF**, jamais un node setup Blender.
- **Un preset `realtime`** qui plafonne le nombre de gaussiennes et le degré de SH.

Le chemin mesh + PBR est déjà agnostique : un glTF metal-roughness entre dans
n'importe quel moteur sans adaptation.

---

## Licences

Deux sujets distincts, deux fichiers :

- **[`LICENSING.md`](LICENSING.md)** — la licence du code de ce dépôt.
  `addon/` est en GPL-3.0-or-later (conséquence de l'API Blender), `engine/` en
  Apache-2.0.
- **[`LICENSES.md`](LICENSES.md)** — la licence de chaque dépendance : 126
  composants, chacun vérifié à sa source primaire.

Une distinction à ne jamais confondre, et c'est l'erreur la plus coûteuse du
domaine : le **copyleft** (GPL) se déclenche à la *distribution du code* et ne
contamine pas les assets produits. Une clause **non-commerciale** (INRIA,
PolyForm, CC-BY-NC) se déclenche à l'*usage du logiciel* et **contamine les
assets**. Un splat produit avec un outil non-commercial ne peut pas partir dans
un produit vendu, même si l'outil n'est jamais distribué.

L'usage commercial du projet n'étant pas tranché, toute méthode non-commerciale
vit derrière un gate `commercial_mode` et n'est jamais le chemin par défaut.

## Contribuer

Voir [`CONTRIBUTING.md`](CONTRIBUTING.md) — en particulier l'initialisation des
submodules, sans laquelle un clone frais donne des dossiers vides et une erreur
incompréhensible.
