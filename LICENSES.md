# LICENSES.md

**Projet :** `GausianAndMeshBuilder_BlenderPlugIn`
**Date de vérification :** 2026-08-10
**Portée :** toutes les dépendances nommées dans la spec technique, plus les dépendances transitives découvertes en chemin.

---

## Méthode

126 composants vérifiés. Chaque ligne a été lue **à la source primaire** : fichier `LICENSE` brut du dépôt, onglet licence GitHub / API, champ `License` de PyPI, ou frontmatter de la fiche Hugging Face. Aucun blog, aucun résumé, aucune mémoire de modèle n'a servi de preuve. Six licences à fort enjeu ont subi une passe **adverse** dédiée (mission : réfuter la licence supposée). Deux de ces six réfutations ont abouti.

Une ligne marquée **`À VÉRIFIER`** signifie que la source primaire n'a pas pu être lue (dépôt gated, anti-bot, page inaccessible) — pas qu'elle est probablement bonne.

---

## Les deux questions à ne jamais confondre

L'audit sépare deux régimes qui n'ont ni le même déclencheur ni le même remède. Confondre les deux est l'erreur la plus coûteuse de ce dossier.

| | Déclencheur | Usage interne studio, sans distribution |
|---|---|---|
| **Clause non-commerciale** (INRIA, Magic Leap, PolyForm, CC-BY-NC, NVIDIA Source Code License, S-Lab) | **L'usage lui-même**, y compris interne sur un projet client payant | ❌ **Interdit** |
| **Copyleft** (GPL, LGPL, MPL) | **La distribution** hors de l'entité juridique | ✅ Autorisé, aucune obligation |
| **AGPL** (Ultralytics) | La distribution **et** l'usage réseau (§13) | ⚠️ Autorisé par le texte, mais l'éditeur revendique le contraire |

Autrement dit : si GAMB reste un outil interne jamais livré à un tiers, la moitié gauche du tableau des risques disparaît — la moitié droite, non.

---

## Légende

| Colonne | Valeurs |
|---|---|
| **Commercial** | `oui` = utilisable et redistribuable dans un produit commercial fermé · `conditionnel` = utilisable sous conditions explicitées · `non` = bloquant · `À VÉRIFIER` = non établi |
| **Conf.** | `confirmé` = texte de licence lu · `inféré` = preuve secondaire forte · `non vérifié` = bloqué |

Verdict établi pour l'hypothèse la plus exigeante : **produit commercial, code fermé, distribué à des tiers**. Si Q4 (§12) répond « usage interne uniquement, jamais distribué », relire la colonne Commercial à la lumière du tableau ci-dessus.

> **État de Q4 au 2026-08-10 : ouverte.** L'usage commercial n'est pas tranché, et un export vers un moteur de jeu est envisagé à terme — or **distribuer un jeu, même gratuitement, est une distribution à des tiers**, ce qui ramène précisément à l'hypothèse stricte retenue ci-dessus.
>
> En conséquence, la colonne Commercial se lit telle quelle, et toute méthode marquée `non` vit derrière le gate `commercial_mode` du moteur : elle n'est jamais le chemin par défaut, et un repli commercialement propre est implémenté en parallèle. Les deux endroits où cela coûte une double implémentation réelle sont la **curation** (P3) et le **relighting** (P9).
>
> Le jour où Q4 se ferme sur « jamais distribué », ce paragraphe saute et le catalogue non-commercial s'ouvre. Tant qu'elle est ouverte, on code pour le cas strict.

---

# A. Ce que l'audit invalide dans la spec

Sept points. Chacun casse une décision écrite dans la spec, pas un détail.

### A.1 — `pyiqa` / IQA-PyTorch est non-commercial. Le module de curation (§4) doit être redessiné.

La spec propose « un modèle NR-IQA local (MUSIQ / CLIP-IQA / TOPIQ via IQA-PyTorch) ». **Le dépôt IQA-PyTorch est sous PolyForm Noncommercial License 1.0.0**, et ses poids sont sur Hugging Face en CC-BY-NC-SA-4.0. Les trois métriques nommées sont bloquées d'un coup, et pas seulement à la distribution : PolyForm NC interdit l'usage. CLIP-IQA a en plus sa propre licence non-commerciale (S-Lab 1.0). Aucun dual-license commercial publié.

→ Chemin de repli : `BRISQUE`/`NIQE` via le module `quality` d'opencv-contrib (Apache-2.0), ou réimplémentation interne depuis les papiers.

### A.2 — `ultralytics` est AGPL-3.0. La voie d'intégration SAM 3 de la spec est inutilisable.

La spec recommande « SAM 3 intégré au package Ultralytics depuis la version 8.3.237 — chemin d'intégration le plus court ». C'est le plus court **et le plus cher** : AGPL-3.0 sur le paquet, **plus** `ultralytics-thop` (dépendance obligatoire, AGPL-3.0 aussi, second saut que personne ne voit). L'éditeur revendique publiquement qu'une Enterprise License payante est requise même pour des « internal business tools or private company applications ». Tarif non public.

→ **Appeler `facebookresearch/sam3` directement.** Sa licence Meta est bien moins invasive, et l'Enterprise Ultralytics n'apporterait de toute façon rien sur les poids, qui restent chez Meta derrière leur gate.

### A.3 — SAM 3 n'est pas open source. Utilisable commercialement, mais pas librement.

