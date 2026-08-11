# Contribuer à GAMB

## ⚠️ Le clone : `--recurse-submodules`, sinon rien ne marche

Tout code de recherche tiers vendorisé vit en **submodule** sous `third_party/`,
jamais en copier-coller dans l'arborescence. Un clone qui les oublie donne des
dossiers vides et une erreur d'import parfaitement incompréhensible.

```bash
git clone --recurse-submodules https://github.com/Morasse/GausianAndMeshBuilder_BlenderPlugIn.git
```

Clone déjà fait sans l'option, ou submodule ajouté depuis :

```bash
git submodule update --init --recursive
```

Après un `git pull` qui touche un submodule :

```bash
git submodule update --recursive
```

> À P0, `third_party/` n'existe pas encore — aucun submodule n'a été ajouté. Le
> réflexe se prend maintenant pour ne pas se découvrir le jour où le premier
> arrive.

**Pourquoi des submodules et pas une copie ?** La traçabilité de licence et de
version. Un dossier copié perd son origine, son commit et sa licence en trois
mois. Un submodule pointe un SHA vérifiable, et
[`LICENSES.md`](LICENSES.md) peut rester honnête.

---

## Environnement

### Deux Python, et ce n'est pas un accident

| | Version | Qui l'installe |
|---|---|---|
| Addon Blender | **3.13** | Blender, embarqué. Rien à faire. |
| Sidecar `gamb-engine` | **3.11 ou 3.12** | Toi, séparément. |

Le moteur ne tourne **pas** dans le Python de Blender — c'est toute la thèse de
l'architecture, expliquée dans le [README](README.md#architecture).

### D'abord regarder ce qui est déjà là

**Ne pas installer avant d'avoir inventorié.** Un interpréteur déjà présent peut
être totalement invisible des inventaires habituels : sur la machine de
développement, les Python 3.11 et 3.12 étaient installés et gérés par `uv`,
donc absents du `PATH`, du registre Windows *et* de `py --list-paths`. Trois
inventaires, trois réponses différentes.

```bash
uv python list          # le plus souvent celui qui trouve
py --list-paths         # registre PEP 514 (Windows)
```

Deux faux positifs à ne jamais retenir :

- `WindowsApps\python.exe` et `python3.exe` sont des **stubs du Microsoft
  Store** : ils ouvrent le Store au lieu de lancer Python.
- Le Python embarqué de Blender (`Blender 5.2\5.2\python\bin\python.exe`).
  Le prendre pour le sidecar annulerait la raison d'être de l'architecture.

Si — et seulement si — rien de convenable n'existe :

```bash
uv python install 3.12                  # build autonome, ne touche pas au système
# ou : winget install Python.Python.3.12
```

### Installation

```bash
uv venv --python 3.12                   # trouve l'interpréteur, ou le provisionne
.venv\Scripts\activate                  # Windows
# source .venv/bin/activate             # Linux / macOS

uv pip install -e ./engine
uv pip install ruff pytest
```

Sans `uv`, et à condition que l'interpréteur soit enregistré auprès du lanceur
`py` — ce qui n'est pas le cas d'un Python géré par `uv` :

```bash
py -3.12 -m venv .venv
```

### Avant de pousser

Exactement ce que fait le CI :

```bash
ruff check .
pytest engine/tests -q
```

⚠️ **Un venv tiède ne reconstruit pas le paquet.** Si tu touches à
`engine/pyproject.toml`, refais la vérification dans un environnement **neuf** —
sinon un build cassé passe inaperçu en local et n'apparaît qu'en CI :

```bash
uv venv --python 3.11 /tmp/verif && uv pip install --python /tmp/verif -e ./engine
```

### La pile d'entraînement (gsplat + CUDA)

Optionnelle : le sidecar démarre, répond et ingère sans elle. Elle n'est requise
que pour entraîner.

Les versions sont **épinglées**, et ce n'est pas de la prudence : gsplat déclare
`torch` sans aucune borne, donc un `pip install gsplat` prend la dernière version
publiée et casse. C'est exactement ce qui est arrivé — torch 2.11 est
incompilable sous Windows, son en-tête déclarant un paramètre nommé `small` que
le SDK Windows redéfinit en `char`.

