"""
Validation tests for Phase 5.

Tests verify:
- Valid generated datasets pass structural checks
- Each of the five injected anomalies is detected
- Ground-truth labels are reconciled correctly
- Unexpected structural errors are reported
- Invalid primary and foreign keys are detected
- Incorrect row counts are detected
- Missing or extra columns are detected
- Repeated validation returns equivalent results
- DEV and FULL profiles are supported
"""

import numpy as np
import pandas as pd
import pytest
from safeops.validate import validate
from safeops.utils.master_gen import generate_master_data
from safeops.utils.event_engine import generate_events
from safeops.utils.anomaly_injector import inject_anomalies
from safeops.config import init_rng, get_profile


class TestStructuralValidation:
    """Test structural integrity validation."""

    def test_valid_data_passes_structural_checks(self):
        """Verify valid generated datasets pass structural checks."""
        rng = init_rng()
        master_data = generate_master_data("dev", rng)
        rng = init_rng()
        event_data = generate_events(master_data, "dev", rng)
        rng = init_rng()
        modified_data, ground_truth, _ = inject_anomalies(master_data, event_data, "dev", rng)

        # Combine all data
        all_data = {**master_data, **modified_data}

        report = validate(all_data, ground_truth, "dev")

        assert report["structural_integrity"] == "pass"
        assert len(report["structural_errors"]) == 0

    def test_missing_table_detected(self):
        """Verify missing tables are detected."""
        rng = init_rng()
        master_data = generate_master_data("dev", rng)
        rng = init_rng()
        event_data = generate_events(master_data, "dev", rng)
        rng = init_rng()
        modified_data, ground_truth, _ = inject_anomalies(master_data, event_data, "dev", rng)

        # Remove a table
        all_data = {**master_data, **modified_data}
        del all_data["plants"]

        report = validate(all_data, ground_truth, "dev")

        assert report["structural_integrity"] == "fail"
        assert any(e["type"] == "missing_table" for e in report["structural_errors"])

    def test_duplicate_primary_key_detected(self):
        """Verify duplicate primary keys are detected."""
        rng = init_rng()
        master_data = generate_master_data("dev", rng)
        rng = init_rng()
        event_data = generate_events(master_data, "dev", rng)
        rng = init_rng()
        modified_data, ground_truth, _ = inject_anomalies(master_data, event_data, "dev", rng)

        # Duplicate a row
        all_data = {**master_data, **modified_data}
        plants = all_data["plants"].copy()
        plants = pd.concat([plants, plants.iloc[[0]]], ignore_index=True)
        all_data["plants"] = plants

        report = validate(all_data, ground_truth, "dev")

        assert report["structural_integrity"] == "fail"
        assert any(e["type"] == "duplicate_primary_key" for e in report["structural_errors"])

    def test_invalid_foreign_key_detected(self):
        """Verify invalid foreign keys are detected."""
        rng = init_rng()
        master_data = generate_master_data("dev", rng)
        rng = init_rng()
        event_data = generate_events(master_data, "dev", rng)
        rng = init_rng()
        modified_data, ground_truth, _ = inject_anomalies(master_data, event_data, "dev", rng)

        # Corrupt a foreign key
        all_data = {**master_data, **modified_data}
        machines = all_data["machines"].copy()
        machines.at[0, "plant_id"] = "INVALID-PLT"
        all_data["machines"] = machines

        report = validate(all_data, ground_truth, "dev")

        assert report["structural_integrity"] == "fail"
        assert any(e["type"] == "invalid_foreign_key" for e in report["structural_errors"])

    def test_invalid_enum_detected(self):
        """Verify invalid enum values are detected."""
        rng = init_rng()
        master_data = generate_master_data("dev", rng)
        rng = init_rng()
        event_data = generate_events(master_data, "dev", rng)
        rng = init_rng()
        modified_data, ground_truth, _ = inject_anomalies(master_data, event_data, "dev", rng)

        # Corrupt an enum value
        all_data = {**master_data, **modified_data}
        machines = all_data["machines"].copy()
        machines.at[0, "machine_type"] = "INVALID_TYPE"
        all_data["machines"] = machines

        report = validate(all_data, ground_truth, "dev")

        assert report["structural_integrity"] == "fail"
        assert any(e["type"] == "invalid_enum" for e in report["structural_errors"])

    def test_row_count_mismatch_detected(self):
        """Verify incorrect row counts are detected."""
        rng = init_rng()
        master_data = generate_master_data("dev", rng)
        rng = init_rng()
        event_data = generate_events(master_data, "dev", rng)
        rng = init_rng()
        modified_data, ground_truth, _ = inject_anomalies(master_data, event_data, "dev", rng)

        # Remove rows to cause count mismatch
        all_data = {**master_data, **modified_data}
        all_data["alarm_events"] = all_data["alarm_events"].iloc[:-10]

        report = validate(all_data, ground_truth, "dev")

        assert report["structural_integrity"] == "fail"
        assert any(e["type"] == "row_count_mismatch" for e in report["structural_errors"])

    def test_column_mismatch_detected(self):
        """Verify column mismatches are detected."""
        rng = init_rng()
        master_data = generate_master_data("dev", rng)
        rng = init_rng()
        event_data = generate_events(master_data, "dev", rng)
        rng = init_rng()
        modified_data, ground_truth, _ = inject_anomalies(master_data, event_data, "dev", rng)

        # Add extra column
        all_data = {**master_data, **modified_data}
        plants = all_data["plants"].copy()
        plants["extra_column"] = "value"
        all_data["plants"] = plants

        report = validate(all_data, ground_truth, "dev")

        assert report["structural_integrity"] == "fail"
        assert any(e["type"] == "column_mismatch" for e in report["structural_errors"])


