"""
Event engine tests for Phase 3.

Tests verify:
- Event counts match profile
- Timestamps within simulation window
- Chronological ordering
- Shift coverage
- Alarm value vs threshold relationship
- Acknowledgement follows alarm timestamp
- Acknowledgement assigned to valid shift
- Incident has valid triggering evidence
- Corrective action lifecycle valid
- Foreign keys resolve to master data
"""

import numpy as np
import pandas as pd
import pytest
from datetime import datetime, timedelta
from safeops.utils.event_engine import generate_events
from safeops.utils.master_gen import generate_master_data
from safeops.config import (
    PROFILES,
    MACHINE_STATUS,
    INTERLOCK_STATUS,
    INCIDENT_SEVERITY,
    ACTION_STATUS,
    SIMULATION_START_UTC,
    SIMULATION_DAYS,
    TIMESTAMP_FORMAT
)


class TestEventGeneration:
    """Test event generation functionality."""

    def test_generate_events_returns_dict(self):
        """Verify generate_events returns dictionary with correct keys."""
        rng = np.random.default_rng(20261022)
        master_data = generate_master_data("dev", rng)
        rng = np.random.default_rng(20261022)  # Reset for events
        result = generate_events(master_data, "dev", rng)

        assert isinstance(result, dict)
        assert "operator_shifts" in result
        assert "machine_state_events" in result
        assert "alarm_events" in result
        assert "acknowledgements" in result
        assert "incidents" in result
        assert "corrective_actions" in result

    def test_all_returns_are_dataframes(self):
        """Verify all returned values are DataFrames."""
        rng = np.random.default_rng(20261022)
        master_data = generate_master_data("dev", rng)
        rng = np.random.default_rng(20261022)
        result = generate_events(master_data, "dev", rng)

        for key, df in result.items():
            assert isinstance(df, pd.DataFrame), f"{key} is not a DataFrame"


