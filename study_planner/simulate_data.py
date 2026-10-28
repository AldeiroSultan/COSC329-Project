"""Simulate student records and write them to CSV (branch MF-00002).

See docs/DATA.md for the generative process.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from study_planner import config as cfg


def sigmoid(z: np.ndarray | float) -> np.ndarray | float:
    return 1.0 / (1.0 + np.exp(-z))


def simulate_students(n: int = cfg.N_STUDENTS, seed: int = cfg.RANDOM_SEED) -> pd.DataFrame:
    """Generate n students following docs/DATA.md; columns in the documented order.

    TODO(MF-00002): use np.random.default_rng(seed) so output is reproducible.
    """
    raise NotImplementedError("MF-00002")


def parent_config_counts(df: pd.DataFrame) -> dict[str, pd.Series]:
    """Row count for every parent configuration of each learned CPT (data sufficiency check).

    TODO(MF-00002)
    """
    raise NotImplementedError("MF-00002")


def write_csv(df: pd.DataFrame, path: Path = cfg.STUDENTS_CSV) -> Path:
    """Write the dataframe to CSV, creating parent folders."""
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)
    return path
