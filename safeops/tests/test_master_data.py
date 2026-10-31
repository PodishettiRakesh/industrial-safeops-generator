"""
Master data generation tests for Phase 2.

Tests verify:
- Exact row counts per profile
- Primary key uniqueness
- Foreign key references resolve
- Enum values are valid
- ID formats match patterns
- Deterministic generation
- created_at precedes simulation start
"""

import re
import numpy as np
import pandas as pd
import pytest
from safeops.utils.master_gen import generate_master_data
from safeops.config import (
    PROFILES,
    MACHINE_TYPES,
    MACHINE_STATUS,
    ZONE_TYPES,
    RISK_LEVELS,
    INTERLOCK_TYPES,
    INTERLOCK_STATES,
    METRIC_NAMES,
    SEVERITY_LEVELS,
    SIMULATION_START_UTC,
    ID_PATTERNS
)


class TestMasterDataGeneration:
    """Test master data generation functionality."""

    def test_generate_master_data_returns_dict(self):
        """Verify generate_master_data returns dictionary with correct keys."""
        rng = np.random.default_rng(20261022)
        result = generate_master_data("dev", rng)

        assert isinstance(result, dict)
        assert "plants" in result
        assert "machines" in result
        assert "safety_zones" in result
        assert "interlocks" in result
        assert "alarm_definitions" in result

    def test_all_returns_are_dataframes(self):
        """Verify all returned values are DataFrames."""
        rng = np.random.default_rng(20261022)
        result = generate_master_data("dev", rng)

        for key, df in result.items():
            assert isinstance(df, pd.DataFrame), f"{key} is not a DataFrame"


class TestPlants:
    """Test Plant entity generation."""

    def test_plants_row_count_dev(self):
        """Verify dev profile generates correct number of plants."""
        rng = np.random.default_rng(20261022)
        result = generate_master_data("dev", rng)
        plants = result["plants"]

        assert len(plants) == PROFILES["dev"]["num_plants"]

    def test_plants_row_count_full(self):
        """Verify full profile generates correct number of plants."""
        rng = np.random.default_rng(20261022)
        result = generate_master_data("full", rng)
        plants = result["plants"]

        assert len(plants) == PROFILES["full"]["num_plants"]

    def test_plants_columns(self):
        """Verify plants DataFrame has correct columns."""
        rng = np.random.default_rng(20261022)
        result = generate_master_data("dev", rng)
        plants = result["plants"]

        expected_columns = ["plant_id", "plant_name", "location", "created_at"]
        assert list(plants.columns) == expected_columns

    def test_plants_primary_key_unique(self):
        """Verify plant_id is unique."""
        rng = np.random.default_rng(20261022)
        result = generate_master_data("dev", rng)
        plants = result["plants"]

        assert plants["plant_id"].is_unique

    def test_plants_primary_key_non_null(self):
        """Verify plant_id has no null values."""
        rng = np.random.default_rng(20261022)
        result = generate_master_data("dev", rng)
        plants = result["plants"]

        assert plants["plant_id"].notna().all()

    def test_plants_id_format(self):
        """Verify plant_id matches format pattern."""
        rng = np.random.default_rng(20261022)
        result = generate_master_data("dev", rng)
        plants = result["plants"]

        pattern = re.compile(ID_PATTERNS["plant"])
        for plant_id in plants["plant_id"]:
            assert pattern.match(plant_id), f"Invalid plant_id format: {plant_id}"

    def test_plants_name_unique(self):
        """Verify plant_name is unique."""
        rng = np.random.default_rng(20261022)
        result = generate_master_data("dev", rng)
        plants = result["plants"]

        assert plants["plant_name"].is_unique

    def test_plants_created_at_before_simulation(self):
        """Verify created_at precedes simulation start."""
        rng = np.random.default_rng(20261022)
        result = generate_master_data("dev", rng)
        plants = result["plants"]

        for created_at in plants["created_at"]:
            assert created_at < SIMULATION_START_UTC

    def test_plants_sorted_by_id(self):
        """Verify plants are sorted by plant_id."""
        rng = np.random.default_rng(20261022)
        result = generate_master_data("dev", rng)
        plants = result["plants"]

        assert list(plants["plant_id"]) == sorted(plants["plant_id"])


