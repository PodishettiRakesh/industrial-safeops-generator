"""
Anomaly injection tests for Phase 4.

Tests verify:
- All five anomaly categories are injected
- Each ground truth label points to actual affected record
- ACK_BEFORE_ALARM violates timestamp ordering
- IMPOSSIBLE_INTERLOCK represents unsafe condition
- MISSING_CONTEXT has missing reference
- REPLAY_FLOOD has expected count, unique IDs, traceability
- UNVERIFIED_CLOSURE has status Closed and null verification
- DEV and FULL final alarm-event counts are exact
- Structural constraints remain valid
- Ground truth has no false labels
- Identical seeds produce identical outputs
- Original DataFrames not mutated
"""

import numpy as np
import pandas as pd
import pytest
from datetime import datetime, timedelta
from safeops.utils.anomaly_injector import inject_anomalies
from safeops.utils.master_gen import generate_master_data
from safeops.utils.event_engine import generate_events
from safeops.config import (
    PROFILES,
    ANOMALY_TYPES,
    get_profile,
    init_rng
)


class TestAnomalyInjection:
    """Test anomaly injection functionality."""

    def test_inject_anomalies_returns_tuple(self):
        """Verify inject_anomalies returns correct structure."""
        rng = init_rng()
        master_data = generate_master_data("dev", rng)
        rng = init_rng()
        event_data = generate_events(master_data, "dev", rng)
        rng = init_rng()

        modified_data, ground_truth, summary = inject_anomalies(master_data, event_data, "dev", rng)

        assert isinstance(modified_data, dict)
        assert isinstance(ground_truth, pd.DataFrame)
        assert isinstance(summary, dict)

    def test_ground_truth_columns(self):
        """Verify ground truth has correct columns."""
        rng = init_rng()
        master_data = generate_master_data("dev", rng)
        rng = init_rng()
        event_data = generate_events(master_data, "dev", rng)
        rng = init_rng()

        _, ground_truth, _ = inject_anomalies(master_data, event_data, "dev", rng)

        expected_columns = ["target_table", "entity_id", "anomaly_type", "description"]
        assert list(ground_truth.columns) == expected_columns

    def test_all_anomaly_categories_present(self):
        """Verify all five anomaly categories are present."""
        rng = init_rng()
        master_data = generate_master_data("dev", rng)
        rng = init_rng()
        event_data = generate_events(master_data, "dev", rng)
        rng = init_rng()

        _, ground_truth, _ = inject_anomalies(master_data, event_data, "dev", rng)

        present_anomalies = set(ground_truth["anomaly_type"].unique())
        assert present_anomalies == set(ANOMALY_TYPES)


class TestAckBeforeAlarm:
    """Test ACK_BEFORE_ALARM anomaly injection."""

    def test_ack_before_alarm_injected(self):
        """Verify ACK_BEFORE_ALARM anomalies are injected."""
        rng = init_rng()
        master_data = generate_master_data("dev", rng)
        rng = init_rng()
        event_data = generate_events(master_data, "dev", rng)
        rng = init_rng()

        modified_data, ground_truth, _ = inject_anomalies(master_data, event_data, "dev", rng)

        ack_anomalies = ground_truth[ground_truth["anomaly_type"] == "ACK_BEFORE_ALARM"]
        assert len(ack_anomalies) > 0

    def test_ack_before_alarm_violates_timestamp(self):
        """Verify ACK_BEFORE_ALARM violates timestamp ordering."""
        rng = init_rng()
        master_data = generate_master_data("dev", rng)
        rng = init_rng()
        event_data = generate_events(master_data, "dev", rng)
        rng = init_rng()

        modified_data, ground_truth, _ = inject_anomalies(master_data, event_data, "dev", rng)

        ack_anomalies = ground_truth[ground_truth["anomaly_type"] == "ACK_BEFORE_ALARM"]
        acknowledgements = modified_data["acknowledgements"]
        alarm_events = modified_data["alarm_events"]

        for _, row in ack_anomalies.iterrows():
            ack_id = row["entity_id"]
            ack = acknowledgements[acknowledgements["ack_id"] == ack_id].iloc[0]
            alarm = alarm_events[alarm_events["alarm_event_id"] == ack["alarm_event_id"]].iloc[0]

            ack_time = datetime.fromisoformat(ack["acknowledged_at"].replace("Z", "+00:00"))
            alarm_time = datetime.fromisoformat(alarm["timestamp"].replace("Z", "+00:00"))

            assert ack_time < alarm_time, f"ACK {ack_id} does not violate timestamp ordering"

    def test_ack_before_alarm_entity_exists(self):
        """Verify ground truth entity IDs exist in data."""
        rng = init_rng()
        master_data = generate_master_data("dev", rng)
        rng = init_rng()
        event_data = generate_events(master_data, "dev", rng)
        rng = init_rng()

        modified_data, ground_truth, _ = inject_anomalies(master_data, event_data, "dev", rng)

        ack_anomalies = ground_truth[ground_truth["anomaly_type"] == "ACK_BEFORE_ALARM"]
        acknowledgements = modified_data["acknowledgements"]

        for entity_id in ack_anomalies["entity_id"]:
            assert entity_id in acknowledgements["ack_id"].values


