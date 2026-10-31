"""
Anomaly injection module.

This module injects labelled anomalies into valid data and generates ground truth.
To be implemented in Phase 4.
"""

import pandas as pd
import numpy as np
from typing import Dict, Tuple


def inject_anomalies(
    master_data: Dict[str, pd.DataFrame],
    event_data: Dict[str, pd.DataFrame],
    profile: str,
    rng: np.random.Generator
) -> Tuple[Dict[str, pd.DataFrame], pd.DataFrame, Dict]:
    """
    Inject labelled anomalies and return modified data, ground truth, and summary.

    Args:
        master_data: Dictionary of master DataFrames.
        event_data: Dictionary of event DataFrames.
        profile: Profile name ('dev' or 'full').
        rng: Random number generator.

    Returns:
        Tuple of:
        - Modified event data dictionary
        - Ground truth DataFrame
        - Injection summary dictionary

    Raises:
        NotImplementedError: Until Phase 4 implementation.
    """
    raise NotImplementedError("anomaly_injector.inject_anomalies to be implemented in Phase 4")