class TestMachines:
    """Test Machine entity generation."""

    def test_machines_row_count_dev(self):
        """Verify dev profile generates correct number of machines."""
        rng = np.random.default_rng(20261022)
        result = generate_master_data("dev", rng)
        machines = result["machines"]

        assert len(machines) == PROFILES["dev"]["num_machines"]

    def test_machines_row_count_full(self):
        """Verify full profile generates correct number of machines."""
        rng = np.random.default_rng(20261022)
        result = generate_master_data("full", rng)
        machines = result["machines"]

        assert len(machines) == PROFILES["full"]["num_machines"]

    def test_machines_columns(self):
        """Verify machines DataFrame has correct columns."""
        rng = np.random.default_rng(20261022)
        result = generate_master_data("dev", rng)
        machines = result["machines"]

        expected_columns = ["machine_id", "plant_id", "machine_type", "model_number", "status"]
        assert list(machines.columns) == expected_columns

    def test_machines_primary_key_unique(self):
        """Verify machine_id is unique."""
        rng = np.random.default_rng(20261022)
        result = generate_master_data("dev", rng)
        machines = result["machines"]

        assert machines["machine_id"].is_unique

    def test_machines_primary_key_non_null(self):
        """Verify machine_id has no null values."""
        rng = np.random.default_rng(20261022)
        result = generate_master_data("dev", rng)
        machines = result["machines"]

        assert machines["machine_id"].notna().all()

    def test_machines_id_format(self):
        """Verify machine_id matches format pattern."""
        rng = np.random.default_rng(20261022)
        result = generate_master_data("dev", rng)
        machines = result["machines"]

        pattern = re.compile(ID_PATTERNS["machine"])
        for machine_id in machines["machine_id"]:
            assert pattern.match(machine_id), f"Invalid machine_id format: {machine_id}"

    def test_machines_foreign_key_resolves(self):
        """Verify plant_id references valid plants."""
        rng = np.random.default_rng(20261022)
        result = generate_master_data("dev", rng)
        machines = result["machines"]
        plants = result["plants"]

        valid_plant_ids = set(plants["plant_id"])
        for plant_id in machines["plant_id"]:
            assert plant_id in valid_plant_ids, f"Invalid plant_id: {plant_id}"

    def test_machines_type_enum_valid(self):
        """Verify machine_type uses allowed enum values."""
        rng = np.random.default_rng(20261022)
        result = generate_master_data("dev", rng)
        machines = result["machines"]

        for machine_type in machines["machine_type"]:
            assert machine_type in MACHINE_TYPES, f"Invalid machine_type: {machine_type}"

    def test_machines_status_enum_valid(self):
        """Verify status uses allowed enum values."""
        rng = np.random.default_rng(20261022)
        result = generate_master_data("dev", rng)
        machines = result["machines"]

        for status in machines["status"]:
            assert status in MACHINE_STATUS, f"Invalid status: {status}"

    def test_machines_model_number_unique(self):
        """Verify model_number is unique or appropriately constrained."""
        rng = np.random.default_rng(20261022)
        result = generate_master_data("dev", rng)
        machines = result["machines"]

        # Model numbers should be unique per our generation logic
        assert machines["model_number"].is_unique

    def test_machines_sorted_by_id(self):
        """Verify machines are sorted by machine_id."""
        rng = np.random.default_rng(20261022)
        result = generate_master_data("dev", rng)
        machines = result["machines"]

        assert list(machines["machine_id"]) == sorted(machines["machine_id"])


class TestSafetyZones:
    """Test SafetyZone entity generation."""

    def test_safety_zones_columns(self):
        """Verify safety_zones DataFrame has correct columns."""
        rng = np.random.default_rng(20261022)
        result = generate_master_data("dev", rng)
        safety_zones = result["safety_zones"]

        expected_columns = ["zone_id", "machine_id", "zone_type", "risk_level"]
        assert list(safety_zones.columns) == expected_columns

    def test_safety_zones_primary_key_unique(self):
        """Verify zone_id is unique."""
        rng = np.random.default_rng(20261022)
        result = generate_master_data("dev", rng)
        safety_zones = result["safety_zones"]

        assert safety_zones["zone_id"].is_unique

    def test_safety_zones_primary_key_non_null(self):
        """Verify zone_id has no null values."""
        rng = np.random.default_rng(20261022)
        result = generate_master_data("dev", rng)
        safety_zones = result["safety_zones"]

        assert safety_zones["zone_id"].notna().all()

    def test_safety_zones_id_format(self):
        """Verify zone_id matches format pattern."""
        rng = np.random.default_rng(20261022)
        result = generate_master_data("dev", rng)
        safety_zones = result["safety_zones"]

        pattern = re.compile(ID_PATTERNS["zone"])
        for zone_id in safety_zones["zone_id"]:
            assert pattern.match(zone_id), f"Invalid zone_id format: {zone_id}"

    def test_safety_zones_foreign_key_resolves(self):
        """Verify machine_id references valid machines."""
        rng = np.random.default_rng(20261022)
        result = generate_master_data("dev", rng)
        safety_zones = result["safety_zones"]
        machines = result["machines"]

        valid_machine_ids = set(machines["machine_id"])
        for machine_id in safety_zones["machine_id"]:
            assert machine_id in valid_machine_ids, f"Invalid machine_id: {machine_id}"

    def test_safety_zones_type_enum_valid(self):
        """Verify zone_type uses allowed enum values."""
        rng = np.random.default_rng(20261022)
        result = generate_master_data("dev", rng)
        safety_zones = result["safety_zones"]

        for zone_type in safety_zones["zone_type"]:
            assert zone_type in ZONE_TYPES, f"Invalid zone_type: {zone_type}"

    def test_safety_zones_risk_enum_valid(self):
        """Verify risk_level uses allowed enum values."""
        rng = np.random.default_rng(20261022)
        result = generate_master_data("dev", rng)
        safety_zones = result["safety_zones"]

        for risk_level in safety_zones["risk_level"]:
            assert risk_level in RISK_LEVELS, f"Invalid risk_level: {risk_level}"

    def test_safety_zones_sorted_by_id(self):
        """Verify safety_zones are sorted by zone_id."""
        rng = np.random.default_rng(20261022)
        result = generate_master_data("dev", rng)
        safety_zones = result["safety_zones"]

        assert list(safety_zones["zone_id"]) == sorted(safety_zones["zone_id"])