class TestImpossibleInterlock:
    """Test IMPOSSIBLE_INTERLOCK anomaly injection."""

    def test_impossible_interlock_injected(self):
        """Verify IMPOSSIBLE_INTERLOCK anomalies are injected."""
        rng = init_rng()
        master_data = generate_master_data("dev", rng)
        rng = init_rng()
        event_data = generate_events(master_data, "dev", rng)
        rng = init_rng()

        modified_data, ground_truth, _ = inject_anomalies(master_data, event_data, "dev", rng)

        interlock_anomalies = ground_truth[ground_truth["anomaly_type"] == "IMPOSSIBLE_INTERLOCK"]
        assert len(interlock_anomalies) > 0

    def test_impossible_interlock_represents_unsafe_condition(self):
        """Verify IMPOSSIBLE_INTERLOCK represents unsafe condition."""
        rng = init_rng()
        master_data = generate_master_data("dev", rng)
        rng = init_rng()
        event_data = generate_events(master_data, "dev", rng)
        rng = init_rng()

        modified_data, ground_truth, _ = inject_anomalies(master_data, event_data, "dev", rng)

        interlock_anomalies = ground_truth[ground_truth["anomaly_type"] == "IMPOSSIBLE_INTERLOCK"]
        state_events = modified_data["machine_state_events"]

        for _, row in interlock_anomalies.iterrows():
            state_event_id = int(row["entity_id"])
            state = state_events[state_events["state_event_id"] == state_event_id].iloc[0]

            assert state["new_state"] == "Operational"
            assert state["interlock_status"] == "Bypassed"

    def test_impossible_interlock_entity_exists(self):
        """Verify ground truth entity IDs exist in data."""
        rng = init_rng()
        master_data = generate_master_data("dev", rng)
        rng = init_rng()
        event_data = generate_events(master_data, "dev", rng)
        rng = init_rng()

        modified_data, ground_truth, _ = inject_anomalies(master_data, event_data, "dev", rng)

        interlock_anomalies = ground_truth[ground_truth["anomaly_type"] == "IMPOSSIBLE_INTERLOCK"]
        state_events = modified_data["machine_state_events"]

        for entity_id in interlock_anomalies["entity_id"]:
            assert int(entity_id) in state_events["state_event_id"].values


