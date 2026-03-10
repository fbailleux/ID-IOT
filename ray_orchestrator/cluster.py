"""
Gestion du cluster Ray.

Par défaut : mode local (single-node, même processus).
Avec RAY_ADDRESS défini : connexion à un cluster distant (ex: ray-head).
"""
from __future__ import annotations

import logging
import os

import ray

logger = logging.getLogger(__name__)

_initialized = False


def init_ray() -> bool:
    """
    Initialise Ray.

    - Si RAY_ADDRESS est défini → connexion au cluster distant.
    - Sinon → mode local (tous les workers dans le même conteneur).

    Retourne True si l'initialisation a réussi.
    """
    global _initialized
    if _initialized and ray.is_initialized():
        return True

    ray_address = os.getenv("RAY_ADDRESS", "")
    num_cpus = int(os.getenv("RAY_NUM_CPUS", "4"))

    try:
        if ray_address:
            ray.init(
                address=ray_address,
                ignore_reinit_error=True,
                log_to_driver=False,
            )
            logger.info(f"[Ray] Connecté au cluster distant : {ray_address}")
        else:
            ray.init(
                ignore_reinit_error=True,
                log_to_driver=False,
                num_cpus=num_cpus,
            )
            logger.info(f"[Ray] Mode local ({num_cpus} CPUs)")

        _initialized = True
        return True

    except Exception as exc:
        logger.error(f"[Ray] Initialisation échouée : {exc}")
        return False


def shutdown_ray() -> None:
    """Arrête le runtime Ray proprement."""
    global _initialized
    if ray.is_initialized():
        ray.shutdown()
        _initialized = False
        logger.info("[Ray] Cluster arrêté")