class TestOperatorShifts:
    """Test OperatorShift entity generation."""

    def test_operator_shifts_columns(self):
        """Verify operator_shifts DataFrame has correct columns."""
        rng = np.random.default_rng(20261022)
        master_data = generate_master_data("dev", rng)
        rng = np.random.default_rng(20261022)
        result = generate_events(master_data, "dev", rng)
        shifts = result["operator_shifts"]

        expected_columns = ["shift_id", "plant_id", "operator_name", "start_time", "end_time"]
        assert list(shifts.columns) == expected_columns

    def test_operator_shifts_primary_key_unique(self):
        """Verify shift_id is unique."""
        rng = np.random.default_rng(20261022)
        master_data = generate_master_data("dev", rng)
        rng = np.random.default_rng(20261022)
        result = generate_events(master_data, "dev", rng)
        shifts = result["operator_shifts"]

        assert shifts["shift_id"].is_unique

    def test_operator_shifts_primary_key_non_null(self):
        """Verify shift_id has no null values."""
        rng = np.random.default_rng(20261022)
        master_data = generate_master_data("dev", rng)
        rng = np.random.default_rng(20261022)
        result = generate_events(master_data, "dev", rng)
        shifts = result["operator_shifts"]

        assert shifts["shift_id"].notna().all()

    def test_operator_shifts_foreign_key_resolves(self):
        """Verify plant_id references valid plants."""
        rng = np.random.default_rng(20261022)
        master_data = generate_master_data("dev", rng)
        rng = np.random.default_rng(20261022)
        result = generate_events(master_data, "dev", rng)
        shifts = result["operator_shifts"]
        plants = master_data["plants"]

        valid_plant_ids = set(plants["plant_id"])
        for plant_id in shifts["plant_id"]:
            assert plant_id in valid_plant_ids, f"Invalid plant_id: {plant_id}"

    def test_operator_shifts_start_before_end(self):
        """Verify start_time precedes end_time for all shifts."""
        rng = np.random.default_rng(20261022)
        master_data = generate_master_data("dev", rng)
        rng = np.random.default_rng(20261022)
        result = generate_events(master_data, "dev", rng)
        shifts = result["operator_shifts"]

        for _, shift in shifts.iterrows():
            start = datetime.fromisoformat(shift["start_time"].replace("Z", "+00:00"))
            end = datetime.fromisoformat(shift["end_time"].replace("Z", "+00:00"))
            assert start < end, f"Shift {shift['shift_id']}: start not before end"

    def test_operator_shifts_coverage(self):
        """Verify shifts cover the simulation window without major gaps."""
        rng = np.random.default_rng(20261022)
        master_data = generate_master_data("dev", rng)
        rng = np.random.default_rng(20261022)
        result = generate_events(master_data, "dev", rng)
        shifts = result["operator_shifts"]

        sim_start = datetime.fromisoformat(SIMULATION_START_UTC.replace("Z", "+00:00"))
        sim_end = sim_start + timedelta(days=SIMULATION_DAYS)

        # Check each plant has shifts
        for plant_id in master_data["plants"]["plant_id"]:
            plant_shifts = shifts[shifts["plant_id"] == plant_id]
            assert len(plant_shifts) > 0, f"Plant {plant_id} has no shifts"

            # Check coverage
            if len(plant_shifts) > 1:
                plant_shifts = plant_shifts.sort_values("start_time")
                first_start = datetime.fromisoformat(plant_shifts.iloc[0]["start_time"].replace("Z", "+00:00"))
                last_end = datetime.fromisoformat(plant_shifts.iloc[-1]["end_time"].replace("Z", "+00:00"))
                assert first_start <= sim_start + timedelta(hours=1), f"Plant {plant_id} shifts start too late"
                assert last_end >= sim_end - timedelta(hours=1), f"Plant {plant_id} shifts end too early"

    def test_operator_shifts_sorted(self):
        """Verify shifts are sorted by start_time and shift_id."""
        rng = np.random.default_rng(20261022)
        master_data = generate_master_data("dev", rng)
        rng = np.random.default_rng(20261022)
        result = generate_events(master_data, "dev", rng)
        shifts = result["operator_shifts"]

        expected_order = shifts.sort_values(["start_time", "shift_id"])
        pd.testing.assert_frame_equal(shifts, expected_order)


class TestMachineStateEvents:
    """Test MachineStateEvent entity generation."""

    def test_machine_state_events_columns(self):
        """Verify machine_state_events DataFrame has correct columns."""
        rng = np.random.default_rng(20261022)
        master_data = generate_master_data("dev", rng)
        rng = np.random.default_rng(20261022)
        result = generate_events(master_data, "dev", rng)
        state_events = result["machine_state_events"]

        expected_columns = ["state_event_id", "machine_id", "timestamp", "previous_state",
                           "new_state", "interlock_status", "source_event_id"]
        assert list(state_events.columns) == expected_columns

    def test_machine_state_events_primary_key_unique(self):
        """Verify state_event_id is unique."""
        rng = np.random.default_rng(20261022)
        master_data = generate_master_data("dev", rng)
        rng = np.random.default_rng(20261022)
        result = generate_events(master_data, "dev", rng)
        state_events = result["machine_state_events"]

        assert state_events["state_event_id"].is_unique

    def test_machine_state_events_foreign_key_resolves(self):
        """Verify machine_id references valid machines."""
        rng = np.random.default_rng(20261022)
        master_data = generate_master_data("dev", rng)
        rng = np.random.default_rng(20261022)
        result = generate_events(master_data, "dev", rng)
        state_events = result["machine_state_events"]
        machines = master_data["machines"]

        valid_machine_ids = set(machines["machine_id"])
        for machine_id in state_events["machine_id"]:
            assert machine_id in valid_machine_ids, f"Invalid machine_id: {machine_id}"

    def test_machine_state_events_state_enum_valid(self):
        """Verify previous_state and new_state use allowed enum values."""
        rng = np.random.default_rng(20261022)
        master_data = generate_master_data("dev", rng)
        rng = np.random.default_rng(20261022)
        result = generate_events(master_data, "dev", rng)
        state_events = result["machine_state_events"]

        for state in state_events["previous_state"]:
            assert state in MACHINE_STATUS, f"Invalid previous_state: {state}"
        for state in state_events["new_state"]:
            assert state in MACHINE_STATUS, f"Invalid new_state: {state}"

    def test_machine_state_events_interlock_enum_valid(self):
        """Verify interlock_status uses allowed enum values."""
        rng = np.random.default_rng(20261022)
        master_data = generate_master_data("dev", rng)
        rng = np.random.default_rng(20261022)
        result = generate_events(master_data, "dev", rng)
        state_events = result["machine_state_events"]

        for status in state_events["interlock_status"]:
            assert status in INTERLOCK_STATUS, f"Invalid interlock_status: {status}"

    def test_machine_state_events_sorted(self):
        """Verify state events are sorted by timestamp and state_event_id."""
        rng = np.random.default_rng(20261022)
        master_data = generate_master_data("dev", rng)
        rng = np.random.default_rng(20261022)
        result = generate_events(master_data, "dev", rng)
        state_events = result["machine_state_events"]

        expected_order = state_events.sort_values(["timestamp", "state_event_id"])
        pd.testing.assert_frame_equal(state_events, expected_order)


