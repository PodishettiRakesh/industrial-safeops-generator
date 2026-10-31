"""
Master data generation module.

This module generates Plant, Machine, SafetyZone, Interlock, and AlarmDefinition entities.
To be implemented in Phase 2.
"""

import pandas as pd
import numpy as np
from typing import Dict


def generate_master_data(profile: str, rng: np.random.Generator) -> Dict[str, pd.DataFrame]:
    """
    Generate all master data entities in dependency order.

    Args:
        profile: Profile name ('dev' or 'full').
        rng: Random number generator.

    Returns:
        Dictionary of DataFrames keyed by entity name.

    Raises:
        NotImplementedError: Until Phase 2 implementation.
    """
    raise NotImplementedError("master_gen.generate_master_data to be implemented in Phase 2")
