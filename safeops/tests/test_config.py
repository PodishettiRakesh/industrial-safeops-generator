"""
Configuration tests for Phase 1.

Tests verify:
- SEED value
- Profile parameters
- RNG initialization consistency
- Enum definitions
- ID pattern validity
- Metric units and ranges
"""

import re
import random
import numpy as np
import pytest
from safeops.config import (
    SEED,
    PROFILES,
    MACHINE_TYPES,
    MACHINE_STATUS,
    ZONE_TYPES,
    RISK_LEVELS,
    INTERLOCK_TYPES,
    INTERLOCK_STATES,
    METRIC_NAMES,
    SEVERITY_LEVELS,
    INTERLOCK_STATUS,
    INCIDENT_SEVERITY,
    ACTION_STATUS,
    ANOMALY_TYPES,
    ID_PATTERNS,
    METRIC_UNITS,
    METRIC_RANGES,
    init_rng,
    get_profile
)


class TestSeed:
    """Test seed configuration."""

    def test_seed_value(self):
        """Verify SEED is set to the required value."""
        assert SEED == 20261022


class TestProfiles:
    """Test profile configuration."""

    def test_dev_profile_exists(self):
        """Verify dev profile exists."""
        assert "dev" in PROFILES

    def test_full_profile_exists(self):
        """Verify full profile exists."""
        assert "full" in PROFILES

    def test_dev_profile_parameters(self):
        """Verify dev profile parameters match specifications."""
        dev = PROFILES["dev"]
        assert dev["num_plants"] == 2
        assert dev["num_machines"] == 5
        assert dev["num_alarm_definitions"] == 10
        assert dev["num_alarm_events"] == 500
        assert dev["shortened_window"] is True

    def test_full_profile_parameters(self):
        """Verify full profile parameters match specifications."""
        full = PROFILES["full"]
        assert full["num_plants"] == 4
        assert full["num_machines"] == 60
        assert full["num_alarm_definitions"] == 200
        assert full["num_alarm_events"] == 50000
        assert full["shortened_window"] is False

    def test_get_profile_valid(self):
        """Verify get_profile returns copy of profile."""
        dev = get_profile("dev")
        assert dev["num_plants"] == 2
        # Modify returned profile should not affect original
        dev["num_plants"] = 999
        assert PROFILES["dev"]["num_plants"] == 2

    def test_get_profile_invalid(self):
        """Verify get_profile raises error for invalid profile."""
        with pytest.raises(ValueError, match="Invalid profile"):
            get_profile("invalid")


class TestEnums:
    """Test enum value definitions."""

    def test_machine_types_non_empty(self):
        """Verify machine types are defined."""
        assert len(MACHINE_TYPES) > 0
        assert "CNC_Mill" in MACHINE_TYPES
        assert "Robotic_Arm" in MACHINE_TYPES
        assert "Stamping_Press" in MACHINE_TYPES
        assert "Furnace" in MACHINE_TYPES

    def test_machine_status_non_empty(self):
        """Verify machine status values are defined."""
        assert len(MACHINE_STATUS) > 0
        assert "Operational" in MACHINE_STATUS
        assert "Maintenance" in MACHINE_STATUS
        assert "Offline" in MACHINE_STATUS

    def test_zone_types_non_empty(self):
        """Verify zone types are defined."""
        assert len(ZONE_TYPES) > 0
        assert "Perimeter_Laser" in ZONE_TYPES
        assert "Pressure_Mat" in ZONE_TYPES
        assert "Proximity_Radar" in ZONE_TYPES

    def test_risk_levels_non_empty(self):
        """Verify risk levels are defined."""
        assert len(RISK_LEVELS) > 0
        assert "Low" in RISK_LEVELS
        assert "Medium" in RISK_LEVELS
        assert "High" in RISK_LEVELS
        assert "Critical" in RISK_LEVELS

    def test_interlock_types_non_empty(self):
        """Verify interlock types are defined."""
        assert len(INTERLOCK_TYPES) > 0
        assert "Mechanical_Guard" in INTERLOCK_TYPES
        assert "Electrical_Relay" in INTERLOCK_TYPES
        assert "Software_E-Stop" in INTERLOCK_TYPES

    def test_interlock_states_non_empty(self):
        """Verify interlock states are defined."""
        assert len(INTERLOCK_STATES) > 0
        assert "Closed" in INTERLOCK_STATES
        assert "Engaged" in INTERLOCK_STATES
        assert "Energized" in INTERLOCK_STATES

    def test_metric_names_non_empty(self):
        """Verify metric names are defined."""
        assert len(METRIC_NAMES) > 0
        assert "Temperature" in METRIC_NAMES
        assert "Vibration" in METRIC_NAMES
        assert "Pressure" in METRIC_NAMES
        assert "Voltage" in METRIC_NAMES

    def test_severity_levels_non_empty(self):
        """Verify severity levels are defined."""
        assert len(SEVERITY_LEVELS) > 0
        assert "Low" in SEVERITY_LEVELS
        assert "Medium" in SEVERITY_LEVELS
        assert "High" in SEVERITY_LEVELS
        assert "Critical" in SEVERITY_LEVELS

    def test_interlock_status_non_empty(self):
        """Verify interlock status values are defined."""
        assert len(INTERLOCK_STATUS) > 0
        assert "Secure" in INTERLOCK_STATUS
        assert "Tripped" in INTERLOCK_STATUS
        assert "Bypassed" in INTERLOCK_STATUS

    def test_incident_severity_non_empty(self):
        """Verify incident severity values are defined."""
        assert len(INCIDENT_SEVERITY) > 0
        assert "Major" in INCIDENT_SEVERITY
        assert "Critical" in INCIDENT_SEVERITY
        assert "Catastrophic" in INCIDENT_SEVERITY

    def test_action_status_non_empty(self):
        """Verify action status values are defined."""
        assert len(ACTION_STATUS) > 0
        assert "Open" in ACTION_STATUS
        assert "In_Progress" in ACTION_STATUS
        assert "Closed" in ACTION_STATUS


