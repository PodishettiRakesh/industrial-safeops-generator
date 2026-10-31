"""
Master data generation module.

This module generates Plant, Machine, SafetyZone, Interlock, and AlarmDefinition entities.
"""

import pandas as pd
import numpy as np
from typing import Dict
from safeops.config import (
    get_profile,
    MACHINE_TYPES,
    MACHINE_STATUS,
    ZONE_TYPES,
    RISK_LEVELS,
    INTERLOCK_TYPES,
    INTERLOCK_NORMAL_STATES,
    METRIC_NAMES,
    SEVERITY_LEVELS,
    METRIC_RANGES,
    INTERLOCK_STATES
)


def generate_master_data(profile: str, rng: np.random.Generator) -> Dict[str, pd.DataFrame]:
    """
    Generate all master data entities in dependency order.

    Args:
        profile: Profile name ('dev' or 'full').
        rng: Random number generator.

    Returns:
        Dictionary of DataFrames keyed by entity name.
    """
    profile_config = get_profile(profile)

    # Generate in dependency order
    plants = generate_plants(profile_config["num_plants"], rng)
    machines = generate_machines(plants, profile_config["num_machines"], rng)
    safety_zones = generate_safety_zones(machines, rng)
    interlocks = generate_interlocks(machines, rng)
    alarm_definitions = generate_alarm_definitions(machines, profile_config["num_alarm_definitions"], rng)

    return {
        "plants": plants,
        "machines": machines,
        "safety_zones": safety_zones,
        "interlocks": interlocks,
        "alarm_definitions": alarm_definitions
    }


def generate_plants(num_plants: int, rng: np.random.Generator) -> pd.DataFrame:
    """
    Generate Plant entities.

    Args:
        num_plants: Number of plants to generate.
        rng: Random number generator.

    Returns:
        DataFrame with columns: plant_id, plant_name, location, created_at
    """
    plant_names = [
        "Factory Alpha",
        "Factory Beta",
        "Factory Gamma",
        "Factory Delta",
        "Factory Epsilon",
        "Factory Zeta",
        "Factory Eta",
        "Factory Theta"
    ]

    locations = [
        "Detroit, MI",
        "Chicago, IL",
        "Houston, TX",
        "Phoenix, AZ",
        "Seattle, WA",
        "Denver, CO",
        "Atlanta, GA",
        "Boston, MA"
    ]

    data = []
    for i in range(num_plants):
        plant_id = f"PLT-{i+1:03d}"
        # Use RNG for deterministic selection
        plant_name = plant_names[rng.integers(0, len(plant_names))]
        location = locations[rng.integers(0, len(locations))]
        created_at = "2025-12-01T00:00:00Z"  # Before simulation start
        data.append({
            "plant_id": plant_id,
            "plant_name": plant_name,
            "location": location,
            "created_at": created_at
        })

    df = pd.DataFrame(data)
    df = df.sort_values("plant_id").reset_index(drop=True)
    return df


def generate_machines(plants: pd.DataFrame, num_machines: int, rng: np.random.Generator) -> pd.DataFrame:
    """
    Generate Machine entities.

    Args:
        plants: DataFrame of plants.
        num_machines: Number of machines to generate.
        rng: Random number generator.

    Returns:
        DataFrame with columns: machine_id, plant_id, machine_type, model_number, status
    """
    plant_ids = plants["plant_id"].tolist()

    data = []
    for i in range(num_machines):
        machine_id = f"MCH-{i+1:03d}"
        # Assign to plant using RNG for deterministic selection
        plant_id = plant_ids[rng.integers(0, len(plant_ids))]
        # Select machine type using RNG
        machine_type = MACHINE_TYPES[rng.integers(0, len(MACHINE_TYPES))]
        # Generate model number based on type and index
        model_number = f"{machine_type.replace('_', '-')}-MK-{i+1:03d}"
        status = "Operational"  # All start operational

        data.append({
            "machine_id": machine_id,
            "plant_id": plant_id,
            "machine_type": machine_type,
            "model_number": model_number,
            "status": status
        })

    df = pd.DataFrame(data)
    df = df.sort_values("machine_id").reset_index(drop=True)
    return df


