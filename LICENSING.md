# Licences du dépôt

Ce fichier fait autorité sur **la licence du code de ce dépôt**. Pour les licences
des *dépendances*, voir [`LICENSES.md`](LICENSES.md) — ce sont deux sujets
distincts qu'il ne faut jamais mélanger.

## La règle

> Le dépôt est sous **GPL-3.0-or-later**, sauf dans un sous-dossier qui contient
> son propre fichier `LICENSE`, auquel cas c'est celui-là qui s'applique.

Il n'existe aujourd'hui qu'une seule exception, et elle est délibérée :

| Chemin | Licence | Pourquoi |
|---|---|---|
| `addon/` | **GPL-3.0-or-later** | Un addon Blender lie l'API de Blender. Ce n'est pas un choix, c'est une conséquence. |
| `engine/` | **Apache-2.0** | Le sidecar est un processus séparé qui ne lie rien de Blender. |
| tout le reste | **GPL-3.0-or-later** | Défaut du dépôt (`LICENSE` à la racine). |

## Pourquoi deux licences plutôt qu'une

Ce n'est pas de la coquetterie juridique, c'est ce qui rend le moteur utilisable.

**Le sidecar doit pouvoir vivre hors de Blender.** La spec exige que tout ce que
fait l'addon soit faisable en CLI, sans Blender. Un moteur sous GPL-3 par
contagion serait verrouillé pour tout réemploi futur — et notamment inutilisable
depuis un moteur de jeu.

**Et une des licences de la stack l'impose littéralement.** L'accord cuDNN de
NVIDIA interdit d'utiliser le SDK « in a manner that would cause it to become
subject to an open source software license » exigeant la divulgation des
sources. Comme l'addon Blender est GPL par construction, cuDNN ne peut pas
légalement vivre dans l'espace processus de Blender. La séparation addon /
sidecar n'est donc pas seulement une bonne idée technique — elle est **requise**.

Apache-2.0 côté moteur parce qu'elle est compatible dans le sens qui compte :
du code Apache-2.0 peut être intégré à un ensemble GPL-3, l'inverse est faux.
C'est aussi la licence de `gsplat`, la dépendance centrale.

## Le cas particulier : `naming.py`

Le module de nommage existe en deux exemplaires **identiques octet pour octet**,
un de chaque côté de la frontière de licence :

```
engine/gamb_engine/naming.py
addon/gausian_and_mesh_builder/naming.py
```

Un fichier ne peut pas être à la fois sous Apache-2.0 et sous GPL-3 selon
l'endroit où on le lit. Il porte donc un double SPDX :

```python
# SPDX-License-Identifier: Apache-2.0 OR GPL-3.0-or-later
```

Le receveur choisit. C'est la seule construction qui satisfait à la fois la
contrainte d'identité binaire — vérifiée par le CI — et la séparation des
licences.

## Ce que GitHub affiche, et pourquoi c'est correct

GitHub ne lit que le `/LICENSE` racine et affichera donc **GPL-3.0**. C'est
volontaire : c'est la plus restrictive des deux, personne n'est induit en erreur
par excès de prudence. L'inverse — un badge permissif sur un dépôt partiellement
copyleft — serait une fausse déclaration.

## La leçon qu'on n'a pas envie de réapprendre

L'audit du 2026-08-10 a trouvé un addon Blender 3DGS très diffusé portant
**trois licences contradictoires** : son `/LICENSE` dit Apache-2.0 (boilerplate
jamais relu depuis 2024), le `blender_manifest.toml` qui ship réellement déclare
`GPL-2.0-or-later`, et l'en-tête de son `__init__.py` dit GPL-3+. Le badge
GitHub ne lit que le premier, donc tout le monde le croit Apache-2.0. Il est
inutilisable en pratique : personne ne peut dire sous quelle licence son code
est réellement distribué.

Les trois défenses qu'on applique ici contre ce scénario :

1. **Un en-tête SPDX dans chaque fichier source.** C'est ce qui reste vrai quand
   les fichiers sont copiés, déplacés ou vendorisés.
2. **Ce fichier** comme carte unique, référencée depuis le README.
3. **Le `blender_manifest.toml` devra déclarer exactement `GPL-3.0-or-later`**
   quand il arrivera à P1 — c'est lui que Blender lit, pas le `/LICENSE`.

## Contribuer

Toute contribution est acceptée sous la licence du sous-arbre où elle atterrit.
Un fichier nouveau porte son en-tête SPDX dès sa création, jamais « plus tard ».