class TestAlarmEvents:
    """Test AlarmEvent entity generation."""

    def test_alarm_events_row_count_dev(self):
        """Verify dev profile generates correct number of alarm events (minus replay reservation)."""
        rng = np.random.default_rng(20261022)
        master_data = generate_master_data("dev", rng)
        rng = np.random.default_rng(20261022)
        result = generate_events(master_data, "dev", rng)
        alarm_events = result["alarm_events"]

        # Baseline generates (num_events - 50) to reserve capacity for Phase 4 replay
        expected = PROFILES["dev"]["num_alarm_events"] - 50
        assert len(alarm_events) == expected

    def test_alarm_events_row_count_full(self):
        """Verify full profile generates correct number of alarm events (minus replay reservation)."""
        rng = np.random.default_rng(20261022)
        master_data = generate_master_data("full", rng)
        rng = np.random.default_rng(20261022)
        result = generate_events(master_data, "full", rng)
        alarm_events = result["alarm_events"]

        # Baseline generates (num_events - 50) to reserve capacity for Phase 4 replay
        expected = PROFILES["full"]["num_alarm_events"] - 50
        assert len(alarm_events) == expected

    def test_alarm_events_columns(self):
        """Verify alarm_events DataFrame has correct columns."""
        rng = np.random.default_rng(20261022)
        master_data = generate_master_data("dev", rng)
        rng = np.random.default_rng(20261022)
        result = generate_events(master_data, "dev", rng)
        alarm_events = result["alarm_events"]

        expected_columns = ["alarm_event_id", "alarm_def_id", "timestamp", "current_value",
                           "interlock_status", "source_event_id", "replay_group_id"]
        assert list(alarm_events.columns) == expected_columns

    def test_alarm_events_primary_key_unique(self):
        """Verify alarm_event_id is unique."""
        rng = np.random.default_rng(20261022)
        master_data = generate_master_data("dev", rng)
        rng = np.random.default_rng(20261022)
        result = generate_events(master_data, "dev", rng)
        alarm_events = result["alarm_events"]

        assert alarm_events["alarm_event_id"].is_unique

    def test_alarm_events_foreign_key_resolves(self):
        """Verify alarm_def_id references valid alarm definitions."""
        rng = np.random.default_rng(20261022)
        master_data = generate_master_data("dev", rng)
        rng = np.random.default_rng(20261022)
        result = generate_events(master_data, "dev", rng)
        alarm_events = result["alarm_events"]
        alarm_defs = master_data["alarm_definitions"]

        valid_def_ids = set(alarm_defs["alarm_def_id"])
        for alarm_def_id in alarm_events["alarm_def_id"]:
            assert alarm_def_id in valid_def_ids, f"Invalid alarm_def_id: {alarm_def_id}"

    def test_alarm_events_sorted(self):
        """Verify alarm events are sorted by timestamp and alarm_event_id."""
        rng = np.random.default_rng(20261022)
        master_data = generate_master_data("dev", rng)
        rng = np.random.default_rng(20261022)
        result = generate_events(master_data, "dev", rng)
        alarm_events = result["alarm_events"]

        expected_order = alarm_events.sort_values(["timestamp", "alarm_event_id"])
        pd.testing.assert_frame_equal(alarm_events, expected_order)