```bash
git submodule update --init --recursive          # ⚠️ AVANT tout le reste
uv pip install --index-url https://download.pytorch.org/whl/cu128 torch==2.8.0
BUILD_NO_CUDA=1 uv pip install --no-build-isolation -e ./third_party/gsplat
gamb build
```

**L'ordre compte.** gsplat a lui-même un submodule imbriqué, `glm`, dont
dépendent tous ses kernels. Et une fois le correctif MSVC posé, le submodule est
modifié, donc git refuse de le mettre à jour — il faut donc initialiser
récursivement *avant*. Sans `glm`, la compilation démarre quand même et échoue au
dixième fichier dans des milliers de lignes de log nvcc. `gamb doctor` et
`gamb build` le vérifient désormais et le disent en une phrase.

**`BUILD_NO_CUDA=1` n'est pas un contournement** : c'est ainsi qu'upstream
produit sa propre wheel PyPI, qui est `py3-none-any`. Sans lui, l'installation
compile les kernels immédiatement, dans un shell qui n'a pas `cl.exe`, et
échoue. Avec lui, l'installation est pure Python et `gamb build` prend la suite :
il pose le correctif MSVC, prépare l'environnement Visual Studio, puis déclenche
la compilation (~80 s, une seule fois).

Prérequis vérifiables sans rien installer :

```bash
gamb doctor        # nvcc, MSVC, vcvars64.bat, état du submodule et du correctif
```

### Le dataset de test

Les vraies captures sont lentes à produire et leurs poses sont *estimées*. Sur
un dataset photo, un mauvais résultat peut venir de l'entraînement ou des poses,
et rien ne permet de les distinguer.

D'où un dataset synthétique dont les poses sont **exactes** :

```bash
blender --background --factory-startup \
    --python scripts/generer_dataset_synthetique.py -- --sortie ./dataset_test

python scripts/verifier_dataset.py ./dataset_test     # attendu : DATASET COHERENT
gamb ingest ./dataset_test --sur-place                # en fait un projet GAMB
```

La vérification reprojette le point que toutes les caméras visent : s'il ne
tombe pas au centre de chaque image, la conversion de repère Blender → COLMAP
est fausse. C'est une erreur invisible à l'œil sur les images rendues, qui ne se
manifeste que par un entraînement qui ne converge jamais.

Ce dataset porte ses poses au format COLMAP, donc **l'entraîneur se valide sans
COLMAP**.

### Entraîner

```bash
gamb options                                   # les fiches et les presets, en clair
gamb train ./dataset_test --preset apercu      # ~1 min, pour vérifier que tout tient
gamb train ./dataset_test --preset production  # la référence
```

Chaque run écrit un dossier **immuable** sous `runs/`, contenant sa
configuration **complète** — pas un diff — ses métriques et son PLY. C'est ce
qui rend deux runs comparables : sans la config entière, une comparaison A/B
ment dès qu'un défaut a changé entre-temps.

Le PSNR affiché en fin de run est celui des **vues de test**, une sur huit, que
l'optimisation n'a jamais vues. Le PSNR d'entraînement mesure la capacité à
mémoriser ; seul celui de test mesure la reconstruction.

### Ajouter un réglage : la règle §14

**Aucun libellé ni tooltip n'est écrit en dur dans le code de l'addon.** Un
nouveau paramètre naît avec sa fiche dans
`engine/gamb_engine/options/fiches/`, qui répond aux quatre questions qu'un
artiste se pose devant un curseur :

```yaml
mon_reglage:
  libelle: "Nom affiché"
  effet: "Ce que ça change, en une phrase"
  monter_quand: "..."
  baisser_quand: "..."
  cout: "VRAM, temps, ou négligeable"
  defaut: 42
```

Un test refuse tout paramètre de preset sans fiche. C'est volontairement
mécanique : la pédagogie ajoutée après coup ne l'est jamais.

### La vérification que le CI ne peut pas faire

Les tests ci-dessus couvrent chaque morceau isolément. Ils ne peuvent pas
vérifier que Blender, l'addon et le moteur se parlent — il n'existe pas de CI
avec un GPU NVIDIA et une installation de Blender.