def generate_safety_zones(machines: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    """
    Generate SafetyZone entities.

    Args:
        machines: DataFrame of machines.
        rng: Random number generator.

    Returns:
        DataFrame with columns: zone_id, machine_id, zone_type, risk_level
    """
    data = []
    zone_counter = {}  # Track zone counter per plant

    for _, machine in machines.iterrows():
        machine_id = machine["machine_id"]
        plant_id = machine["plant_id"]
        machine_type = machine["machine_type"]

        # Each machine gets 1-3 zones using RNG
        num_zones = rng.integers(1, 4)

        # Initialize plant counter if needed
        if plant_id not in zone_counter:
            zone_counter[plant_id] = 0

        for z in range(num_zones):
            zone_counter[plant_id] += 1
            zone_id = f"SAFE-{plant_id}-{zone_counter[plant_id]:03d}"

            # Select zone type using RNG
            zone_type = ZONE_TYPES[rng.integers(0, len(ZONE_TYPES))]

            # Risk level using RNG
            risk_level = RISK_LEVELS[rng.integers(0, len(RISK_LEVELS))]

            data.append({
                "zone_id": zone_id,
                "machine_id": machine_id,
                "zone_type": zone_type,
                "risk_level": risk_level
            })

    df = pd.DataFrame(data)
    df = df.sort_values("zone_id").reset_index(drop=True)
    return df


def generate_interlocks(machines: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    """
    Generate Interlock entities.

    Args:
        machines: DataFrame of machines.
        rng: Random number generator.

    Returns:
        DataFrame with columns: interlock_id, machine_id, interlock_type, normal_state
    """
    data = []
    interlock_counter = 0

    for _, machine in machines.iterrows():
        machine_id = machine["machine_id"]

        # Each machine gets 2-4 interlocks using RNG
        num_interlocks = rng.integers(2, 5)

        for i in range(num_interlocks):
            interlock_counter += 1
            interlock_id = f"INT-{interlock_counter:04d}"

            # Select interlock type using RNG
            interlock_type = INTERLOCK_TYPES[rng.integers(0, len(INTERLOCK_TYPES))]

            # Normal state based on interlock type
            normal_state = INTERLOCK_NORMAL_STATES[interlock_type]

            data.append({
                "interlock_id": interlock_id,
                "machine_id": machine_id,
                "interlock_type": interlock_type,
                "normal_state": normal_state
            })

    df = pd.DataFrame(data)
    df = df.sort_values("interlock_id").reset_index(drop=True)
    return df


def generate_alarm_definitions(
    machines: pd.DataFrame,
    num_definitions: int,
    rng: np.random.Generator
) -> pd.DataFrame:
    """
    Generate AlarmDefinition entities.

    Args:
        machines: DataFrame of machines.
        num_definitions: Number of alarm definitions to generate.
        rng: Random number generator.

    Returns:
        DataFrame with columns: alarm_def_id, machine_id, metric_name, severity, threshold_limit
    """
    machine_ids = machines["machine_id"].tolist()

    data = []
    for i in range(num_definitions):
        alarm_def_id = f"DEF-{i+1:04d}"

        # Assign to machine using RNG
        machine_id = machine_ids[rng.integers(0, len(machine_ids))]

        # Select metric name using RNG
        metric_name = METRIC_NAMES[rng.integers(0, len(METRIC_NAMES))]

        # Select severity using RNG
        severity = SEVERITY_LEVELS[rng.integers(0, len(SEVERITY_LEVELS))]

        # Threshold based on metric range and severity
        metric_range = METRIC_RANGES[metric_name]
        min_val, max_val = metric_range

        # Higher severity = lower threshold (easier to breach)
        severity_multiplier = {
            "Low": 0.9,
            "Medium": 0.7,
            "High": 0.5,
            "Critical": 0.3
        }
        threshold = min_val + (max_val - min_val) * severity_multiplier[severity]

        data.append({
            "alarm_def_id": alarm_def_id,
            "machine_id": machine_id,
            "metric_name": metric_name,
            "severity": severity,
            "threshold_limit": round(threshold, 2)
        })

    df = pd.DataFrame(data)
    df = df.sort_values("alarm_def_id").reset_index(drop=True)
    return df