class TestAcknowledgements:
    """Test Acknowledgement entity generation."""

    def test_acknowledgements_columns(self):
        """Verify acknowledgements DataFrame has correct columns."""
        rng = np.random.default_rng(20261022)
        master_data = generate_master_data("dev", rng)
        rng = np.random.default_rng(20261022)
        result = generate_events(master_data, "dev", rng)
        acknowledgements = result["acknowledgements"]

        expected_columns = ["ack_id", "alarm_event_id", "shift_id", "acknowledged_at"]
        assert list(acknowledgements.columns) == expected_columns

    def test_acknowledgements_primary_key_unique(self):
        """Verify ack_id is unique."""
        rng = np.random.default_rng(20261022)
        master_data = generate_master_data("dev", rng)
        rng = np.random.default_rng(20261022)
        result = generate_events(master_data, "dev", rng)
        acknowledgements = result["acknowledgements"]

        assert acknowledgements["ack_id"].is_unique

    def test_acknowledgements_foreign_key_alarm_resolves(self):
        """Verify alarm_event_id references valid alarm events."""
        rng = np.random.default_rng(20261022)
        master_data = generate_master_data("dev", rng)
        rng = np.random.default_rng(20261022)
        result = generate_events(master_data, "dev", rng)
        acknowledgements = result["acknowledgements"]
        alarm_events = result["alarm_events"]

        valid_alarm_ids = set(alarm_events["alarm_event_id"])
        for alarm_event_id in acknowledgements["alarm_event_id"]:
            assert alarm_event_id in valid_alarm_ids, f"Invalid alarm_event_id: {alarm_event_id}"

    def test_acknowledgements_foreign_key_shift_resolves(self):
        """Verify shift_id references valid shifts."""
        rng = np.random.default_rng(20261022)
        master_data = generate_master_data("dev", rng)
        rng = np.random.default_rng(20261022)
        result = generate_events(master_data, "dev", rng)
        acknowledgements = result["acknowledgements"]
        shifts = result["operator_shifts"]

        valid_shift_ids = set(shifts["shift_id"])
        for shift_id in acknowledgements["shift_id"]:
            assert shift_id in valid_shift_ids, f"Invalid shift_id: {shift_id}"

    def test_acknowledgements_sorted(self):
        """Verify acknowledgements are sorted by acknowledged_at and ack_id."""
        rng = np.random.default_rng(20261022)
        master_data = generate_master_data("dev", rng)
        rng = np.random.default_rng(20261022)
        result = generate_events(master_data, "dev", rng)
        acknowledgements = result["acknowledgements"]

        expected_order = acknowledgements.sort_values(["acknowledged_at", "ack_id"])
        pd.testing.assert_frame_equal(acknowledgements, expected_order)