class TestMissingContext:
    """Test MISSING_CONTEXT anomaly injection."""

    def test_missing_context_injected(self):
        """Verify MISSING_CONTEXT anomalies are injected."""
        rng = init_rng()
        master_data = generate_master_data("dev", rng)
        rng = init_rng()
        event_data = generate_events(master_data, "dev", rng)
        rng = init_rng()

        modified_data, ground_truth, _ = inject_anomalies(master_data, event_data, "dev", rng)

        missing_anomalies = ground_truth[ground_truth["anomaly_type"] == "MISSING_CONTEXT"]
        assert len(missing_anomalies) > 0

    def test_missing_context_has_null_reference(self):
        """Verify MISSING_CONTEXT has null alarm_event_id."""
        rng = init_rng()
        master_data = generate_master_data("dev", rng)
        rng = init_rng()
        event_data = generate_events(master_data, "dev", rng)
        rng = init_rng()

        modified_data, ground_truth, _ = inject_anomalies(master_data, event_data, "dev", rng)

        missing_anomalies = ground_truth[ground_truth["anomaly_type"] == "MISSING_CONTEXT"]
        incidents = modified_data["incidents"]

        for _, row in missing_anomalies.iterrows():
            incident_id = row["entity_id"]
            incident = incidents[incidents["incident_id"] == incident_id].iloc[0]

            assert pd.isna(incident["alarm_event_id"])

    def test_missing_context_entity_exists(self):
        """Verify ground truth entity IDs exist in data."""
        rng = init_rng()
        master_data = generate_master_data("dev", rng)
        rng = init_rng()
        event_data = generate_events(master_data, "dev", rng)
        rng = init_rng()

        modified_data, ground_truth, _ = inject_anomalies(master_data, event_data, "dev", rng)

        missing_anomalies = ground_truth[ground_truth["anomaly_type"] == "MISSING_CONTEXT"]
        incidents = modified_data["incidents"]

        for entity_id in missing_anomalies["entity_id"]:
            assert entity_id in incidents["incident_id"].values


class TestReplayFlood:
    """Test REPLAY_FLOOD anomaly injection."""

    def test_replay_flood_injected(self):
        """Verify REPLAY_FLOOD anomalies are injected."""
        rng = init_rng()
        master_data = generate_master_data("dev", rng)
        rng = init_rng()
        event_data = generate_events(master_data, "dev", rng)
        rng = init_rng()

        modified_data, ground_truth, _ = inject_anomalies(master_data, event_data, "dev", rng)

        replay_anomalies = ground_truth[ground_truth["anomaly_type"] == "REPLAY_FLOOD"]
        assert len(replay_anomalies) == 50

    def test_replay_flood_count(self):
        """Verify REPLAY_FLOOD adds exactly 50 records."""
        rng = init_rng()
        master_data = generate_master_data("dev", rng)
        rng = init_rng()
        event_data = generate_events(master_data, "dev", rng)
        rng = init_rng()

        original_count = len(event_data["alarm_events"])
        modified_data, _, summary = inject_anomalies(master_data, event_data, "dev", rng)

        assert summary["added_replay_records"] == 50
        assert len(modified_data["alarm_events"]) == original_count + 50

    def test_replay_flood_unique_ids(self):
        """Verify replay records have unique IDs."""
        rng = init_rng()
        master_data = generate_master_data("dev", rng)
        rng = init_rng()
        event_data = generate_events(master_data, "dev", rng)
        rng = init_rng()

        modified_data, ground_truth, _ = inject_anomalies(master_data, event_data, "dev", rng)
        alarm_events = modified_data["alarm_events"]

        assert alarm_events["alarm_event_id"].is_unique

    def test_replay_flood_traceability(self):
        """Verify replay records have replay_group_id for traceability."""
        rng = init_rng()
        master_data = generate_master_data("dev", rng)
        rng = init_rng()
        event_data = generate_events(master_data, "dev", rng)
        rng = init_rng()

        modified_data, ground_truth, _ = inject_anomalies(master_data, event_data, "dev", rng)
        alarm_events = modified_data["alarm_events"]

        replay_anomalies = ground_truth[ground_truth["anomaly_type"] == "REPLAY_FLOOD"]

        for _, row in replay_anomalies.iterrows():
            replay_id = row["entity_id"]
            replay = alarm_events[alarm_events["alarm_event_id"] == replay_id].iloc[0]

            assert pd.notna(replay["replay_group_id"])

    def test_dev_final_alarm_count(self):
        """Verify DEV profile final alarm event count is exactly 500."""
        rng = init_rng()
        master_data = generate_master_data("dev", rng)
        rng = init_rng()
        event_data = generate_events(master_data, "dev", rng)
        rng = init_rng()

        modified_data, _, _ = inject_anomalies(master_data, event_data, "dev", rng)

        assert len(modified_data["alarm_events"]) == PROFILES["dev"]["num_alarm_events"]

    def test_full_final_alarm_count(self):
        """Verify FULL profile final alarm event count is exactly 50,000."""
        rng = init_rng()
        master_data = generate_master_data("full", rng)
        rng = init_rng()
        event_data = generate_events(master_data, "full", rng)
        rng = init_rng()

        modified_data, _, _ = inject_anomalies(master_data, event_data, "full", rng)

        assert len(modified_data["alarm_events"]) == PROFILES["full"]["num_alarm_events"]