Cette chaîne-là se vérifie à la main, en deux commandes. Le moteur d'abord :

```bash
gamb serve
```

Puis, dans un autre terminal :

```bash
blender --background --factory-startup --python scripts/verifier_dans_blender.py
```

Attendu : `RESULTAT: TOUT VERT`, précédé de la ligne exacte que le panneau
affiche — par exemple `online, VRAM 12.6 / 16.0 Go libres`.

C'est le critère d'acceptation de P1, rejouable à volonté.

---

## La règle qui casse le CI si on l'oublie

**`Gausian` prend un seul `s`, et le dépôt dit `Builder`.** Voir la
[table de nommage](README.md#table-de-nommage).

Toutes les valeurs de nom viennent de `naming.py`. **Aucune chaîne de nom en dur
ailleurs**, jamais, même « juste pour un test » :

```python
from gamb_engine import naming

bl_idname = naming.operator_id("start_training")   # ✅
bl_idname = "gamb.start_training"                  # ❌
```

### Le miroir

`naming.py` existe en deux exemplaires **identiques octet pour octet** :

```
engine/gamb_engine/naming.py
addon/gausian_and_mesh_builder/naming.py
```

L'addon ne peut pas importer depuis `engine/` — il tourne dans un autre
interpréteur, sans le package installé. D'où la duplication, et d'où le test
`test_les_deux_copies_sont_identiques_octet_pour_octet` qui compare les deux
fichiers et casse le CI à la moindre divergence.

**Pour modifier la table :** édite la copie moteur, puis recopie-la sur l'autre.
Ne les édite jamais séparément.

```bash
cp engine/gamb_engine/naming.py addon/gausian_and_mesh_builder/naming.py
```

Ce module **n'importe rien**, jamais — un test le vérifie aussi. Il est chargé
par l'addon Blender, qui n'a droit qu'à la bibliothèque standard.

---

## Licences

Chaque fichier source porte son en-tête SPDX **dès sa création** :

```python
# SPDX-License-Identifier: GPL-3.0-or-later    # sous addon/
# SPDX-License-Identifier: Apache-2.0          # sous engine/
```

La carte complète est dans [`LICENSING.md`](LICENSING.md). En résumé : `addon/`
est GPL-3 parce qu'un addon Blender lie l'API Blender, `engine/` est Apache-2.0
parce que le sidecar est un processus séparé qui ne lie rien.

**Toute nouvelle dépendance s'ajoute d'abord à [`LICENSES.md`](LICENSES.md)**,
avec sa licence lue **à la source primaire** — le fichier `LICENSE` du dépôt, le
champ de PyPI, le frontmatter de la fiche Hugging Face. Pas un blog, pas un
résumé, pas un souvenir. Une ligne `À VÉRIFIER` est acceptable ; une ligne
devinée ne l'est pas.

---

## Git

Le dépôt est manipulé depuis un **client graphique**. L'historique doit rester
lisible sans ligne de commande : pas de rebase interactif exotique, pas de
réécriture d'historique, des messages clairs.

### Branches

- `main` est protégée, et reste toujours dans un état où le CI est vert.
- **Une branche par phase** : `p1-sidecar`, `p2-ingest`, `p3-curation`, …
- Merge par **pull request**, même en solo. C'est ce qui donne un historique
  relisable — et exploitable comme documentation RS&DE.

### Commits

Une phrase à l'impératif, en français, qui dit *ce que fait* le commit :

```
Ajoute la table de nommage et ses gardes CI
Corrige le budget VRAM du preset Production
```

### Ce qui n'entre jamais dans le dépôt

**Ni checkpoints, ni PLY, ni images, ni HDRI — et pas de Git LFS non plus.** Le
dépôt ne contient que du code et de la config ; les artefacts vivent dans le
dossier projet sur disque décrit par `gamb.json`.

Ce n'est pas de la préciosité : un objet poussé reste dans l'historique de tous
les clones, pour toujours. Le [`.gitignore`](.gitignore) est écrit pour ça —
avant d'y ajouter une exception, demande-toi si le fichier ne devrait pas juste
vivre ailleurs.