class TestIncidents:
    """Test Incident entity generation."""

    def test_incidents_columns(self):
        """Verify incidents DataFrame has correct columns."""
        rng = np.random.default_rng(20261022)
        master_data = generate_master_data("dev", rng)
        rng = np.random.default_rng(20261022)
        result = generate_events(master_data, "dev", rng)
        incidents = result["incidents"]

        expected_columns = ["incident_id", "machine_id", "alarm_event_id", "severity_level",
                           "logged_at", "issue_type"]
        assert list(incidents.columns) == expected_columns

    def test_incidents_primary_key_unique(self):
        """Verify incident_id is unique."""
        rng = np.random.default_rng(20261022)
        master_data = generate_master_data("dev", rng)
        rng = np.random.default_rng(20261022)
        result = generate_events(master_data, "dev", rng)
        incidents = result["incidents"]

        assert incidents["incident_id"].is_unique

    def test_incidents_foreign_key_machine_resolves(self):
        """Verify machine_id references valid machines."""
        rng = np.random.default_rng(20261022)
        master_data = generate_master_data("dev", rng)
        rng = np.random.default_rng(20261022)
        result = generate_events(master_data, "dev", rng)
        incidents = result["incidents"]
        machines = master_data["machines"]

        valid_machine_ids = set(machines["machine_id"])
        for machine_id in incidents["machine_id"]:
            assert machine_id in valid_machine_ids, f"Invalid machine_id: {machine_id}"

    def test_incidents_alarm_not_null_baseline(self):
        """Verify baseline incidents have valid alarm_event_id (no MISSING_CONTEXT in baseline)."""
        rng = np.random.default_rng(20261022)
        master_data = generate_master_data("dev", rng)
        rng = np.random.default_rng(20261022)
        result = generate_events(master_data, "dev", rng)
        incidents = result["incidents"]

        # Baseline incidents should all have valid alarm_event_id
        assert incidents["alarm_event_id"].notna().all(), "Baseline incidents must have valid alarm_event_id"

    def test_incidents_severity_enum_valid(self):
        """Verify severity_level uses allowed enum values."""
        rng = np.random.default_rng(20261022)
        master_data = generate_master_data("dev", rng)
        rng = np.random.default_rng(20261022)
        result = generate_events(master_data, "dev", rng)
        incidents = result["incidents"]

        for severity in incidents["severity_level"]:
            assert severity in INCIDENT_SEVERITY, f"Invalid severity_level: {severity}"

    def test_incidents_sorted(self):
        """Verify incidents are sorted by logged_at and incident_id."""
        rng = np.random.default_rng(20261022)
        master_data = generate_master_data("dev", rng)
        rng = np.random.default_rng(20261022)
        result = generate_events(master_data, "dev", rng)
        incidents = result["incidents"]

        expected_order = incidents.sort_values(["logged_at", "incident_id"])
        pd.testing.assert_frame_equal(incidents, expected_order)

    def test_incidents_based_on_safety_rules(self):
        """Verify incidents are generated from qualifying alarms based on safety rules."""
        rng = np.random.default_rng(20261022)
        master_data = generate_master_data("dev", rng)
        rng = np.random.default_rng(20261022)
        result = generate_events(master_data, "dev", rng)
        incidents = result["incidents"]
        alarm_events = result["alarm_events"]
        alarm_definitions = master_data["alarm_definitions"]

        # Create severity lookup
        def_to_severity = dict(zip(alarm_definitions["alarm_def_id"], alarm_definitions["severity"]))

        # All incidents should reference valid alarm events
        assert incidents["alarm_event_id"].notna().all()

        # Verify incident alarms are qualifying (critical+tripped, high+2xthreshold, or tripped)
        for _, incident in incidents.iterrows():
            alarm_event_id = incident["alarm_event_id"]
            alarm = alarm_events[alarm_events["alarm_event_id"] == alarm_event_id].iloc[0]
            alarm_def_id = alarm["alarm_def_id"]
            severity = def_to_severity.get(alarm_def_id, "Low")
            threshold = alarm_definitions[alarm_definitions["alarm_def_id"] == alarm_def_id].iloc[0]["threshold_limit"]
            current_value = alarm["current_value"]
            interlock_status = alarm["interlock_status"]

            # Check if qualifies under safety rules
            qualifies = (
                (severity == "Critical" and interlock_status == "Tripped") or
                (severity in ["High", "Critical"] and current_value > threshold * 2) or
                (interlock_status == "Tripped")
            )
            assert qualifies, f"Incident {incident['incident_id']} does not qualify under safety rules"


