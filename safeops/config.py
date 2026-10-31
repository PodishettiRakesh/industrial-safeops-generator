"""
Configuration module for SafeOps Generator.

This module defines all configuration parameters, profiles, enums,
and deterministic random number generator initialization.
"""

import random
from typing import Dict, Any
import numpy as np

# =============================================================================
# GLOBAL CONSTANTS
# =============================================================================

SEED = 20261022
SIMULATION_START_UTC = "2026-01-01T00:00:00Z"
SIMULATION_DAYS = 30
TIMESTAMP_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
CSV_ENCODING = "utf-8"
CSV_NULL_VALUE = ""
FLOAT_FORMAT = "%.6f"

# =============================================================================
# PROFILES
# =============================================================================

PROFILES: Dict[str, Dict[str, Any]] = {
    "dev": {
        "num_plants": 2,
        "num_machines": 5,
        "num_alarm_definitions": 10,
        "num_alarm_events": 500,
        "shortened_window": True
    },
    "full": {
        "num_plants": 4,
        "num_machines": 60,
        "num_alarm_definitions": 200,
        "num_alarm_events": 50000,
        "shortened_window": False
    }
}

# =============================================================================
# ENUM VALUES
# =============================================================================

MACHINE_TYPES = ["CNC_Mill", "Robotic_Arm", "Stamping_Press", "Furnace"]
MACHINE_STATUS = ["Operational", "Maintenance", "Offline"]
ZONE_TYPES = ["Perimeter_Laser", "Pressure_Mat", "Proximity_Radar"]
RISK_LEVELS = ["Low", "Medium", "High", "Critical"]
INTERLOCK_TYPES = ["Mechanical_Guard", "Electrical_Relay", "Software_E-Stop"]
INTERLOCK_STATES = ["Closed", "Engaged", "Energized"]
METRIC_NAMES = ["Temperature", "Vibration", "Pressure", "Voltage"]
SEVERITY_LEVELS = ["Low", "Medium", "High", "Critical"]
INTERLOCK_STATUS = ["Secure", "Tripped", "Bypassed"]
INCIDENT_SEVERITY = ["Major", "Critical", "Catastrophic"]
ACTION_STATUS = ["Open", "In_Progress", "Closed"]

# =============================================================================
# ANOMALY CATEGORIES
# =============================================================================

ANOMALY_TYPES = [
    "ACK_BEFORE_ALARM",
    "IMPOSSIBLE_INTERLOCK",
    "MISSING_CONTEXT",
    "REPLAY_FLOOD",
    "UNVERIFIED_CLOSURE"
]

# =============================================================================
# ID FORMAT PATTERNS (regex for validation)
# =============================================================================

ID_PATTERNS = {
    "plant": r"^PLT-\d{3}$",
    "machine": r"^MCH-\d{3}$",
    "zone": r"^SAFE-PLT-\d{3}-\d{3}$",
    "interlock": r"^INT-\d{4}$",
    "alarm_def": r"^DEF-\d{4}$",
    "shift": r"^SHF-2026-\d{5}$",
    "alarm_event": r"^ALM-MCH-\d{3}-\d{6}$",
    "ack": r"^ACK-ALM-MCH-\d{3}-\d{6}-\d{2}$",
    "incident": r"^INC-2026-\d{6}$",
    "action": r"^ACT-INC-2026-\d{6}-\d{2}$"
}

# =============================================================================
# METRIC UNITS AND THRESHOLD RANGES
# =============================================================================

METRIC_UNITS = {
    "Temperature": "°C",
    "Vibration": "mm/s",
    "Pressure": "bar",
    "Voltage": "V"
}

METRIC_RANGES = {
    "Temperature": (20.0, 150.0),
    "Vibration": (0.0, 50.0),
    "Pressure": (0.0, 100.0),
    "Voltage": (110.0, 480.0)
}

# =============================================================================
# BUSINESS RULES (documented for later phases)
# =============================================================================

# Shift duration: 8 hours
SHIFT_DURATION_HOURS = 8

# Acknowledgement SLAs by severity (in minutes)
ACKNOWLEDGEMENT_SLAS = {
    "Low": 120,      # 2 hours
    "Medium": 60,   # 1 hour
    "High": 30,     # 30 minutes
    "Critical": 15  # 15 minutes
}

# Interlock normal states by type
INTERLOCK_NORMAL_STATES = {
    "Mechanical_Guard": "Closed",
    "Electrical_Relay": "Engaged",
    "Software_E-Stop": "Energized"
}

# Anomaly budget (percentage of relevant records)
ANOMALY_BUDGET_PERCENT = 0.01

# =============================================================================
# RANDOM NUMBER GENERATOR INITIALIZATION
# =============================================================================

def init_rng(seed: int = SEED) -> np.random.Generator:
    """
    Initialize deterministic random number generators.

    Args:
        seed: Random seed for reproducibility. Defaults to SEED.

    Returns:
        NumPy random generator instance.
    """
    random.seed(seed)
    return np.random.default_rng(seed)


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def get_profile(profile_name: str) -> Dict[str, Any]:
    """
    Get profile configuration by name.

    Args:
        profile_name: Name of the profile ('dev' or 'full').

    Returns:
        Dictionary containing profile configuration.

    Raises:
        ValueError: If profile_name is not valid.
    """
    if profile_name not in PROFILES:
        raise ValueError(f"Invalid profile: {profile_name}. Must be one of {list(PROFILES.keys())}")
    return PROFILES[profile_name].copy()