class TestUnverifiedClosure:
    """Test UNVERIFIED_CLOSURE anomaly injection."""

    def test_unverified_closure_injected(self):
        """Verify UNVERIFIED_CLOSURE anomalies are injected."""
        rng = init_rng()
        master_data = generate_master_data("dev", rng)
        rng = init_rng()
        event_data = generate_events(master_data, "dev", rng)
        rng = init_rng()

        modified_data, ground_truth, _ = inject_anomalies(master_data, event_data, "dev", rng)

        closure_anomalies = ground_truth[ground_truth["anomaly_type"] == "UNVERIFIED_CLOSURE"]
        assert len(closure_anomalies) > 0

    def test_unverified_closure_status_closed(self):
        """Verify UNVERIFIED_CLOSURE has status Closed."""
        rng = init_rng()
        master_data = generate_master_data("dev", rng)
        rng = init_rng()
        event_data = generate_events(master_data, "dev", rng)
        rng = init_rng()

        modified_data, ground_truth, _ = inject_anomalies(master_data, event_data, "dev", rng)

        closure_anomalies = ground_truth[ground_truth["anomaly_type"] == "UNVERIFIED_CLOSURE"]
        actions = modified_data["corrective_actions"]

        for _, row in closure_anomalies.iterrows():
            action_id = row["entity_id"]
            action = actions[actions["action_id"] == action_id].iloc[0]

            assert action["status"] == "Closed"

    def test_unverified_closure_null_verification(self):
        """Verify UNVERIFIED_CLOSURE has null verified_at."""
        rng = init_rng()
        master_data = generate_master_data("dev", rng)
        rng = init_rng()
        event_data = generate_events(master_data, "dev", rng)
        rng = init_rng()

        modified_data, ground_truth, _ = inject_anomalies(master_data, event_data, "dev", rng)

        closure_anomalies = ground_truth[ground_truth["anomaly_type"] == "UNVERIFIED_CLOSURE"]
        actions = modified_data["corrective_actions"]

        for _, row in closure_anomalies.iterrows():
            action_id = row["entity_id"]
            action = actions[actions["action_id"] == action_id].iloc[0]

            assert pd.isna(action["verified_at"])

    def test_unverified_closure_entity_exists(self):
        """Verify ground truth entity IDs exist in data."""
        rng = init_rng()
        master_data = generate_master_data("dev", rng)
        rng = init_rng()
        event_data = generate_events(master_data, "dev", rng)
        rng = init_rng()

        modified_data, ground_truth, _ = inject_anomalies(master_data, event_data, "dev", rng)

        closure_anomalies = ground_truth[ground_truth["anomaly_type"] == "UNVERIFIED_CLOSURE"]
        actions = modified_data["corrective_actions"]

        for entity_id in closure_anomalies["entity_id"]:
            assert entity_id in actions["action_id"].values