class TestAnomalyDetection:
    """Test anomaly detection."""

    def test_ack_before_alarm_detected(self):
        """Verify ACK_BEFORE_ALARM anomalies are detected."""
        rng = init_rng()
        master_data = generate_master_data("dev", rng)
        rng = init_rng()
        event_data = generate_events(master_data, "dev", rng)
        rng = init_rng()
        modified_data, ground_truth, _ = inject_anomalies(master_data, event_data, "dev", rng)

        all_data = {**master_data, **modified_data}
        report = validate(all_data, ground_truth, "dev")

        assert "ACK_BEFORE_ALARM" in report["detected_anomalies"]
        assert len(report["detected_anomalies"]["ACK_BEFORE_ALARM"]) > 0

    def test_impossible_interlock_detected(self):
        """Verify IMPOSSIBLE_INTERLOCK anomalies are detected."""
        rng = init_rng()
        master_data = generate_master_data("dev", rng)
        rng = init_rng()
        event_data = generate_events(master_data, "dev", rng)
        rng = init_rng()
        modified_data, ground_truth, _ = inject_anomalies(master_data, event_data, "dev", rng)

        all_data = {**master_data, **modified_data}
        report = validate(all_data, ground_truth, "dev")

        assert "IMPOSSIBLE_INTERLOCK" in report["detected_anomalies"]
        assert len(report["detected_anomalies"]["IMPOSSIBLE_INTERLOCK"]) > 0

    def test_missing_context_detected(self):
        """Verify MISSING_CONTEXT anomalies are detected."""
        rng = init_rng()
        master_data = generate_master_data("dev", rng)
        rng = init_rng()
        event_data = generate_events(master_data, "dev", rng)
        rng = init_rng()
        modified_data, ground_truth, _ = inject_anomalies(master_data, event_data, "dev", rng)

        all_data = {**master_data, **modified_data}
        report = validate(all_data, ground_truth, "dev")

        assert "MISSING_CONTEXT" in report["detected_anomalies"]
        assert len(report["detected_anomalies"]["MISSING_CONTEXT"]) > 0

    def test_replay_flood_detected(self):
        """Verify REPLAY_FLOOD anomalies are detected."""
        rng = init_rng()
        master_data = generate_master_data("dev", rng)
        rng = init_rng()
        event_data = generate_events(master_data, "dev", rng)
        rng = init_rng()
        modified_data, ground_truth, _ = inject_anomalies(master_data, event_data, "dev", rng)

        all_data = {**master_data, **modified_data}
        report = validate(all_data, ground_truth, "dev")

        assert "REPLAY_FLOOD" in report["detected_anomalies"]
        assert len(report["detected_anomalies"]["REPLAY_FLOOD"]) == 50

    def test_unverified_closure_detected(self):
        """Verify UNVERIFIED_CLOSURE anomalies are detected."""
        rng = init_rng()
        master_data = generate_master_data("dev", rng)
        rng = init_rng()
        event_data = generate_events(master_data, "dev", rng)
        rng = init_rng()
        modified_data, ground_truth, _ = inject_anomalies(master_data, event_data, "dev", rng)

        all_data = {**master_data, **modified_data}
        report = validate(all_data, ground_truth, "dev")

        assert "UNVERIFIED_CLOSURE" in report["detected_anomalies"]
        assert len(report["detected_anomalies"]["UNVERIFIED_CLOSURE"]) > 0