class TestInterlocks:
    """Test Interlock entity generation."""

    def test_interlocks_columns(self):
        """Verify interlocks DataFrame has correct columns."""
        rng = np.random.default_rng(20261022)
        result = generate_master_data("dev", rng)
        interlocks = result["interlocks"]

        expected_columns = ["interlock_id", "machine_id", "interlock_type", "normal_state"]
        assert list(interlocks.columns) == expected_columns

    def test_interlocks_primary_key_unique(self):
        """Verify interlock_id is unique."""
        rng = np.random.default_rng(20261022)
        result = generate_master_data("dev", rng)
        interlocks = result["interlocks"]

        assert interlocks["interlock_id"].is_unique

    def test_interlocks_primary_key_non_null(self):
        """Verify interlock_id has no null values."""
        rng = np.random.default_rng(20261022)
        result = generate_master_data("dev", rng)
        interlocks = result["interlocks"]

        assert interlocks["interlock_id"].notna().all()

    def test_interlocks_id_format(self):
        """Verify interlock_id matches format pattern."""
        rng = np.random.default_rng(20261022)
        result = generate_master_data("dev", rng)
        interlocks = result["interlocks"]

        pattern = re.compile(ID_PATTERNS["interlock"])
        for interlock_id in interlocks["interlock_id"]:
            assert pattern.match(interlock_id), f"Invalid interlock_id format: {interlock_id}"

    def test_interlocks_foreign_key_resolves(self):
        """Verify machine_id references valid machines."""
        rng = np.random.default_rng(20261022)
        result = generate_master_data("dev", rng)
        interlocks = result["interlocks"]
        machines = result["machines"]

        valid_machine_ids = set(machines["machine_id"])
        for machine_id in interlocks["machine_id"]:
            assert machine_id in valid_machine_ids, f"Invalid machine_id: {machine_id}"

    def test_interlocks_type_enum_valid(self):
        """Verify interlock_type uses allowed enum values."""
        rng = np.random.default_rng(20261022)
        result = generate_master_data("dev", rng)
        interlocks = result["interlocks"]

        for interlock_type in interlocks["interlock_type"]:
            assert interlock_type in INTERLOCK_TYPES, f"Invalid interlock_type: {interlock_type}"

    def test_interlocks_state_enum_valid(self):
        """Verify normal_state uses allowed enum values."""
        rng = np.random.default_rng(20261022)
        result = generate_master_data("dev", rng)
        interlocks = result["interlocks"]

        for normal_state in interlocks["normal_state"]:
            assert normal_state in INTERLOCK_STATES, f"Invalid normal_state: {normal_state}"

    def test_interlocks_sorted_by_id(self):
        """Verify interlocks are sorted by interlock_id."""
        rng = np.random.default_rng(20261022)
        result = generate_master_data("dev", rng)
        interlocks = result["interlocks"]

        assert list(interlocks["interlock_id"]) == sorted(interlocks["interlock_id"])