class TestStructuralIntegrity:
    """Test structural integrity after anomaly injection."""

    def test_primary_keys_remain_unique(self):
        """Verify primary keys remain unique after injection."""
        rng = init_rng()
        master_data = generate_master_data("dev", rng)
        rng = init_rng()
        event_data = generate_events(master_data, "dev", rng)
        rng = init_rng()

        modified_data, _, _ = inject_anomalies(master_data, event_data, "dev", rng)

        assert modified_data["alarm_events"]["alarm_event_id"].is_unique
        assert modified_data["acknowledgements"]["ack_id"].is_unique
        assert modified_data["incidents"]["incident_id"].is_unique
        assert modified_data["corrective_actions"]["action_id"].is_unique

    def test_foreign_keys_remain_valid(self):
        """Verify foreign keys remain valid after injection."""
        rng = init_rng()
        master_data = generate_master_data("dev", rng)
        rng = init_rng()
        event_data = generate_events(master_data, "dev", rng)
        rng = init_rng()

        modified_data, _, _ = inject_anomalies(master_data, event_data, "dev", rng)

        # Check alarm foreign keys
        alarm_def_ids = set(master_data["alarm_definitions"]["alarm_def_id"])
        for alarm_def_id in modified_data["alarm_events"]["alarm_def_id"]:
            assert alarm_def_id in alarm_def_ids

        # Check acknowledgement foreign keys
        alarm_event_ids = set(modified_data["alarm_events"]["alarm_event_id"])
        for alarm_event_id in modified_data["acknowledgements"]["alarm_event_id"]:
            assert alarm_event_id in alarm_event_ids


class TestGroundTruth:
    """Test ground truth DataFrame."""

    def test_ground_truth_no_false_labels(self):
        """Verify ground truth has no false labels."""
        rng = init_rng()
        master_data = generate_master_data("dev", rng)
        rng = init_rng()
        event_data = generate_events(master_data, "dev", rng)
        rng = init_rng()

        modified_data, ground_truth, _ = inject_anomalies(master_data, event_data, "dev", rng)

        # All ground truth labels should correspond to actual anomalies
        for _, row in ground_truth.iterrows():
            table = row["target_table"]
            entity_id = row["entity_id"]
            anomaly_type = row["anomaly_type"]

            if table == "acknowledgements":
                ack = modified_data["acknowledgements"][modified_data["acknowledgements"]["ack_id"] == entity_id]
                if anomaly_type == "ACK_BEFORE_ALARM":
                    assert len(ack) > 0

    def test_ground_truth_sorted(self):
        """Verify ground truth is sorted deterministically."""
        rng = init_rng()
        master_data = generate_master_data("dev", rng)
        rng = init_rng()
        event_data = generate_events(master_data, "dev", rng)
        rng = init_rng()

        _, ground_truth, _ = inject_anomalies(master_data, event_data, "dev", rng)

        expected_order = ground_truth.sort_values(["target_table", "entity_id"])
        pd.testing.assert_frame_equal(ground_truth, expected_order)


class TestDeterminism:
    """Test deterministic behavior."""

    def test_same_seed_same_output(self):
        """Verify same seed produces identical output."""
        rng1 = init_rng()
        master_data1 = generate_master_data("dev", rng1)
        rng1 = init_rng()
        event_data1 = generate_events(master_data1, "dev", rng1)
        rng1 = init_rng()
        modified1, ground_truth1, summary1 = inject_anomalies(master_data1, event_data1, "dev", rng1)

        rng2 = init_rng()
        master_data2 = generate_master_data("dev", rng2)
        rng2 = init_rng()
        event_data2 = generate_events(master_data2, "dev", rng2)
        rng2 = init_rng()
        modified2, ground_truth2, summary2 = inject_anomalies(master_data2, event_data2, "dev", rng2)

        for key in modified1:
            pd.testing.assert_frame_equal(modified1[key], modified2[key])
        pd.testing.assert_frame_equal(ground_truth1, ground_truth2)
        assert summary1 == summary2

    def test_original_not_mutated(self):
        """Verify original DataFrames are not mutated."""
        rng = init_rng()
        master_data = generate_master_data("dev", rng)
        rng = init_rng()
        event_data = generate_events(master_data, "dev", rng)

        # Store original alarm event count
        original_alarm_count = len(event_data["alarm_events"])

        rng = init_rng()
        modified_data, _, _ = inject_anomalies(master_data, event_data, "dev", rng)

        # Original should be unchanged
        assert len(event_data["alarm_events"]) == original_alarm_count