La spec écrit « SAM 3 est open source ». **Faux, et la réfutation est nette** : la SAM License n'est pas sur la liste OSI, GitHub retourne `NOASSERTION`, Hugging Face tague `license: other`. Elle échoue l'Open Source Definition §6 (discrimination par domaine d'usage) via les interdits ITAR/militaire.

**La bonne nouvelle** : le mot « commercial » n'apparaît pas une seule fois dans les 62 lignes de la licence. Aucune clause non-commerciale, aucun seuil d'utilisateurs façon Llama, aucune AUP incorporée par référence. L'usage commercial est permis.

Terme correct dans la doc : **source-available / weights-available**, jamais « open source ».

### A.4 — La cible Blender de la spec est périmée, et la version Python n'est vraie que pour 5.1.

Blender 5.1 est bien sorti (17 mars 2026) et embarque bien Python 3.13 — la spec a raison sur ce point précis. Mais 5.1 est **hors support depuis juillet 2026**. Le courant est **5.2 LTS** (14 juillet 2026, supporté jusqu'en juillet 2028), lui aussi en Python 3.13. Attention : **Blender 5.0 est en Python 3.11** — un manifeste avec `blender_version_min = "5.0.0"` embarquant des wheels `cp313` est cassé.

→ Cibler **5.2 LTS**, `blender_version_min = "5.1.0"` au plus bas.

### A.5 — Blender n'est pas GPL-3. C'est GPL-2.0-or-later aux sources.

La spec dit « `LICENSE` : GPL-3.0. Ce n'est pas un choix, c'est une conséquence ». La conséquence est réelle, la version est fausse : le `COPYING` de Blender pointe la **GPL version 2**, et les en-têtes SPDX du code disent `GPL-2.0-or-later`. Seul le **binaire redistribué** est GPL-3.0-or-later.

Ça ne change pas la conclusion pour l'addon (`GPL-3.0-or-later` reste le bon choix, c'est ce qu'exige extensions.blender.org et ce que met le template officiel), mais ça change la formulation dans le README — et ça compte si quelqu'un argumente un jour sur la compatibilité Apache-2.0.

### A.6 — L'addon KIRI a trois licences contradictoires. Ne pas en copier une ligne.

Réfutation aboutie. Le dépôt affirme **trois licences incompatibles** :

| Fichier | Déclaration |
|---|---|
| `/LICENSE` | Apache-2.0 (ajouté au commit initial 2024-09-27, jamais modifié depuis) |
| `blender_manifest.toml` | `license = [ "SPDX:GPL-2.0-or-later" ]` — c'est **ce qui ship réellement** dans l'extension |
| `__init__.py` | En-tête GPL v3 « or (at your option) any later version » |

Le badge « Apache-2.0 » de GitHub est auto-détecté depuis `/LICENSE` seul — il ne lit ni le manifeste ni les en-têtes. C'est exactement de là que vient l'affirmation de la spec.

**Règle du plus strict** → traiter comme **GPL-3.0-or-later**. Aucune de ces lectures n'interdit l'usage commercial ; le risque est la **portée du copyleft**. Reprendre ses Geometry Nodes ou son Python dans GAMB est bloqué sous deux des trois lectures.

→ Interop à distance par fichier (`.ply` sur disque) uniquement. Ce qui est de toute façon la recommandation Q5.

### A.7 — Quasi toute la §2.5 (mesh) et la §2.6 (relighting) est non-commerciale.

Ce n'est pas une surprise ponctuelle, c'est **systémique** : la lignée INRIA contamine presque tout le domaine.

| Méthode citée dans la spec | Licence réelle | Commercial |
|---|---|---|
| 2DGS | Gaussian-Splatting License (INRIA/MPII) | ❌ |
| GOF | Gaussian-Splatting License | ❌ |
| MILo | Gaussian-Splatting License **+** nvdiffrast (NVIDIA SCL) | ❌❌ |
| PGSR | Licence académique ZJU custom, **plus stricte qu'INRIA** (« toute modification doit être open-source et interdite au commercial ») | ❌ |
| GausSurf | MIT déclarée — **mais le code n'est pas publié** (« coming soon ») | ⚠️ |
| GS-2M | Gaussian-Splatting License **+** hérite de PGSR | ❌❌ |
| Relightable 3D Gaussians | Gaussian-Splatting License | ❌ |
| GS-IR | `/LICENSE` = MIT **au nom de Mark Kellogg, un tiers sans rapport** ; les sources portent l'en-tête INRIA | ❌ |
| GI-GS | `/LICENSE` = MIT ; noyau 3DGS vendorisé = INRIA ; **+** nvdiffrast | ❌❌ |
| GeoSplatting | **Apache-2.0, et bâti sur gsplat, pas sur INRIA** — seul survivant de la famille | ⚠️ conditionnel |
| MaterialClusterGS | Papier seul, **aucun code publié** | ❌ |

**GeoSplatting est la seule porte de sortie du relighting**, et seulement si on lui retire `nvdiffrast`.

---

# B. Tableaux par famille

## B.1 — Trainers et rastériseurs (§2.1–2.3)

| Composant | Version | Licence | Commercial | Conf. |
|---|---|---|---|---|
| **gsplat** (nerfstudio-project) | v1.5.3 / main | Apache-2.0 | **oui** ⚠️1 | confirmé |
| nerfstudio | 1.1.5 | Apache-2.0 | oui ⚠️2 | confirmé |
| **Brush** (ArthurBrussee) | 0.3.0 | Apache-2.0 | **oui** | confirmé |
| spirulae-splat | master | GPL-3.0 | conditionnel ⚠️3 | confirmé |
| LichtFeld Studio | master | GPL-3.0 | conditionnel ⚠️4 | confirmé |
| **gaussian-splatting (INRIA)** | main | Gaussian-Splatting License | **non** | confirmé |
| **diff-gaussian-rasterization** + forks | main | Gaussian-Splatting License | **non** ⚠️5 | confirmé |
| 3dgrut / 3DGUT (NVIDIA nv-tlabs) | main | Apache-2.0 | conditionnel ⚠️6 | confirmé |
| plyfile | 1.1.5 | **GPL-3.0-or-later** | conditionnel ⚠️7 | confirmé |
| tiny-cuda-nn (NVlabs) | master | BSD-3-Clause | oui | confirmé |
| glm (g-truc) | submodule gsplat | Happy Bunny **OU** MIT | oui ⚠️E1 | confirmé |
| GoogleTest | submodule gsplat | BSD-3-Clause | oui (test only) | confirmé |
| PPISP (nv-tlabs) | 1.2.1 | Apache-2.0 | oui | confirmé |
| fused-ssim | commit épinglé | MIT | oui | confirmé |
| fused-bilagrid | commit épinglé | MIT | oui | confirmé |
| nerfview | commit épinglé | Apache-2.0 | oui | confirmé |
| nvidia-ncore | 19.5.1 | Apache-2.0 | oui | confirmé |
| simple-knn (Inria) | — | **À VÉRIFIER** ⚠️V1 | non | non vérifié |

**⚠️1 — gsplat : la revendication survit, avec deux chausse-trappes réelles.** La passe adverse a tout tenté : recherche exhaustive de fichiers de licence (un seul, `./LICENSE`), extraction des 392 tags SPDX du dépôt (100 % `Apache-2.0`, zéro exception), grep INRIA/graphdeco/non-commercial sur tout l'arbre, historique du fichier LICENSE (2 commits, aucun changement de type), vérification des contributions NVIDIA (`SPDX-License-Identifier: Apache-2.0`). C'est une réimplémentation indépendante, pas un dérivé INRIA.

**Mais** : `gsplat` **exporte publiquement** `rasterization_inria_wrapper` et `rasterization_2dgs_inria_wrapper` depuis son `__init__.py`. Ces fonctions importent `diff_gaussian_rasterization` paresseusement, dans le corps de la fonction. Le paquet n'est **pas** une dépendance déclarée, donc jamais installé — mais si du code GAMB appelle ces symboles, la licence recherche INRIA entre par la porte de service. **À interdire en CI.** Second point : `examples/download_3dgs_paper_scenes.py` télécharge les scènes pré-entraînées d'INRIA, qui sont sous les mêmes termes recherche.

**⚠️2 — nerfstudio** est un hôte de plugins. Son Apache-2.0 ne blanchit aucun plugin tiers ni aucun rastériseur INRIA qu'on brancherait dedans.

**⚠️3 / ⚠️4 — spirulae-splat et LichtFeld Studio, GPL-3.0.** Usage interne studio sans distribution : aucune obligation. Bundlé ou importé dans un produit distribué : le produit entier devient GPL-3.0. Aucun dual-license offert. `spirulae-splat` est la piste « training en linéaire » de la spec §2.2 — **cette piste est donc réservée à l'usage interne**, sauf accord écrit de l'auteur. Sur LichtFeld : son `THIRD_PARTY_LICENSES.md` liste le 3DGS d'INRIA en « Custom » sans dire si du code est réellement vendorisé — si oui, la relicence GPL-3 serait invalide et l'INRIA gouvernerait. Question ouverte à poser au mainteneur.

**⚠️5 — La règle pratique la plus importante du dossier.** Si `import diff_gaussian_rasterization` peut réussir dans l'environnement livré, le produit n'est pas distribuable. Les forks héritent : la copie `ashawkey` a été ouverte indépendamment, même licence, même interdiction.

**⚠️6 — 3dgrut** : le code NVIDIA est propre (Apache-2.0, aucun avenant NVIDIA). Le blocage vient de son `pyproject.toml`, qui déclare **`plyfile` en dépendance dure** — GPL-3.0-or-later. Retirer ou remplacer `plyfile` avant de livrer.

**⚠️7 — `plyfile` est la contamination GPL la plus probable de tout le sidecar**, et elle se cache derrière un projet Apache-2.0. Le layout PLY 3DGS est trivial : écrire son propre lecteur/écrivain coûte moins cher que la conformité.

## B.2 — SfM et poses, piste A (§2.4)

| Composant | Version | Licence | Commercial | Conf. |
|---|---|---|---|---|
| **pycolmap** (wheel PyPI officielle) | 4.1.1 | BSD-3-Clause | **oui** ⚠️8 | confirmé |
| COLMAP (build source par défaut) | 4.1.1 | BSD-3-Clause **+ deps** | conditionnel ⚠️9 | confirmé |
| GLOMAP | archivé 2026-03-09 | BSD-3-Clause | oui ⚠️10 | confirmé |
| **LSD** (transitif, bundlé COLMAP) | vendorisé | **AGPL-3.0-or-later** | **non** ⚠️9 | confirmé |
| **SiftGPU** (transitif, bundlé COLMAP) | vendorisé | Licence académique UNC | **non** ⚠️9 | confirmé |
| PoseLib | — | BSD-3-Clause | oui | confirmé |
| VLFeat / PoissonRecon / faiss | bundlés COLMAP | BSD-2 / MIT / MIT | oui | confirmé |
| hloc | master | Apache-2.0 | conditionnel ⚠️11 | confirmé |
| **SuperGlue** (Magic Leap) | master | Noncommercial Research Use Only | **non** ⚠️12 | confirmé |
| **SuperPoint** (Magic Leap) | master | Noncommercial Research Use Only | **non** ⚠️12 | confirmé |
| LightGlue | v0.2 | Apache-2.0 (code **et** poids) | conditionnel ⚠️13 | confirmé |
| R2D2 (transitif, submodule hloc) | master | CC BY-NC-SA 3.0 | **non** | confirmé |
| d2-net (submodule hloc) | — | Clear BSD | oui | confirmé |
| deep-image-retrieval (submodule hloc) | — | BSD-3-Clause | oui | confirmé |
| Pixel-Perfect-SfM | main | Apache-2.0 | conditionnel ⚠️14 | confirmé |
| S2DNet (transitif pixsfm) | master | MIT (code) / poids non déclarés | conditionnel ⚠️V2 | confirmé |

**⚠️8 — La wheel `pycolmap` officielle est propre, et c'est vérifié empiriquement, pas supposé.** Les scripts CI amont compilent avec `-DLSD_ENABLED=OFF -DGUI_ENABLED=OFF -DCUDA_ENABLED=OFF`. La wheel `cp312-win_amd64` a été téléchargée et le binaire `_core.pyd` scanné : **0 occurrence** de « LSD », « Affero », « AGPL ». La seule occurrence de « SiftGPU » est une chaîne de message d'erreur. → **Passer par `pycolmap` PyPI, jamais par un COLMAP recompilé maison.**

**⚠️9 — Le piège COLMAP, et il est sévère.** Le `COPYING.txt` prévient lui-même : « this text refers only to the license for COLMAP itself, independent of its dependencies ». Deux composants entrent **par défaut** :
- `LSD` : **AGPL-3.0-or-later**, `option(LSD_ENABLED ... ON)` — ON par défaut.
- `SiftGPU` : licence UNC limitée à « educational, research and non-profit », activée dès que `CUDA_ENABLED` ou `OPENGL_ENABLED` (les deux par défaut).

Et `.github/workflows/build-windows.yml` ne surcharge rien → **les `colmap.exe` officiels de la page Releases contiennent du code AGPL et du code non-commercial.** Ne jamais redistribuer le binaire COLMAP officiel dans le produit.

**⚠️10 — GLOMAP est archivé** (2026-03-09, lecture seule) et migré dans COLMAP comme option de mapper `global`. Basculer dessus, c'est retomber dans les caveats de build COLMAP ci-dessus.

**⚠️11 — hloc est une coquille Apache-2.0 sur des modèles non-commerciaux.** Son `.gitmodules` tire SuperGlue+SuperPoint et R2D2 par `git submodule update --init --recursive` — la commande d'install recommandée. `hloc/extractors/superpoint.py` importe directement depuis `third_party/SuperGluePretrainedNetwork`. Utilisable en commercial **uniquement** avec DISK / ALIKED / SIFT + LightGlue, et sans tirer ces sous-modules.

**⚠️12 — Rejet franc.** Licence propriétaire Magic Leap : « PERMITTED USES: The Software may be used for your own noncommercial internal research purposes », interdiction de revente/sous-licence/transfert, **toute modification que vous écrivez devient propriété de Magic Leap**, et clause de confidentialité perpétuelle. Code **et** poids. Aucune option commerciale offerte.

**⚠️13 — LightGlue est le rare dépôt honnête** : son README documente lui-même le split. Poids LightGlue = Apache-2.0 (cas favorable). Mais l'extracteur pilote la licence effective : LightGlue+DISK ✅, +ALIKED ✅, +SIFT ✅, **+SuperPoint ❌** — et SuperPoint est le pairing par défaut de tous les tutoriels. `lightglue/superpoint.py` porte le bandeau « Magic Leap CONFIDENTIAL … STRICTLY PROHIBITED ». → Forcer l'extracteur en config, ne pas expédier ce fichier ni `superpoint_lightglue.pth`.

**⚠️14 — pixsfm** : code Apache-2.0 propre, mais sa chaîne d'exécution documentée impose un COLMAP buildé source (⚠️9), passe par hloc en config SuperPoint par défaut (⚠️11), et télécharge les poids S2DNet depuis une URL Dropbox sans licence attachée.

## B.3 — Modèles 3D feed-forward, piste B (§2.4)

| Composant | Version | Licence | Commercial | Conf. |
|---|---|---|---|---|
| VGGT — **code** | main ≥ a1179fe (2025-07-29) | VGGT License v1 (Meta) | conditionnel ⚠️15 | confirmé |
| VGGT — code **avant** 2025-07-29 | ≤ 2025-07-28 | CC-BY-NC-4.0 | **non** ⚠️15 | confirmé |
| VGGT-1B — **poids par défaut** | HF `facebook/VGGT-1B` | **CC-BY-NC-4.0** | **non** ⚠️15 | confirmé |
| VGGT-1B-**Commercial** — poids | HF, gated | `vggt-aup-license` | conditionnel ⚠️V3 | inféré |
| **VGGT-X** | main | **CC-BY-NC-4.0** | **non** ⚠️16 | confirmé |
| Pi3 / pi-cubed | main | code BSD-3 / **poids CC-BY-NC-4.0** | **non** ⚠️17 | confirmé |
| MapAnything — code | main | Apache-2.0 | oui | confirmé |
| MapAnything — poids `-apache` | HF `map-anything-apache` | **Apache-2.0** | **oui** ⚠️18 | confirmé |
| MapAnything — poids par défaut | HF `map-anything` | CC-BY-NC-4.0 | **non** ⚠️18 | confirmé |
| 3R-GS | main | **aucun fichier de licence** | **non** ⚠️19 | confirmé |
| DUSt3R | main | CC-BY-NC-SA-4.0 | **non** | confirmé |
| MASt3R | main | CC-BY-NC-SA-4.0 | **non** ⚠️20 | confirmé |
| DINOv2 (transitif, encodeur de VGGT/Pi3) | main | Apache-2.0 (code **et** poids) | **oui** ⚠️21 | confirmé |

**⚠️15 — Le piège VGGT : code et poids ont divergé, et le checkpoint par défaut est le mauvais.** Le code a été relicencié le 2025-07-29 (README verbatim : « We've updated the license for VGGT to permit commercial use… **only the newly released checkpoint VGGT-1B-Commercial is licensed for commercial usage — the original checkpoint remains non-commercial** »). Donc : **utiliser `facebook/VGGT-1B` dans un outil studio commercial est une violation.** Et tout dépôt qui a vendorisé VGGT avant le 2025-07-29 porte l'ancienne licence CC-BY-NC. → Épingler l'id du checkpoint et **ajouter un assert CI que `VGGT-1B` n'est jamais téléchargé**.

**⚠️16 — VGGT-X : réfutation aboutie.** La spec le cite comme la voie rapide de la piste B. Son `LICENSE.txt` est le texte complet CC-BY-NC-4.0. GitHub affiche `NOASSERTION`, donc **aucun scanner ne préviendra**. Pas de dual-license, pas de clause « contact for commercial ». Et même en négociant, il faudrait aussi clarifier MASt3R, qu'il cite en dépendance.

**⚠️17 — Pi3 : conflit de sources réel.** Le README GitHub affiche un tableau « Model Weights | CC BY-NC 4.0 | **Strictly Non-Commercial** » avec une justification par la provenance des datasets d'entraînement ; la fiche HF `yyfz233/Pi3` déclare `license: bsd-2-clause`. Deux sources primaires se contredisent. Règle du plus strict → `non`. Les deux lectures bloquent de toute façon : la version BSD-2 dit « For commercial use, please contact the authors ».

**⚠️18 — MapAnything a la meilleure histoire commerciale de la famille — mais le défaut est piégé.** Deux variantes de poids, et le README dit explicitement « For Commercial Use: Use `facebook/map-anything-apache` ». **Danger** : le quick-start du README appelle `MapAnything.from_pretrained("facebook/map-anything")` — le checkpoint **non-commercial** est le copier-coller par défaut, la variante Apache reléguée en commentaire. Quiconque copie l'exemple livre un modèle NC. → Coder l'id `-apache` en dur, refuser tout id fourni par l'utilisateur. Aucun gate, contrairement à VGGT.

**⚠️19 — 3R-GS n'a aucun fichier de licence.** Vérifié trois fois : `LICENSE`/`LICENSE.md`/`LICENSE.txt` en 404, `"license": null` via l'API GitHub, aucune section License dans le README. Absence de concession = tous droits réservés. Publier sur GitHub ne concède que le droit de fork/consultation des ToS, pas un droit d'usage. Et même s'ils ajoutaient un MIT demain, 3R-GS consomme des sorties MASt3R-SfM (CC-BY-NC-SA).

**⚠️20 — MASt3R est le contaminant commun** derrière VGGT-X et 3R-GS. Même les **sorties précalculées** (poses, nuages dérivés) sont discutablement des adaptations sous CC-BY-NC-SA — livrer des poses dérivées de MASt3R dans un produit payant n'est pas un contournement sûr.

**⚠️21 — DINOv2 : le piège historique, aujourd'hui désamorcé.** Publié en CC-BY-NC-4.0 en avril 2023, relicencié Apache-2.0 le 2023-08-31 (commit « Update license everywhere (#182) »). C'est ce qui a rendu possible `VGGT-1B-Commercial`. **Attention** : si un fork ou des poids ont été copiés **avant** cette date, la copie locale est encore CC-BY-NC. Et ne jamais tirer les variantes `Cell-DINO` / `X-RAY DINO` du même dépôt, qui sont sous FAIR Noncommercial Research License.

## B.4 — Segmentation (§2.7)

| Composant | Version | Licence | Commercial | Conf. |
|---|---|---|---|---|
| **SAM 3** — code | main | SAM License (Meta, non-OSI) | conditionnel ⚠️22 | confirmé |
| SAM 3 — poids | HF `facebook/sam3`, gated | SAM License | conditionnel ⚠️23 | inféré |
| SAM 3.1 Object Multiplex | HF `facebook/sam3.1`, gated, 2026-03-27 | SAM License (code) / poids **À VÉRIFIER** | conditionnel ⚠️V4 | inféré |
| **SAM 2** | main | **Apache-2.0** (code **et** poids, sans gate) | **oui** ⚠️24 | confirmé |
| **ultralytics** | 8.3.237 → 8.4.117 | **AGPL-3.0** | **non** ⚠️A2 | confirmé |
| **ultralytics-thop** (transitif obligatoire) | 2.1.6 | **AGPL-3.0** | **non** ⚠️A2 | confirmé |

**⚠️22 — SAM 3, conditions à intégrer au contrat.** Code et poids sont sous **la même** licence (la définition de « SAM Materials » englobe explicitement « trained model weights »). Aucune clause commerciale restrictive. Ce qui rend la ligne `conditionnel` :
- **§1.b.i, propagation** : si vous livrez l'addon ou le sidecar contenant du SAM Material ou un dérivé à un tiers (client, autre studio), vous ne pouvez le faire que sous ce même accord, et vous devez en joindre une copie. C'est un copyleft faible sur la portion SAM — ça n'infecte pas votre code, contrairement à la GPL.
- **§8, modification unilatérale** : Meta peut modifier l'accord à tout moment, « effective immediately », et l'usage continu vaut acceptation. Un pipeline de production est exposé à un changement de termes sous ses pieds.
- **§6** : résiliation sur violation, avec obligation de suppression. **§5.b** : rétorsion brevets + indemnisation large de Meta. **§7** : juridiction exclusive de Californie. Concession **non transférable** — pertinent en cas de cession ou d'acquisition du studio.

**⚠️23 — SAM 3, réalité opérationnelle du gate.** Les poids sont en approbation **manuelle** Meta. Le formulaire collecte nom, date de naissance, pays, affiliation, intitulé de poste, géo/IP. Conséquences concrètes : Meta peut refuser ou révoquer un compte ; **un runner CI non authentifié ou un poste artiste neuf ne peut pas télécharger le checkpoint** ; et mirrorer le `.pt` en interne pour contourner le gate est un événement de redistribution qui déclenche §1.b.i. → Accepter le gate sous **identité d'entreprise**, jamais personnelle.

**⚠️24 — SAM 2 est le plan de repli propre** si le juridique refuse la licence Meta custom : Apache-2.0 sur le code **et** les poids, aucun gate, téléchargement direct. Moins performant, mais sans aucune des sept conditions ci-dessus.

## B.5 — Curation d'images (§4)

| Composant | Version | Licence | Commercial | Conf. |
|---|---|---|---|---|
| **IQA-PyTorch / pyiqa** | 0.1.16 | **PolyForm Noncommercial 1.0.0** + S-Lab 1.0 | **non** ⚠️A1 | confirmé |
| **CLIP-IQA** | master | **S-Lab License 1.0** | **non** | confirmé |
| **TOPIQ** | via pyiqa | PolyForm NC / poids CC-BY-NC-SA-4.0 | **non** | confirmé |
| **IQA-PyTorch-Weights** (HF, transitif) | — | **CC-BY-NC-SA-4.0** | **non** ⚠️25 | confirmé |
| MUSIQ (google-research) | master | Apache-2.0 (code) / **poids non déclarés** | À VÉRIFIER ⚠️V5 | non vérifié |
| OpenAI CLIP | main | MIT (code) / **poids non déclarés** | À VÉRIFIER ⚠️V6 | non vérifié |
| DINOv2 | main | Apache-2.0 (code et poids) | **oui** | confirmé |
| DINOv3 | LICENSE.md 2025-08-19 | DINOv3 License (Meta, non-OSI) | conditionnel ⚠️26 | confirmé |
| opencv-python | 5.0.0.93 | MIT (scripts) + Apache-2.0 (OpenCV) | conditionnel ⚠️27 | confirmé |
| opencv-contrib-python | 5.0.0.93 | idem | conditionnel ⚠️27 ⚠️28 | confirmé |
| FFmpeg + Qt5 (transitifs, wheels OpenCV) | — | **LGPL-2.1 / LGPL-3.0** | conditionnel ⚠️27 | confirmé |
| scikit-image | 0.26.0 | BSD-3-Clause (+BSD-2, MIT) | **oui** | confirmé |
| scipy | 1.18.0 | BSD-3-Clause | **oui** | confirmé |

**⚠️25 — La surprise transitive la plus vicieuse de la famille.** Même en croyant n'utiliser « que le code » d'une métrique, `pyiqa` télécharge ses poids depuis ce dépôt HF au premier appel, déclaré `cc-by-nc-sa-4.0`. Double verrou : NC bloque l'usage, SA contaminerait tout fine-tuning interne. Le dépôt précise en outre que certains poids traînent **en plus** la licence de leur repo d'origine — CC-BY-NC-SA-4.0 est un plancher, pas un plafond. → Bloquer tout téléchargement depuis ce dépôt dans le sidecar de prod, et **traiter tout cache local de ces poids comme un contaminant à purger**.

**⚠️26 — DINOv3 n'est pas non-commercial**, contrairement à l'intuition. Le texte a été lu intégralement : concession « non-exclusive, worldwide, non-transferable and royalty-free », les mots « commercial », « non-commercial », « research only » sont **absents**. Trois obligations à budgéter : mention **« Built with DINOv3 »** visible sur le site / l'UI / la doc produit ; redistribution sous cette même licence avec copie jointe ; poids gated (accepter sous identité d'entreprise, pas de mirroring public).

**⚠️27 — OpenCV : le cœur est sain, les wheels le sont moins.** Apache-2.0 + MIT côté code. Mais les wheels redistribuées embarquent **FFmpeg (LGPL-2.1, dans tous les packages)** et **Qt 5 (LGPL-3.0, wheels Linux non-headless et macOS)**. Tant qu'on se contente d'un `pip install` à l'exécution, rien ne se déclenche. Dès qu'on redistribue l'addon **avec** les wheels — cas très probable — il faut fournir les textes LGPL, indiquer où obtenir les sources, et permettre le relink. → **Mitigation en une ligne : utiliser `opencv-python-headless`**, ce qui élimine Qt5/LGPL-3.0. Un sidecar sans GUI n'a pas besoin de `highgui`.

**⚠️28 — opencv-contrib** : la wheel PyPI est propre, SURF/xfeatures2d non-free en sont **absents** par construction, et SIFT est inclus (brevet expiré). Le piège est le flag CMake `OPENCV_ENABLE_NONFREE=ON` sur une recompilation maison, qui réintroduirait du code breveté hors couverture Apache-2.0. → À interdire dans les scripts de build.

## B.6 — Chaîne RAW / DNG (§4)

| Composant | Version | Licence | Commercial | Conf. |
|---|---|---|---|---|
| **rawpy** | 0.27.0 | MIT | **oui** ⚠️29 | confirmé |
| **LibRaw** (statique dans la wheel) | 0.22.1 / 0.22.2 | **LGPL-2.1 OU CDDL-1.0** (au choix) | conditionnel ⚠️E2 | confirmé |
| LibRaw-demosaic-pack-GPL2 / GPL3 | submodules rawpy | GPL-2.0 / GPL-3.0 | **non** ⚠️30 | confirmé |
| lcms2 (transitif, wheel rawpy) | 2.11 | MIT | oui ⚠️31 | confirmé |
| libgomp (transitif, wheels Linux rawpy) | 8.5.0 | GPL-3.0+ **WITH** GCC-exception-3.1 | conditionnel ⚠️31 | confirmé |
| darktable | 5.6.0 (2026-06-21) | GPL-3.0-or-later | conditionnel ⚠️32 | confirmé |
| darktable-ai / RawNIND UtNet2 (poids) | release-5.6.0 | GPL-3.0 **ou** CC-BY-4.0 | conditionnel ⚠️E3 | confirmé |
| tifffile | 2026.7.31 | BSD-3-Clause | **oui** ⚠️33 | confirmé |
| imageio | 2.37.4 | BSD-2-Clause | **oui** | confirmé |
| imageio-freeimage | optionnel | FIPL **ou** GPL-2.0 **ou** GPL-3.0 | conditionnel ⚠️34 | confirmé |
| colour-science | 0.4.7 | BSD-3-Clause | **oui** | confirmé |
| ExifTool | 13.59 | Perl Artistic **OU** GPL | conditionnel ⚠️E4 | confirmé |

**⚠️29 — rawpy : la revendication tient à moitié.** Le code Python est bien MIT. Mais la wheel binaire **embarque LibRaw en statique**, qui n'est pas MIT — le dépôt livre un second fichier `LICENSE.LibRaw` contenant la LGPL-2.1. Livrer une wheel rawpy dans un produit studio, c'est livrer LibRaw et hériter de ses obligations. Bonne nouvelle : les packs de dématriçage GPL ne sont **pas** compilés dans les wheels PyPI (vérifié : `no` sur toutes les plateformes).

**⚠️30 — Risque opérationnel concret.** Ces deux dépôts **sont** déclarés comme submodules dans le `.gitmodules` de rawpy, donc `git submodule update --init` les clone. Ils ne sont pas compilés par défaut (`RAWPY_BUILD_GPL_CODE=1` requis), mais un ingénieur qui recompile rawpy pour gagner en qualité de dématriçage produit un binaire GPL-2/3 qui contamine le produit fermé. → À interdire dans le script de build et **à vérifier en CI**.

**⚠️31 — Deux notices manquantes dans la wheel rawpy.** Aucun texte de licence lcms2 n'est présent (la wheel ne contient que `LICENSE` et `LICENSE.LibRaw`) : le studio doit ajouter lui-même la notice MIT de Little CMS. Et sur Linux, `auditwheel` injecte `libgomp` (GPL-3.0+ with GCC exception) **sans son texte de licence** — redistribuer la wheel Linux telle quelle, c'est redistribuer un binaire GPLv3+ sans son avis. Sans objet si le sidecar est Windows-only.

**⚠️32 — darktable : l'usage est libre, la distribution ne l'est pas.** La GPL restreint la distribution, pas l'usage, et les DNG produits sont votre travail, pas une œuvre dérivée. → Le documenter comme **prérequis externe installé par l'utilisateur**, ne jamais le bundler.
**Sur l'« AI Raw Denoise » de la 5.6, deux nuances que la spec ne mentionne pas** : il exige un build avec `-DUSE_AI=ON` (**OFF par défaut** — les binaires officiels ne l'ont peut-être pas compilé) et il est désactivé par défaut dans les préférences. Il est scriptable via la nouvelle API Lua `darktable.ai`, travaille bien avant dématriçage et écrit un DNG — ce qui colle à la chaîne. Mais **aucune source primaire n'atteste qu'il soit exposé dans `darktable-cli`** : si un denoise headless est requis, c'est à tester avant de compter dessus.

**⚠️33 — tifffile est la bonne façon de lire des tags DNG** sans toucher à du copyleft : DNG est une variante de TIFF, et tifffile est BSD-3 pur.

**⚠️34 — `imageio-freeimage` a été volontairement séparé du cœur pour raison de licence** (les mainteneurs le disent dans le README). Une chaîne rawpy + tifffile + imageio core n'en a aucun besoin. → **Ne pas l'installer.**

## B.7 — Extraction de mesh (§2.5)

| Composant | Licence | Commercial | Conf. |
|---|---|---|---|
| **2DGS** | Gaussian-Splatting License | **non** | confirmé |
| **diff-surfel-rasterization** (transitif 2DGS) | Gaussian-Splatting License | **non** ⚠️35 | confirmé |
| **GOF** | Gaussian-Splatting License (+ CGAL GPL-3.0) | **non** | confirmé |
| **MILo** | Gaussian-Splatting License **+** nvdiffrast | **non** | confirmé |
| **PGSR** | Licence académique ZJU custom | **non** ⚠️36 | confirmé |
| GausSurf | MIT déclarée — **aucun code publié** | À VÉRIFIER ⚠️37 | confirmé |
| **GS-2M** | Gaussian-Splatting License **+** PGSR | **non** ⚠️38 | confirmé |
| **nvdiffrast** (transitif) | NVIDIA Source Code License (1-Way Commercial) | **non** ⚠️39 | confirmé |
| StableNormal | Apache-2.0 déclarée (code et poids) | conditionnel ⚠️V7 | confirmé |
| **Open3D** | MIT | **oui** | confirmé |
| **trimesh** | MIT | **oui** ⚠️40 | confirmé |
| **xatlas** (+ bindings Python) | MIT | **oui** | confirmé |
| libigl | MPL-2.0 **+ sous-dossiers GPL/LGPL/AGPL** | conditionnel ⚠️41 | confirmé |
| PyMeshLab | GPL-3.0 | conditionnel ⚠️42 | confirmé |
| MeshLab | GPL-3.0 (+ Qt LGPL/GPL) | conditionnel ⚠️42 | confirmé |

**⚠️35 — Remplacer le Python de 2DGS par le sien ne suffit pas** : ce sont les kernels CUDA qui sont la partie licenciée.

**⚠️36 — PGSR est plus strict qu'INRIA, pas équivalent.** Clause virale absente du texte INRIA : « Any modification based on this work must be **open-source** and prohibited for commercial use. » Une exception négociée devrait donc couvrir **deux** obligations, pas une. Contact : zhangguofeng@zju.edu.cn.

**⚠️37 — GS-2M et GausSurf : deux vérifications d'existence, deux résultats opposés.** GS-2M **existe et le code est publié** (arXiv 2509.22276, CGF DOI 10.1111/cgf.70347, ~113 commits, `train.py`/`render.py`/`pbr/` présents) — mais sous licence INRIA, plus l'héritage PGSR. GausSurf, à l'inverse, **n'a pas de code** : le dépôt ne contient que `data/`, `LICENSE` et un README « Code is coming soon… ». Son MIT ne couvre donc rien, et il est peu probable qu'il survive à la publication vu que tous ses comparables ont dû relicencier en INRIA. → **Ne pas planifier la spec autour de GausSurf.**

**⚠️38 — Le mode « Material (R&D) » de la spec (GS-2M) est bloqué deux fois** : INRIA **et** ZJU. Une clearance commerciale exigerait les deux.

**⚠️39 — nvdiffrast est la surprise transitive du domaine mesh**, parce que c'est une dépendance de build, pas un composant en vue. §3.3 verbatim : « The Work and any derivative works thereof only may be used or intended for use **non-commercially**. » Le « 1-Way » est délibéré : NVIDIA garde les droits commerciaux, pas vous. Aucun chemin d'upgrade publié.

**⚠️40 — trimesh core est MIT, ses extras ne le sont pas.** `trimesh[all]` peut tirer des backends aux termes plus lourds (Blender et OpenSCAD invoqués en binaires externes pour les booléens, helpers CGAL). → Épingler un jeu d'extras minimal ; ne pas laisser une ligne « trimesh is MIT » couvrir les extras.

**⚠️41 — libigl : ne jamais écrire « libigl est MPL-2.0 » sans le qualificatif.** GitHub reporte **à la fois** GPL-3.0 et MPL-2.0. Les fichiers directement sous `include/igl` sont MPL-2.0 (copyleft au fichier, compatible avec un produit fermé). Mais `include/igl/copyleft/` contient du GPL/LGPL/AGPL — et c'est précisément là que vivent **les booléens de mesh (`copyleft/cgal`) et la tétraédrisation (`copyleft/tetgen`)**, exactement les opérations qu'un pipeline d'extraction va chercher. → Ajouter un check CI qui grep `igl/copyleft` dans le graphe d'inclusion.

**⚠️42 — PyMeshLab / MeshLab, avec une nuance Blender intéressante.** GPL-3.0 permet l'usage et même la vente commerciale, donc `conditionnel`, pas `non`. Mais un produit distribué qui `import pymeshlab` doit offrir ses sources en GPL-3.0. **Le côté addon Blender est déjà en territoire GPL** — PyMeshLab y est donc tolérable ; c'est le **sidecar fermé** qui est en risque. Si les filtres MeshLab sont nécessaires : invocation en **processus séparé** sur fichiers, jamais en import in-process.

## B.8 — Relighting (§2.6)

| Composant | Licence | Commercial | Conf. |
|---|---|---|---|
| **Relightable 3D Gaussians** | Gaussian-Splatting License | **non** | confirmé |
| **GS-IR** | `/LICENSE` MIT **au nom d'un tiers** ; sources INRIA | **non** ⚠️43 | confirmé |
| **GI-GS** | `/LICENSE` MIT ; noyau INRIA + nvdiffrast | **non** ⚠️43 | confirmé |
| **GeoSplatting** | **Apache-2.0**, bâti sur gsplat | conditionnel ⚠️44 | confirmé |
| MaterialClusterGS | Papier seul (arXiv 2606.09018), **aucun code** | **non** ⚠️45 | non vérifié |
| nvdiffrec / nvdiffrecmc (transitifs) | NVIDIA Source Code License | **non** ⚠️46 | confirmé |

**⚠️43 — Le piège du badge GitHub, dans sa forme la plus trompeuse.** `GS-IR` a un `/LICENSE` au texte MIT verbatim… dont la ligne de copyright dit **« Copyright (c) 2023 Mark Kellogg »** — le titulaire de `mkkellogg/GaussianSplats3D`, un projet sans rapport. Vérifié par quatre chemins indépendants, y compris l'API GitHub qui retourne `spdx_id: "MIT"`. **Un fichier MIT ne peut pas licencier du code que les auteurs ne possèdent pas.** Les sources réelles (`scene/gaussian_model.py`) portent l'en-tête « Copyright (C) 2023, Inria / GRAPHDECO research group … free for non-commercial, research and evaluation use ». Si quelqu'un objecte « mais GitHub dit MIT », ce sont les en-têtes Inria et le `LICENSE.md` du submodule qui font foi. Même schéma pour GI-GS.

**⚠️44 — GeoSplatting est la seule porte de sortie, et elle est atteignable.** Apache-2.0 confirmé (`pyproject.toml` : `license = { text="Apache 2.0" }`), et surtout : **il rastérise via `gsplat~=1.4.0`, pas via le rastériseur INRIA** — inspection de `rfstudio/` faite, aucun module nvdiffrec vendorisé trouvé. Le seul blocage est `nvdiffrast`, listé dans les étapes d'install du README. → **Commercial = oui si (a) `nvdiffrast` est retiré ou remplacé, et (b) un balayage d'en-têtes NVIDIA fichier par fichier de `rfstudio/graphics/` revient propre.** Ce balayage n'a pas été fait par l'audit et doit l'être avant tout ship.

**⚠️45 — MaterialClusterGS n'existe pas en tant que logiciel.** Recherche GitHub : « 0 results ». Page arXiv : aucun lien code, aucune page projet. La licence arXiv « perpetual non-exclusive » licencie arXiv à distribuer **le papier** — elle ne vous concède rien et ne couvre aucun logiciel. Et si le code sort un jour en forkant `2d-gaussian-splatting`, il portera presque certainement la licence INRIA.

**⚠️46 — Un « Acknowledgement » signifie souvent que du code a été copié, pas seulement cité.** Le code split-sum / renderutils / light-probe de nvdiffrec se retrouve fréquemment collé dans les dépôts aval **sans l'en-tête NVIDIA**. Avant de livrer quoi que ce soit de cette famille : balayage d'en-têtes de copyright et similarité de code. Toute correspondance est un blocage dur.

## B.9 — HDRI d'environnement (§2.8)

| Composant | Licence | Commercial | Conf. |
|---|---|---|---|
| **DiffusionLight** — code | MIT | **oui** ⚠️47 | confirmé |
| DiffusionLight — poids LoRA | MIT déclaré (frontmatter HF) | conditionnel ⚠️47 | confirmé |
| **SDXL base 1.0** | CreativeML Open RAIL++-M | conditionnel ⚠️48 | confirmé |
| controlnet-depth-sdxl-1.0 | CreativeML Open RAIL++-M | conditionnel | confirmé |
| **skylibs** (transitif DiffusionLight) | **LGPL-3.0** | conditionnel ⚠️49 | confirmé |
| huggingface diffusers | 0.39.0 | Apache-2.0 | **oui** | confirmé |
| huggingface transformers | 5.15.0 | Apache-2.0 | **oui** | confirmé |
| Hugin (+ nona, libpano13) | 2025.0.1 | GPL-2.0-or-later | conditionnel ⚠️50 | confirmé |
| enblend / enfuse | 4.2 (2016) | GPL-2.0-or-later | conditionnel ⚠️50 ⚠️51 | confirmé |
| PTGui / PTGui Pro | 13.9 | Propriétaire (EULA) | conditionnel ⚠️52 | confirmé |

**⚠️47 — Le MIT du LoRA ne peut pas effacer les restrictions de SDXL.** Le frontmatter HF déclare `license: mit`, mais aussi `base_model: stabilityai/stable-diffusion-xl-base-1.0` : c'est un adaptateur LoRA, juridiquement une œuvre dérivée de SDXL, inutilisable sans charger le modèle de base. Or la CreativeML Open RAIL++-M stipule que les versions dérivées « will always have to include — at minimum — the same use-based restrictions ». **Termes effectifs = MIT + restrictions d'usage OpenRAIL++.**

**⚠️48 — SDXL n'est pas non-commercial**, contrairement à une idée reçue tenace : la §II concède « perpetual, worldwide, non-exclusive, no-charge, royalty-free, irrevocable copyright license ». Trois conditions à porter dans le produit : (1) les restrictions d'usage de l'Attachment A doivent être **répercutées à tout utilisateur aval** et intégrées au CLUF de l'addon ; (2) le licenceur se réserve le droit de restreindre l'usage à distance ; (3) **contradiction à faire trancher** : la fiche modèle affirme « The model is intended for research purposes only » alors que la licence autorise le commercial. Le texte de licence prime normalement, mais l'ambiguïté est documentée — ne pas signer un contrat client là-dessus sans avis juridique écrit.

**⚠️49 — La surprise de la famille : `skylibs`, LGPL-3.0**, listée en dur dans le `requirements.txt` de DiffusionLight (`skylibs==0.7.4`), et que personne ne regarde. L'import depuis du code propriétaire est autorisé, mais la distribution impose de permettre le **relink** par l'utilisateur. **Le schéma dangereux est le gel dans un PyInstaller one-file**, qui casse de fait ce droit et met la conformité en défaut. → Alternative : remplacer par du code maison + OpenEXR/imageio.

**⚠️50 — Hugin / enblend / enfuse : appel en sous-processus = OK, redistribution = obligations.** Invoquer `hugin`, `nona`, `pto_gen` en sous-processus depuis le sidecar est le schéma « arm's length » admis et ne contamine pas votre code. Bundler les binaires dans un installeur ou une image Docker déclenche l'obligation de fournir le texte GPL et une offre de source. **Interdit absolument** : lier `hugin_base` ou `libpano13` en process.

**⚠️51 — Avertissement méthodologique, pas de licence : `enfuse` produit une image LDR fusionnée, pas un HDR linéaire radiométrique.** Si la §2.8 attend un `.exr`/`.hdr` mesuré — et c'est bien ce qu'elle attend pour du relighting crédible — enfuse ne suffit pas et il faut une étape de merge HDR séparée, dont la licence reste à auditer. (Note annexe : enblend/enfuse est dormant depuis 2016, aucun correctif récent.)

**⚠️52 — PTGui : la licence Personal ne couvre pas un usage studio.** Il faut une licence Company (par poste) ou Floating. Vous ne pouvez **pas** le bundler ni le revendre : l'addon peut seulement l'invoquer si chaque poste a sa propre licence. Le merge HDR de panoramas est une fonction **Pro** spécifiquement. Contrepartie favorable : aucune contamination GPL, votre code reste fermé.

## B.10 — Infrastructure du sidecar (§1, §5)

| Composant | Version | Licence | Commercial | Conf. |
|---|---|---|---|---|
| **PyTorch** | 2.13.0 | BSD-3-Clause | **oui** ⚠️53 | confirmé |
| **NVIDIA CUDA Toolkit** (wheels `nvidia-*`) | 13.x | **EULA propriétaire** | conditionnel ⚠️54 | confirmé |
| **NVIDIA cuDNN** | 9.x | **EULA propriétaire distinct** | conditionnel ⚠️55 | confirmé |
| **Pilote NVIDIA GeForce / Titan** | 2026-08 | EULA propriétaire | conditionnel ⚠️56 | confirmé |
| nvidia-nccl (Linux) | 2.30.7 | Apache-2.0 (+ portions BSD-3) | **oui** | confirmé |
| FastAPI | 0.141.1 | MIT | **oui** | confirmé |
| uvicorn | 0.52.1 | BSD-3-Clause | **oui** | confirmé |
| starlette | 1.6.0 | BSD-3-Clause | **oui** | confirmé |
| pydantic | 2.13.4 | MIT | **oui** | confirmé |
| websockets | 17.0.1 | BSD-3-Clause | **oui** | confirmé |
| numpy | 2.5.2 | BSD-3-Clause (wheel composite) | **oui** | confirmé |
| Pillow | 12.3.0 | MIT-CMU | **oui** ⚠️57 | confirmé |
| PyYAML | 6.0.3 | MIT | **oui** | confirmé |
| **tqdm** | 4.70.0 | **MPL-2.0 AND MIT** | **oui** ⚠️58 | confirmé |
| certifi (transitif) | 2026.7.22 | **MPL-2.0** | **oui** ⚠️58 | confirmé |
| ruff | 0.16.2 | MIT | **oui** (dev only) | confirmé |
| pytest | 9.1.1 | MIT | **oui** (dev only) | confirmé |
| Intel MKL / OpenMP (transitif possible) | — | **À VÉRIFIER** ⚠️V8 | À VÉRIFIER | non vérifié |

**⚠️53 — Le code PyTorch est BSD-3, la wheel ne l'est pas.** PyPI déclare pour la distribution binaire `Apache-2.0 AND Apache-2.0 WITH LLVM-exception AND BSD-2-Clause AND BSD-3-Clause AND BSL-1.0 AND MIT`. Sur Windows, **les DLL CUDA/cuDNN sont livrées dans `torch/lib`**, pas en wheels séparées. → Avant toute redistribution, inspecter physiquement `site-packages/torch/lib` et `torch-*.dist-info/licenses` de la wheel exacte livrée.

**⚠️54 — CUDA est propriétaire.** L'usage commercial interne est autorisé. La redistribution est autorisée **mais clôturée** : seuls les fichiers énumérés à l'Attachment A, uniquement « incorporated in object code format into a software application », et **« Your application must have material additional functionality, beyond the included portions of the SDK »**. Un addon Blender + sidecar satisfait plausiblement ce test, mais c'est un jugement juridique, pas technique. → **Si vous demandez simplement à l'utilisateur d'installer CUDA lui-même, aucune de ces clauses ne mord.** C'est de loin le chemin le plus simple.

**⚠️55 — cuDNN a un accord distinct, et une clause qui vous concerne directement.** L'accord **interdit** d'utiliser le SDK « in a manner that would cause it to become subject to an open source software license » exigeant la divulgation des sources. Autrement dit : **cuDNN ne peut pas être lié dans quoi que ce soit que vous livrez sous GPL/AGPL.** Comme l'addon Blender est GPL par construction, cela **impose** de garder CUDA/cuDNN strictement dans le sidecar séparé, communiquant par IPC/HTTP — jamais dans un module Python importé dans l'espace processus GPL de Blender. **C'est un argument juridique supplémentaire, indépendant, en faveur de l'architecture sidecar de la §1.**

**⚠️56 — La licence qui gate réellement le déploiement studio, et que tout le monde oublie.** Verbatim : « GeForce or Titan SOFTWARE … (ii) **is not licensed for datacenter deployment** » et « you may not … provide commercial hosting services with the SOFTWARE ». Concrètement : la RTX 4080 sur un poste artiste, aucun problème. Mettre des cartes GeForce dans une ferme de rendu rackée, ou offrir le sidecar GAMB en service hébergé sur du GeForce, sort de cette licence et exige des GPU RTX pro / datacenter. **Pertinent pour Q7 (sidecar distant) : la réponse « machine distante » peut basculer de la question technique à la question de licence GPU.**

**⚠️57 — Pillow** : MIT-CMU, permissif. Un seul point pour la redistribution : les wheels embarquent statiquement libjpeg-turbo, zlib, libtiff, libwebp, openjpeg, freetype, littlecms, dont les notices ne sont pas dans le LICENSE — **freetype (FTL) exige un crédit dans votre documentation**.

**⚠️58 — Les deux MPL-2.0 silencieux d'une stack que tout le monde étiquette « tout MIT/BSD ».** `tqdm` n'est **pas** MIT : PyPI dit littéralement `MPL-2.0 AND MIT`. `certifi` est MPL-2.0. MPL-2.0 est du copyleft **au fichier**, il n'infecte ni l'addon ni le sidecar. L'obligation ne se déclenche que si vous **modifiez** leurs fichiers et distribuez le résultat. → Règle simple : utiliser ces paquets non modifiés, ne jamais vendoriser une copie patchée. Pour `certifi` en particulier : configurer un chemin CA à l'exécution plutôt qu'éditer le paquet.

## B.11 — Côté Blender et distribution (§9, §10 P0)

| Composant | Licence | Commercial | Conf. |
|---|---|---|---|
| **Blender** | Sources **GPL-2.0-or-later** ; binaire distribué GPL-3.0-or-later | **oui** ⚠️A5 | confirmé |
| **API Python Blender (`bpy`)** | Partie intégrante de Blender → GPL | conditionnel ⚠️59 | confirmé |
| **`bpy` (paquet PyPI)** | GPL-3.0 | conditionnel ⚠️60 | confirmé |
| **extensions.blender.org** | Politique : add-ons **GPL-3.0-or-later obligatoire** ; assets binaires **CC0 obligatoire** | conditionnel ⚠️61 | confirmé |
| **3DGS Render by KIRI Engine** | **À VÉRIFIER** — trois déclarations contradictoires | conditionnel ⚠️A6 | non vérifié |

**⚠️59 — La position officielle, verbatim, et le carve-out exact.** blender.org/about/license : « Blender's Python API is an integral part of the software … The GNU GPL license therefore requires that such scripts (if published) are being shared under a GPL compliant license. **You are free to sell such scripts**, but the sales then is restricted to the download service itself. » Et la FAQ : « Can I sell add-ons for Blender? **Yes you can, but only if you provide the add-on and the sources to your clients under the GNU GPL license.** »

Le carve-out processus séparé, verbatim : « You have full freedom to license your software product however you wish **if and only if**: – It operates outside of Blender. – **Uses no Blender source code or API calls (including Python API)**. – Produces data for Blender to operate on. – Executes Blender to read and operate on the data. »

→ **L'addon doit être GPL s'il est distribué. Le sidecar peut rester propriétaire uniquement s'il n'appelle aucune API Blender.** Usage purement interne, sans distribution externe : aucune obligation de publication.

**⚠️60 — Le piège qui annulerait tout le bénéfice de l'architecture.** Si le sidecar fait `import bpy` (le paquet PyPI, « Blender as a Python module ») — par exemple pour convertir ou exporter sans ouvrir Blender — il devient une œuvre dérivée de Blender sous GPL-3.0 et **perd immédiatement le bénéfice du processus séparé**, même en tournant dans un processus distinct. → À interdire en CI côté sidecar, au même titre que `diff_gaussian_rasterization`.

**⚠️61 — Publier sur extensions.blender.org = renoncer définitivement à un addon propriétaire.** ToS §1.1 : « Uploaded add-ons must be wholly compliant with the GNU General Public License, version 3 or later. » §1.2 : les assets binaires embarqués (images, SVG, polices) doivent être **CC0**. La plateforme ne distribue que du gratuit et open source ; une vente doit passer par un autre canal (Superhive) et reste soumise à la GPL.
*Divergence relevée :* le code de la plateforme (`constants/licenses.py`) accepte **deux** valeurs SPDX — `GPL-2.0-or-later` **et** `GPL-3.0-or-later` — alors que les ToS exigent GPLv3+. Le template officiel Blender déclare `SPDX:GPL-3.0-or-later`. → Utiliser `GPL-3.0-or-later`.

---

# C. Élections de licence à acter

Cinq composants offrent un **choix** de licence. Ne pas choisir, c'est laisser un relecteur choisir à votre place — et il choisira la plus stricte.

| Composant | Options | **Élection recommandée** | Pourquoi |
|---|---|---|---|
| **E1 — glm** | Happy Bunny **ou** MIT | **MIT** | La variante Happy Bunny ajoute une clause blague mais textuellement présente (« By making use of the Software for military purposes, you choose to make a Bunny unhappy »). Élire MIT évite tout débat. glm est **compilé dans l'extension CUDA livrée** : sa notice doit figurer dans le fichier d'attribution — l'Apache-2.0 de gsplat ne la couvre pas. |
| **E2 — LibRaw** | LGPL-2.1 **ou** CDDL-1.0 | **CDDL-1.0** | Sous LGPL-2.1, le linkage statique (ce que fait la wheel rawpy) déclenche le §6 : fournir les fichiers objets ou un mécanisme de **relink**. Pénible pour un sidecar compilé. Sous CDDL-1.0, le copyleft est **au fichier** : linkage statique dans du propriétaire autorisé, obligation de source uniquement sur les fichiers LibRaw que **vous** modifiez. ⚠️ La wheel rawpy ne livre **que** le texte LGPL — si vous élisez CDDL, ajoutez `LICENSE.CDDL` vous-même. |
| **E3 — Poids RawNIND UtNet2** | GPL-3.0 **ou** CC-BY-4.0 | **CC-BY-4.0** | Réduit l'obligation à l'attribution seule et évite de traîner de la GPL dans ce que vous redistribuez. |
| **E4 — ExifTool** | Perl Artistic **ou** GPL | **Perl Artistic** | Le badge GitHub dit « GPL-3.0 » parce que le `/LICENSE` du dépôt est du GPLv3 — mais la concession réelle de l'auteur, dans le README, est duale : « under the same terms as Perl itself (either the Perl Artistic License or GPL) ». Si vous ne dites rien, un relecteur conclura GPL. Invoquer en **processus séparé** (`-stay_open`), jamais en embarquant la lib Perl. |
| **E5 — OpenCV** | standard **ou** headless | **`opencv-python-headless`** | Élimine la dépendance Qt5/LGPL-3.0, le composant le plus contraignant. Un sidecar sans GUI n'a pas besoin de `highgui`. Il reste FFmpeg/LGPL-2.1 à documenter. |

---

# D. Lignes « À VÉRIFIER » — actions nommées

Dix lignes n'ont pas pu être confirmées à la source primaire. Chacune a une action précise et un responsable implicite.

| # | Composant | Ce qui a bloqué | Action |
|---|---|---|---|
| **V1** | simple-knn (Inria) | `gitlab.inria.fr` derrière le challenge anti-bot Anubis ; toutes les URLs raw renvoient l'interstitiel | `git clone https://gitlab.inria.fr/bkerbl/simple-knn.git` depuis un client git (le clone contourne Anubis) et lire `LICENSE.md`. **Sans objet si on reste sur gsplat/Brush**, qui n'en ont pas besoin. Traiter comme non-commercial d'ici là. |
| **V2** | Poids S2DNet | Checkpoint hébergé sur une URL Dropbox codée en dur, hors dépôt, sans model card ni licence | Confirmation écrite de l'auteur (Hugo Germain) que le MIT couvre le `.pth`, **ou** désactiver le raffinement dense de pixsfm. Ce n'est pas un signal de restriction, c'est une absence de déclaration. |
| **V3** | Poids VGGT-1B-Commercial | HF gated (`manual`), `HTTP 401` sur `/raw/main/LICENSE` | Un humain avec compte approuvé télécharge et **archive le corps de la licence**. Question ouverte décisive : peut-on bundler le `.pth` dans un installeur studio, ou chaque poste doit-il accepter le gate ? |
| **V4** | Poids SAM 3.1 | HF gated, `HTTP 401` ; le dépôt contient bien un `LICENSE` mais illisible | Diff du `LICENSE` de `facebook/sam3.1` contre celui de `facebookresearch/sam3`. Le **code** 3.1 est confirmé (il vit dans le dépôt sam3), seuls les **poids** sont non vérifiés. |
| **V5** | Poids MUSIQ | Checkpoints sur un bucket GCS sans énoncé de licence ; page Kaggle en JS, contenu vide au fetch | Vérifier à la main la fiche Kaggle / TF-Hub dans un navigateur. **Ne pas supposer Apache-2.0** : les checkpoints ne sont pas des « source files in this repository ». Le README porte « This is not an official Google product ». |
| **V6** | Poids OpenAI CLIP | Aucune déclaration de licence trouvée : README, model card, frontmatter HF et API HF tous muets | Signal défavorable à ne pas ignorer : la model card dit « **Any** deployed use case of the model — whether commercial or not — is currently out of scope ». → Préférer **OpenCLIP** (code Apache-2.0, poids LAION explicitement licenciés), à auditer séparément. |
| **V7** | StableNormal | Apache-2.0 déclarée code **et** poids, mais fine-tuné depuis **SD 2.1** ; `stabilityai/stable-diffusion-2-1` renvoie `HTTP 401` (gated) | Lire `LICENSE-MODEL` de SD 2.1 avec un compte HF, puis faire trancher : le relabel Apache-2.0 de Stable-X peut-il valablement retirer les restrictions d'usage RAIL++-M amont ? |
| **V8** | Intel MKL / OpenMP | Le paquet PyPI `mkl` déclare « Intel Simplified Software License » (propriétaire), mais la présence effective dans la wheel torch Windows n'est pas établie | Dézipper la wheel torch exacte livrée, lister `torch/lib/*.dll`, lire `torch-*.dist-info/licenses`. **Ne pas cocher « oui » au prétexte que « PyTorch est BSD ».** |
| **V9** | KIRI 3DGS Render | Trois licences contradictoires dans le même dépôt (voir ⚠️A6) | Clarification écrite de KIRI (contact@kiri-innov.com) ou issue amont. **Reste `À VÉRIFIER` d'ici là.** Sans objet si on s'en tient à l'interop par fichier. |
| **V10** | MaterialClusterGS | Aucun dépôt de code n'existe | Re-vérifier si le code sort. Traiter toute publication future comme INRIA-contaminée jusqu'à lecture de son `LICENSE`. |

---

# E. Règles à appliquer en CI

L'audit ne vaut que s'il est **mécanisé**. Chacune de ces règles ferme une contamination identifiée ci-dessus et coûte quelques lignes.

| Règle | Ferme |
|---|---|
| Aucun import hors stdlib + `bpy` dans `addon/` | La frontière d'architecture §1 |
| **`bpy` interdit dans `engine/`** | ⚠️60 — perte du carve-out processus séparé |
| `diff_gaussian_rasterization` et `*_inria_wrapper` interdits partout | ⚠️1, ⚠️5 — la licence recherche INRIA |
| `ultralytics` et `ultralytics-thop` interdits | ⚠️A2 — AGPL-3.0 |
| `pyiqa` interdit | ⚠️A1 — PolyForm Noncommercial |
| `plyfile` interdit | ⚠️7 — GPL-3.0-or-later |
| Assert : `VGGT-1B` jamais résolu comme id de checkpoint (seul `VGGT-1B-Commercial` autorisé) | ⚠️15 |
| Assert : `map-anything` jamais résolu (seul `map-anything-apache` autorisé) | ⚠️18 |
| Grep `igl/copyleft` dans le graphe d'inclusion | ⚠️41 |
| `RAWPY_BUILD_GPL_CODE` et `OPENCV_ENABLE_NONFREE` interdits dans les scripts de build | ⚠️30, ⚠️28 |
| Tout COLMAP buildé maison : `-DLSD_ENABLED=OFF`, sans `GPU_ENABLED` | ⚠️9 |
| `opencv-*-headless` épinglé, variante non-headless interdite | E5 |
| Snapshot du lockfile résolu + diff de licences à chaque montée de version | LibRaw prévient : « We do not guarantee that the licensing will not change » |

---

# F. Récapitulatif — la stack livrable

Ce qui reste après filtrage, pour un produit commercial fermé et distribué :

| Étage | Retenu | Écarté |
|---|---|---|
| **Trainer** | **gsplat** (Apache-2.0) · Brush en comparaison | INRIA, tous ses forks, spirulae-splat et LichtFeld si distribué |
| **Poses** | **pycolmap** wheel PyPI · GLOMAP · LightGlue+DISK/ALIKED | COLMAP buildé maison, SuperPoint, SuperGlue, R2D2 |
| **Feed-forward** | **MapAnything `-apache`** · VGGT code + `VGGT-1B-Commercial` | VGGT-X, Pi3, 3R-GS, DUSt3R, MASt3R, `VGGT-1B` |
| **Segmentation** | **SAM 3** direct (conditions §B.4) · SAM 2 en repli propre | Ultralytics |
| **Curation** | DINOv2 · scikit-image · scipy · opencv headless | pyiqa, TOPIQ, CLIP-IQA, et MUSIQ par cette voie |
| **RAW** | **rawpy** (LibRaw en CDDL) · tifffile · imageio · colour-science · ExifTool en sous-processus | packs de dématriçage GPL, imageio-freeimage |
| **Mesh** | **Open3D** · trimesh · xatlas · libigl hors `copyleft/` | 2DGS, GOF, MILo, PGSR, GS-2M, nvdiffrast, PyMeshLab in-process |
| **Relighting** | **GeoSplatting** sans nvdiffrast — seule voie | GS-IR, GI-GS, Relightable3DGS, MaterialClusterGS |
| **HDRI** | DiffusionLight + SDXL (restrictions RAIL++ à répercuter) · Hugin en sous-processus | skylibs en bundle figé, PTGui bundlé |
| **Infra** | FastAPI · uvicorn · pydantic · PyTorch · CUDA installé par l'utilisateur | — |

**La conclusion structurante :** le pipeline « mesh haute fidélité + matériaux » de la §2.5 et la §2.6 n'a **aucune** voie commerciale prête à l'emploi. La seule piste est **GeoSplatting débarrassé de nvdiffrast**, parce qu'il est le seul du domaine bâti sur gsplat plutôt que sur le rastériseur INRIA. Tout le reste exige une licence négociée avec l'Inria (`stip-sophia.transfert@inria.fr`), avec l'université de Zhejiang, ou avec NVIDIA Research.

---

*Audit conduit le 2026-08-10. Toute montée de version invalide la ligne correspondante : re-vérifier. Ce fichier est un document vivant, pas un instantané.*
