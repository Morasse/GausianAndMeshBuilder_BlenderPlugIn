# SPDX-License-Identifier: Apache-2.0
"""Entraînement.

Le module n'importe **ni torch ni gsplat au chargement**. Le sidecar doit
répondre `/health` et servir les fiches d'options sans avoir payé trois
secondes d'import CUDA, et le CI doit pouvoir tester tout ce qui n'est pas du
GPU sur un runner qui n'en a pas.
"""