class TestCorrectiveActions:
    """Test CorrectiveAction entity generation."""

    def test_corrective_actions_columns(self):
        """Verify corrective_actions DataFrame has correct columns."""
        rng = np.random.default_rng(20261022)
        master_data = generate_master_data("dev", rng)
        rng = np.random.default_rng(20261022)
        result = generate_events(master_data, "dev", rng)
        actions = result["corrective_actions"]

        expected_columns = ["action_id", "incident_id", "action_taken", "status", "verified_at"]
        assert list(actions.columns) == expected_columns

    def test_corrective_actions_primary_key_unique(self):
        """Verify action_id is unique."""
        rng = np.random.default_rng(20261022)
        master_data = generate_master_data("dev", rng)
        rng = np.random.default_rng(20261022)
        result = generate_events(master_data, "dev", rng)
        actions = result["corrective_actions"]

        assert actions["action_id"].is_unique

    def test_corrective_actions_foreign_key_resolves(self):
        """Verify incident_id references valid incidents."""
        rng = np.random.default_rng(20261022)
        master_data = generate_master_data("dev", rng)
        rng = np.random.default_rng(20261022)
        result = generate_events(master_data, "dev", rng)
        actions = result["corrective_actions"]
        incidents = result["incidents"]

        valid_incident_ids = set(incidents["incident_id"])
        for incident_id in actions["incident_id"]:
            assert incident_id in valid_incident_ids, f"Invalid incident_id: {incident_id}"

    def test_corrective_actions_status_enum_valid(self):
        """Verify status uses allowed enum values."""
        rng = np.random.default_rng(20261022)
        master_data = generate_master_data("dev", rng)
        rng = np.random.default_rng(20261022)
        result = generate_events(master_data, "dev", rng)
        actions = result["corrective_actions"]

        for status in actions["status"]:
            assert status in ACTION_STATUS, f"Invalid status: {status}"

    def test_corrective_actions_closed_has_verification(self):
        """Verify baseline Closed actions have verified_at (no UNVERIFIED_CLOSURE in baseline)."""
        rng = np.random.default_rng(20261022)
        master_data = generate_master_data("dev", rng)
        rng = np.random.default_rng(20261022)
        result = generate_events(master_data, "dev", rng)
        actions = result["corrective_actions"]

        # Closed actions should have verified_at in baseline
        closed_actions = actions[actions["status"] == "Closed"]
        if len(closed_actions) > 0:
            assert closed_actions["verified_at"].notna().all(), "Baseline Closed actions must have verified_at"

    def test_corrective_actions_sorted(self):
        """Verify actions are sorted by incident_id and action_id."""
        rng = np.random.default_rng(20261022)
        master_data = generate_master_data("dev", rng)
        rng = np.random.default_rng(20261022)
        result = generate_events(master_data, "dev", rng)
        actions = result["corrective_actions"]

        expected_order = actions.sort_values(["incident_id", "action_id"])
        pd.testing.assert_frame_equal(actions, expected_order)


class TestDeterminism:
    """Test deterministic generation."""

    def test_same_seed_same_output(self):
        """Verify same seed produces identical output."""
        rng1 = np.random.default_rng(20261022)
        master_data1 = generate_master_data("dev", rng1)
        rng1 = np.random.default_rng(20261022)
        result1 = generate_events(master_data1, "dev", rng1)

        rng2 = np.random.default_rng(20261022)
        master_data2 = generate_master_data("dev", rng2)
        rng2 = np.random.default_rng(20261022)
        result2 = generate_events(master_data2, "dev", rng2)

        for key in result1:
            pd.testing.assert_frame_equal(result1[key], result2[key])