class TestAlarmDefinitions:
    """Test AlarmDefinition entity generation."""

    def test_alarm_definitions_row_count_dev(self):
        """Verify dev profile generates correct number of alarm definitions."""
        rng = np.random.default_rng(20261022)
        result = generate_master_data("dev", rng)
        alarm_definitions = result["alarm_definitions"]

        assert len(alarm_definitions) == PROFILES["dev"]["num_alarm_definitions"]

    def test_alarm_definitions_row_count_full(self):
        """Verify full profile generates correct number of alarm definitions."""
        rng = np.random.default_rng(20261022)
        result = generate_master_data("full", rng)
        alarm_definitions = result["alarm_definitions"]

        assert len(alarm_definitions) == PROFILES["full"]["num_alarm_definitions"]

    def test_alarm_definitions_columns(self):
        """Verify alarm_definitions DataFrame has correct columns."""
        rng = np.random.default_rng(20261022)
        result = generate_master_data("dev", rng)
        alarm_definitions = result["alarm_definitions"]

        expected_columns = ["alarm_def_id", "machine_id", "metric_name", "severity", "threshold_limit"]
        assert list(alarm_definitions.columns) == expected_columns

    def test_alarm_definitions_primary_key_unique(self):
        """Verify alarm_def_id is unique."""
        rng = np.random.default_rng(20261022)
        result = generate_master_data("dev", rng)
        alarm_definitions = result["alarm_definitions"]

        assert alarm_definitions["alarm_def_id"].is_unique

    def test_alarm_definitions_primary_key_non_null(self):
        """Verify alarm_def_id has no null values."""
        rng = np.random.default_rng(20261022)
        result = generate_master_data("dev", rng)
        alarm_definitions = result["alarm_definitions"]

        assert alarm_definitions["alarm_def_id"].notna().all()

    def test_alarm_definitions_id_format(self):
        """Verify alarm_def_id matches format pattern."""
        rng = np.random.default_rng(20261022)
        result = generate_master_data("dev", rng)
        alarm_definitions = result["alarm_definitions"]

        pattern = re.compile(ID_PATTERNS["alarm_def"])
        for alarm_def_id in alarm_definitions["alarm_def_id"]:
            assert pattern.match(alarm_def_id), f"Invalid alarm_def_id format: {alarm_def_id}"

    def test_alarm_definitions_foreign_key_resolves(self):
        """Verify machine_id references valid machines."""
        rng = np.random.default_rng(20261022)
        result = generate_master_data("dev", rng)
        alarm_definitions = result["alarm_definitions"]
        machines = result["machines"]

        valid_machine_ids = set(machines["machine_id"])
        for machine_id in alarm_definitions["machine_id"]:
            assert machine_id in valid_machine_ids, f"Invalid machine_id: {machine_id}"

    def test_alarm_definitions_metric_enum_valid(self):
        """Verify metric_name uses allowed enum values."""
        rng = np.random.default_rng(20261022)
        result = generate_master_data("dev", rng)
        alarm_definitions = result["alarm_definitions"]

        for metric_name in alarm_definitions["metric_name"]:
            assert metric_name in METRIC_NAMES, f"Invalid metric_name: {metric_name}"

    def test_alarm_definitions_severity_enum_valid(self):
        """Verify severity uses allowed enum values."""
        rng = np.random.default_rng(20261022)
        result = generate_master_data("dev", rng)
        alarm_definitions = result["alarm_definitions"]

        for severity in alarm_definitions["severity"]:
            assert severity in SEVERITY_LEVELS, f"Invalid severity: {severity}"

    def test_alarm_definitions_threshold_non_null(self):
        """Verify threshold_limit has no null values."""
        rng = np.random.default_rng(20261022)
        result = generate_master_data("dev", rng)
        alarm_definitions = result["alarm_definitions"]

        assert alarm_definitions["threshold_limit"].notna().all()

    def test_alarm_definitions_sorted_by_id(self):
        """Verify alarm_definitions are sorted by alarm_def_id."""
        rng = np.random.default_rng(20261022)
        result = generate_master_data("dev", rng)
        alarm_definitions = result["alarm_definitions"]

        assert list(alarm_definitions["alarm_def_id"]) == sorted(alarm_definitions["alarm_def_id"])


class TestDeterminism:
    """Test deterministic generation."""

    def test_same_seed_same_output(self):
        """Verify same seed produces identical output."""
        rng1 = np.random.default_rng(20261022)
        result1 = generate_master_data("dev", rng1)

        rng2 = np.random.default_rng(20261022)
        result2 = generate_master_data("dev", rng2)

        for key in result1:
            pd.testing.assert_frame_equal(result1[key], result2[key])

    def test_different_seed_different_output(self):
        """Verify different seed produces different output."""
        rng1 = np.random.default_rng(20261022)
        result1 = generate_master_data("dev", rng1)

        rng2 = np.random.default_rng(20261023)
        result2 = generate_master_data("dev", rng2)

        # At least one entity should differ
        differs = False
        for key in result1:
            try:
                pd.testing.assert_frame_equal(result1[key], result2[key])
            except AssertionError:
                differs = True
                break

        assert differs, "Different seed should produce different output"