class TestAnomalyTypes:
    """Test anomaly type definitions."""

    def test_anomaly_types_complete(self):
        """Verify all 5 required anomaly types are defined."""
        assert len(ANOMALY_TYPES) == 5
        assert "ACK_BEFORE_ALARM" in ANOMALY_TYPES
        assert "IMPOSSIBLE_INTERLOCK" in ANOMALY_TYPES
        assert "MISSING_CONTEXT" in ANOMALY_TYPES
        assert "REPLAY_FLOOD" in ANOMALY_TYPES
        assert "UNVERIFIED_CLOSURE" in ANOMALY_TYPES


class TestIdPatterns:
    """Test ID pattern regex validity."""

    def test_id_patterns_compile(self):
        """Verify all ID patterns compile as valid regex."""
        for name, pattern in ID_PATTERNS.items():
            try:
                re.compile(pattern)
            except re.error as e:
                pytest.fail(f"ID pattern '{name}' is invalid regex: {e}")

    def test_plant_id_pattern(self):
        """Verify plant ID pattern matches expected format."""
        pattern = re.compile(ID_PATTERNS["plant"])
        assert pattern.match("PLT-001")
        assert pattern.match("PLT-999")
        assert not pattern.match("PLT-1")
        assert not pattern.match("PLT-001A")

    def test_machine_id_pattern(self):
        """Verify machine ID pattern matches expected format."""
        pattern = re.compile(ID_PATTERNS["machine"])
        assert pattern.match("MCH-001")
        assert pattern.match("MCH-999")
        assert not pattern.match("MCH-1")
        assert not pattern.match("MCH-001A")

    def test_zone_id_pattern(self):
        """Verify zone ID pattern matches expected format."""
        pattern = re.compile(ID_PATTERNS["zone"])
        assert pattern.match("SAFE-PLT-001-001")
        assert pattern.match("SAFE-PLT-999-999")
        assert not pattern.match("SAFE-PLT-1-001")
        assert not pattern.match("SAFE-PLT-001-1")


class TestMetricUnits:
    """Test metric units configuration."""

    def test_metric_units_defined(self):
        """Verify all metrics have units defined."""
        for metric in METRIC_NAMES:
            assert metric in METRIC_UNITS

    def test_metric_ranges_defined(self):
        """Verify all metrics have ranges defined."""
        for metric in METRIC_NAMES:
            assert metric in METRIC_RANGES
            assert len(METRIC_RANGES[metric]) == 2
            assert METRIC_RANGES[metric][0] < METRIC_RANGES[metric][1]


class TestRngInitialization:
    """Test RNG initialization and determinism."""

    def test_init_rng_returns_generator(self):
        """Verify init_rng returns NumPy generator."""
        rng = init_rng()
        assert isinstance(rng, np.random.Generator)

    def test_rng_determinism_same_seed(self):
        """Verify same seed produces same first random value."""
        rng1 = init_rng(SEED)
        val1 = rng1.random()
        rng2 = init_rng(SEED)
        val2 = rng2.random()
        assert val1 == val2

    def test_rng_determinism_different_seeds(self):
        """Verify different seeds produce different first random value."""
        rng1 = init_rng(SEED)
        val1 = rng1.random()
        rng2 = init_rng(SEED + 1)
        val2 = rng2.random()
        assert val1 != val2

    def test_python_random_seeded(self):
        """Verify Python random module is also seeded."""
        init_rng(SEED)
        val1 = random.random()
        init_rng(SEED)
        val2 = random.random()
        assert val1 == val2