class TestGroundTruthReconciliation:
    """Test ground truth reconciliation."""

    def test_ground_truth_reconciliation(self):
        """Verify ground truth labels are reconciled correctly."""
        rng = init_rng()
        master_data = generate_master_data("dev", rng)
        rng = init_rng()
        event_data = generate_events(master_data, "dev", rng)
        rng = init_rng()
        modified_data, ground_truth, _ = inject_anomalies(master_data, event_data, "dev", rng)

        all_data = {**master_data, **modified_data}
        report = validate(all_data, ground_truth, "dev")

        reconciliation = report["ground_truth_reconciliation"]

        # All 5 categories should be present
        assert len(reconciliation) == 5

        # Each category should have reconciliation metrics
        for anomaly_type in reconciliation:
            assert "ground_truth_count" in reconciliation[anomaly_type]
            assert "detected_count" in reconciliation[anomaly_type]
            assert "matched_count" in reconciliation[anomaly_type]
            assert "missed_labels" in reconciliation[anomaly_type]
            assert "unlabelled_detections" in reconciliation[anomaly_type]

    def test_no_missed_labels(self):
        """Verify all ground truth labels are detected (no missed labels)."""
        rng = init_rng()
        master_data = generate_master_data("dev", rng)
        rng = init_rng()
        event_data = generate_events(master_data, "dev", rng)
        rng = init_rng()
        modified_data, ground_truth, _ = inject_anomalies(master_data, event_data, "dev", rng)

        all_data = {**master_data, **modified_data}
        report = validate(all_data, ground_truth, "dev")

        reconciliation = report["ground_truth_reconciliation"]

        # All categories should have 0 missed labels
        for anomaly_type in reconciliation:
            assert reconciliation[anomaly_type]["missed_labels"] == 0

    def test_no_unlabelled_detections(self):
        """Verify no detections are missing from ground truth."""
        rng = init_rng()
        master_data = generate_master_data("dev", rng)
        rng = init_rng()
        event_data = generate_events(master_data, "dev", rng)
        rng = init_rng()
        modified_data, ground_truth, _ = inject_anomalies(master_data, event_data, "dev", rng)

        all_data = {**master_data, **modified_data}
        report = validate(all_data, ground_truth, "dev")

        reconciliation = report["ground_truth_reconciliation"]

        # All categories should have 0 unlabelled detections
        for anomaly_type in reconciliation:
            assert reconciliation[anomaly_type]["unlabelled_detections"] == 0


class TestProfileSupport:
    """Test DEV and FULL profile support."""

    def test_dev_profile_supported(self):
        """Verify DEV profile is supported."""
        rng = init_rng()
        master_data = generate_master_data("dev", rng)
        rng = init_rng()
        event_data = generate_events(master_data, "dev", rng)
        rng = init_rng()
        modified_data, ground_truth, _ = inject_anomalies(master_data, event_data, "dev", rng)

        all_data = {**master_data, **modified_data}
        report = validate(all_data, ground_truth, "dev")

        assert report["profile"] == "dev"
        assert report["overall_status"] == "pass"

    def test_full_profile_supported(self):
        """Verify FULL profile is supported."""
        rng = init_rng()
        master_data = generate_master_data("full", rng)
        rng = init_rng()
        event_data = generate_events(master_data, "full", rng)
        rng = init_rng()
        modified_data, ground_truth, _ = inject_anomalies(master_data, event_data, "full", rng)

        all_data = {**master_data, **modified_data}
        report = validate(all_data, ground_truth, "full")

        assert report["profile"] == "full"
        assert report["overall_status"] == "pass"


class TestDeterminism:
    """Test deterministic behavior."""

    def test_repeated_validation_equivalent(self):
        """Verify repeated validation returns equivalent results."""
        rng = init_rng()
        master_data = generate_master_data("dev", rng)
        rng = init_rng()
        event_data = generate_events(master_data, "dev", rng)
        rng = init_rng()
        modified_data, ground_truth, _ = inject_anomalies(master_data, event_data, "dev", rng)

        all_data = {**master_data, **modified_data}

        report1 = validate(all_data, ground_truth, "dev")
        report2 = validate(all_data, ground_truth, "dev")

        assert report1 == report2
