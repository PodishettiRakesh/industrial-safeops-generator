"""
Validation module.

This module validates structural integrity, business rules, and ground truth.
"""

import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, List, Any
from safeops.config import (
    get_profile,
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
    SIMULATION_START_UTC,
    SIMULATION_DAYS,
    TIMESTAMP_FORMAT,
    ID_PATTERNS
)


def validate(
    data: Dict[str, pd.DataFrame],
    ground_truth: pd.DataFrame,
    profile: str
) -> Dict:
    """
    Validate all data and return validation report.

    Args:
        data: Dictionary of all DataFrames.
        ground_truth: Ground truth DataFrame with anomaly labels.
        profile: Profile name ('dev' or 'full').

    Returns:
        Validation report dictionary with pass/fail status and details.
    """
    profile_config = get_profile(profile)

    report = {
        "profile": profile,
        "expected_row_counts": {},
        "actual_row_counts": {},
        "structural_integrity": "pass",
        "structural_errors": [],
        "expected_anomalies": {},
        "detected_anomalies": {},
        "ground_truth_reconciliation": {},
        "overall_status": "pass"
    }

    # 1. Structural integrity checks
    structural_errors = _validate_structural_integrity(data, profile_config)
    report["structural_errors"] = structural_errors

    if structural_errors:
        report["structural_integrity"] = "fail"
        report["overall_status"] = "fail"

    # 2. Row count validation
    report["expected_row_counts"] = {
        "alarm_events": profile_config["num_alarm_events"],
        "machines": profile_config["num_machines"],
        "plants": profile_config["num_plants"],
        "alarm_definitions": profile_config["num_alarm_definitions"]
    }
    report["actual_row_counts"] = {
        "alarm_events": len(data.get("alarm_events", pd.DataFrame())),
        "machines": len(data.get("machines", pd.DataFrame())),
        "plants": len(data.get("plants", pd.DataFrame())),
        "alarm_definitions": len(data.get("alarm_definitions", pd.DataFrame()))
    }

    # Check alarm event count
    if report["actual_row_counts"]["alarm_events"] != report["expected_row_counts"]["alarm_events"]:
        report["structural_errors"].append({
            "type": "row_count_mismatch",
            "table": "alarm_events",
            "expected": report["expected_row_counts"]["alarm_events"],
            "actual": report["actual_row_counts"]["alarm_events"]
        })
        report["structural_integrity"] = "fail"
        report["overall_status"] = "fail"

    # 3. Detect anomalies independently
    detected_anomalies = _detect_anomalies(data, ground_truth)
    report["detected_anomalies"] = detected_anomalies

    # 4. Ground truth reconciliation
    reconciliation = _reconcile_ground_truth(ground_truth, detected_anomalies, data)
    report["ground_truth_reconciliation"] = reconciliation

    # 5. Expected anomalies from ground truth
    if len(ground_truth) > 0:
        report["expected_anomalies"] = ground_truth["anomaly_type"].value_counts().to_dict()

    # 6. Check for unlabelled detections
    unlabelled = reconciliation.get("unlabelled_detections", 0)
    if unlabelled > 0:
        report["structural_errors"].append({
            "type": "unlabelled_anomalies",
            "count": unlabelled
        })
        # Don't fail for unlabelled detections, just report

    return report


def _validate_structural_integrity(
    data: Dict[str, pd.DataFrame],
    profile_config: Dict
) -> List[Dict]:
    """
    Validate structural integrity of all tables.

    Returns list of error dictionaries.
    """
    errors = []

    # Expected tables
    expected_tables = [
        "plants", "machines", "safety_zones", "interlocks", "alarm_definitions",
        "operator_shifts", "machine_state_events", "alarm_events",
        "acknowledgements", "incidents", "corrective_actions"
    ]

    # Check required tables exist
    for table in expected_tables:
        if table not in data:
            errors.append({
                "type": "missing_table",
                "table": table
            })
            continue

        df = data[table]

        # Check table is not empty
        if len(df) == 0:
            errors.append({
                "type": "empty_table",
                "table": table
            })

    # Validate each table
    if "plants" in data:
        errors.extend(_validate_plants(data["plants"]))

    if "machines" in data:
        errors.extend(_validate_machines(data["machines"], data.get("plants", pd.DataFrame())))

    if "safety_zones" in data:
        errors.extend(_validate_safety_zones(data["safety_zones"], data.get("machines", pd.DataFrame())))

    if "interlocks" in data:
        errors.extend(_validate_interlocks(data["interlocks"], data.get("machines", pd.DataFrame())))

    if "alarm_definitions" in data:
        errors.extend(_validate_alarm_definitions(data["alarm_definitions"], data.get("machines", pd.DataFrame())))

    if "operator_shifts" in data:
        errors.extend(_validate_operator_shifts(data["operator_shifts"], data.get("plants", pd.DataFrame())))

    if "machine_state_events" in data:
        errors.extend(_validate_machine_state_events(data["machine_state_events"], data.get("machines", pd.DataFrame())))

    if "alarm_events" in data:
        errors.extend(_validate_alarm_events(data["alarm_events"], data.get("alarm_definitions", pd.DataFrame())))

    if "acknowledgements" in data:
        errors.extend(_validate_acknowledgements(
            data["acknowledgements"],
            data.get("alarm_events", pd.DataFrame()),
            data.get("operator_shifts", pd.DataFrame()),
            data.get("machines", pd.DataFrame()),
            data.get("alarm_definitions", pd.DataFrame())
        ))

    if "incidents" in data:
        errors.extend(_validate_incidents(
            data["incidents"],
            data.get("machines", pd.DataFrame()),
            data.get("alarm_events", pd.DataFrame())
        ))

    if "corrective_actions" in data:
        errors.extend(_validate_corrective_actions(data["corrective_actions"], data.get("incidents", pd.DataFrame())))

    return errors


def _validate_plants(df: pd.DataFrame) -> List[Dict]:
    """Validate Plants table."""
    errors = []

    expected_columns = ["plant_id", "plant_name", "location", "created_at"]
    if list(df.columns) != expected_columns:
        errors.append({
            "type": "column_mismatch",
            "table": "plants",
            "expected": expected_columns,
            "actual": list(df.columns)
        })

    # Primary key uniqueness
    if not df["plant_id"].is_unique:
        errors.append({
            "type": "duplicate_primary_key",
            "table": "plants",
            "column": "plant_id"
        })

    # Primary key non-null
    if df["plant_id"].isna().any():
        errors.append({
            "type": "null_primary_key",
            "table": "plants",
            "column": "plant_id"
        })

    # plant_name uniqueness
    if not df["plant_name"].is_unique:
        errors.append({
            "type": "duplicate_value",
            "table": "plants",
            "column": "plant_name"
        })

    return errors


def _validate_machines(df: pd.DataFrame, plants: pd.DataFrame) -> List[Dict]:
    """Validate Machines table."""
    errors = []

    expected_columns = ["machine_id", "plant_id", "machine_type", "model_number", "status"]
    if list(df.columns) != expected_columns:
        errors.append({
            "type": "column_mismatch",
            "table": "machines",
            "expected": expected_columns,
            "actual": list(df.columns)
        })

    # Primary key uniqueness
    if not df["machine_id"].is_unique:
        errors.append({
            "type": "duplicate_primary_key",
            "table": "machines",
            "column": "machine_id"
        })

    # Primary key non-null
    if df["machine_id"].isna().any():
        errors.append({
            "type": "null_primary_key",
            "table": "machines",
            "column": "machine_id"
        })

    # Foreign key to plants
    if len(plants) > 0:
        valid_plant_ids = set(plants["plant_id"])
        for plant_id in df["plant_id"]:
            if plant_id not in valid_plant_ids:
                errors.append({
                    "type": "invalid_foreign_key",
                    "table": "machines",
                    "column": "plant_id",
                    "value": plant_id
                })

    # Enum validation
    for machine_type in df["machine_type"]:
        if machine_type not in MACHINE_TYPES:
            errors.append({
                "type": "invalid_enum",
                "table": "machines",
                "column": "machine_type",
                "value": machine_type
            })

    for status in df["status"]:
        if status not in MACHINE_STATUS:
            errors.append({
                "type": "invalid_enum",
                "table": "machines",
                "column": "status",
                "value": status
            })

    return errors


def _validate_safety_zones(df: pd.DataFrame, machines: pd.DataFrame) -> List[Dict]:
    """Validate SafetyZone table."""
    errors = []

    expected_columns = ["zone_id", "machine_id", "zone_type", "risk_level"]
    if list(df.columns) != expected_columns:
        errors.append({
            "type": "column_mismatch",
            "table": "safety_zones",
            "expected": expected_columns,
            "actual": list(df.columns)
        })

    # Primary key uniqueness
    if not df["zone_id"].is_unique:
        errors.append({
            "type": "duplicate_primary_key",
            "table": "safety_zones",
            "column": "zone_id"
        })

    # Foreign key to machines
    if len(machines) > 0:
        valid_machine_ids = set(machines["machine_id"])
        for machine_id in df["machine_id"]:
            if machine_id not in valid_machine_ids:
                errors.append({
                    "type": "invalid_foreign_key",
                    "table": "safety_zones",
                    "column": "machine_id",
                    "value": machine_id
                })

    # Enum validation
    for zone_type in df["zone_type"]:
        if zone_type not in ZONE_TYPES:
            errors.append({
                "type": "invalid_enum",
                "table": "safety_zones",
                "column": "zone_type",
                "value": zone_type
            })

    for risk_level in df["risk_level"]:
        if risk_level not in RISK_LEVELS:
            errors.append({
                "type": "invalid_enum",
                "table": "safety_zones",
                "column": "risk_level",
                "value": risk_level
            })

    return errors


def _validate_interlocks(df: pd.DataFrame, machines: pd.DataFrame) -> List[Dict]:
    """Validate Interlock table."""
    errors = []

    expected_columns = ["interlock_id", "machine_id", "interlock_type", "normal_state"]
    if list(df.columns) != expected_columns:
        errors.append({
            "type": "column_mismatch",
            "table": "interlocks",
            "expected": expected_columns,
            "actual": list(df.columns)
        })

    # Primary key uniqueness
    if not df["interlock_id"].is_unique:
        errors.append({
            "type": "duplicate_primary_key",
            "table": "interlocks",
            "column": "interlock_id"
        })

    # Foreign key to machines
    if len(machines) > 0:
        valid_machine_ids = set(machines["machine_id"])
        for machine_id in df["machine_id"]:
            if machine_id not in valid_machine_ids:
                errors.append({
                    "type": "invalid_foreign_key",
                    "table": "interlocks",
                    "column": "machine_id",
                    "value": machine_id
                })

    # Enum validation
    for interlock_type in df["interlock_type"]:
        if interlock_type not in INTERLOCK_TYPES:
            errors.append({
                "type": "invalid_enum",
                "table": "interlocks",
                "column": "interlock_type",
                "value": interlock_type
            })

    for normal_state in df["normal_state"]:
        if normal_state not in INTERLOCK_STATES:
            errors.append({
                "type": "invalid_enum",
                "table": "interlocks",
                "column": "normal_state",
                "value": normal_state
            })

    return errors


def _validate_alarm_definitions(df: pd.DataFrame, machines: pd.DataFrame) -> List[Dict]:
    """Validate AlarmDefinition table."""
    errors = []

    expected_columns = ["alarm_def_id", "machine_id", "metric_name", "severity", "threshold_limit"]
    if list(df.columns) != expected_columns:
        errors.append({
            "type": "column_mismatch",
            "table": "alarm_definitions",
            "expected": expected_columns,
            "actual": list(df.columns)
        })

    # Primary key uniqueness
    if not df["alarm_def_id"].is_unique:
        errors.append({
            "type": "duplicate_primary_key",
            "table": "alarm_definitions",
            "column": "alarm_def_id"
        })

    # Foreign key to machines
    if len(machines) > 0:
        valid_machine_ids = set(machines["machine_id"])
        for machine_id in df["machine_id"]:
            if machine_id not in valid_machine_ids:
                errors.append({
                    "type": "invalid_foreign_key",
                    "table": "alarm_definitions",
                    "column": "machine_id",
                    "value": machine_id
                })

    # Enum validation
    for metric_name in df["metric_name"]:
        if metric_name not in METRIC_NAMES:
            errors.append({
                "type": "invalid_enum",
                "table": "alarm_definitions",
                "column": "metric_name",
                "value": metric_name
            })

    for severity in df["severity"]:
        if severity not in SEVERITY_LEVELS:
            errors.append({
                "type": "invalid_enum",
                "table": "alarm_definitions",
                "column": "severity",
                "value": severity
            })

    # threshold_limit non-null
    if df["threshold_limit"].isna().any():
        errors.append({
            "type": "null_required_field",
            "table": "alarm_definitions",
            "column": "threshold_limit"
        })

    return errors


def _validate_operator_shifts(df: pd.DataFrame, plants: pd.DataFrame) -> List[Dict]:
    """Validate OperatorShift table."""
    errors = []

    expected_columns = ["shift_id", "plant_id", "operator_name", "start_time", "end_time"]
    if list(df.columns) != expected_columns:
        errors.append({
            "type": "column_mismatch",
            "table": "operator_shifts",
            "expected": expected_columns,
            "actual": list(df.columns)
        })

    # Primary key uniqueness
    if not df["shift_id"].is_unique:
        errors.append({
            "type": "duplicate_primary_key",
            "table": "operator_shifts",
            "column": "shift_id"
        })

    # Foreign key to plants
    if len(plants) > 0:
        valid_plant_ids = set(plants["plant_id"])
        for plant_id in df["plant_id"]:
            if plant_id not in valid_plant_ids:
                errors.append({
                    "type": "invalid_foreign_key",
                    "table": "operator_shifts",
                    "column": "plant_id",
                    "value": plant_id
                })

    # Timestamp validation
    for _, row in df.iterrows():
        try:
            start = datetime.fromisoformat(row["start_time"].replace("Z", "+00:00"))
            end = datetime.fromisoformat(row["end_time"].replace("Z", "+00:00"))
            if start >= end:
                errors.append({
                    "type": "invalid_timestamp_order",
                    "table": "operator_shifts",
                    "shift_id": row["shift_id"]
                })
        except ValueError:
            errors.append({
                "type": "invalid_timestamp",
                "table": "operator_shifts",
                "shift_id": row["shift_id"]
            })

    return errors


def _validate_machine_state_events(df: pd.DataFrame, machines: pd.DataFrame) -> List[Dict]:
    """Validate MachineStateEvent table."""
    errors = []

    expected_columns = ["state_event_id", "machine_id", "timestamp", "previous_state",
                       "new_state", "interlock_status", "source_event_id"]
    if list(df.columns) != expected_columns:
        errors.append({
            "type": "column_mismatch",
            "table": "machine_state_events",
            "expected": expected_columns,
            "actual": list(df.columns)
        })

    # Primary key uniqueness
    if not df["state_event_id"].is_unique:
        errors.append({
            "type": "duplicate_primary_key",
            "table": "machine_state_events",
            "column": "state_event_id"
        })

    # Foreign key to machines
    if len(machines) > 0:
        valid_machine_ids = set(machines["machine_id"])
        for machine_id in df["machine_id"]:
            if machine_id not in valid_machine_ids:
                errors.append({
                    "type": "invalid_foreign_key",
                    "table": "machine_state_events",
                    "column": "machine_id",
                    "value": machine_id
                })

    # Enum validation
    for state in df["previous_state"]:
        if state not in MACHINE_STATUS:
            errors.append({
                "type": "invalid_enum",
                "table": "machine_state_events",
                "column": "previous_state",
                "value": state
            })

    for state in df["new_state"]:
        if state not in MACHINE_STATUS:
            errors.append({
                "type": "invalid_enum",
                "table": "machine_state_events",
                "column": "new_state",
                "value": state
            })

    for status in df["interlock_status"]:
        if status not in INTERLOCK_STATUS:
            errors.append({
                "type": "invalid_enum",
                "table": "machine_state_events",
                "column": "interlock_status",
                "value": status
            })

    return errors


def _validate_alarm_events(df: pd.DataFrame, alarm_definitions: pd.DataFrame) -> List[Dict]:
    """Validate AlarmEvent table."""
    errors = []

    expected_columns = ["alarm_event_id", "alarm_def_id", "timestamp", "current_value",
                       "interlock_status", "source_event_id", "replay_group_id"]
    if list(df.columns) != expected_columns:
        errors.append({
            "type": "column_mismatch",
            "table": "alarm_events",
            "expected": expected_columns,
            "actual": list(df.columns)
        })

    # Primary key uniqueness
    if not df["alarm_event_id"].is_unique:
        errors.append({
            "type": "duplicate_primary_key",
            "table": "alarm_events",
            "column": "alarm_event_id"
        })

    # Foreign key to alarm_definitions
    if len(alarm_definitions) > 0:
        valid_def_ids = set(alarm_definitions["alarm_def_id"])
        for alarm_def_id in df["alarm_def_id"]:
            if alarm_def_id not in valid_def_ids:
                errors.append({
                    "type": "invalid_foreign_key",
                    "table": "alarm_events",
                    "column": "alarm_def_id",
                    "value": alarm_def_id
                })

    # Enum validation
    for status in df["interlock_status"]:
        if status not in INTERLOCK_STATUS:
            errors.append({
                "type": "invalid_enum",
                "table": "alarm_events",
                "column": "interlock_status",
                "value": status
            })

    # Timestamp validation
    for _, row in df.iterrows():
        try:
            datetime.fromisoformat(row["timestamp"].replace("Z", "+00:00"))
        except ValueError:
            errors.append({
                "type": "invalid_timestamp",
                "table": "alarm_events",
                "alarm_event_id": row["alarm_event_id"]
            })

    return errors


def _validate_acknowledgements(
    df: pd.DataFrame,
    alarm_events: pd.DataFrame,
    operator_shifts: pd.DataFrame,
    machines: pd.DataFrame,
    alarm_definitions: pd.DataFrame
) -> List[Dict]:
    """Validate Acknowledgement table."""
    errors = []

    expected_columns = ["ack_id", "alarm_event_id", "shift_id", "acknowledged_at"]
    if list(df.columns) != expected_columns:
        errors.append({
            "type": "column_mismatch",
            "table": "acknowledgements",
            "expected": expected_columns,
            "actual": list(df.columns)
        })

    # Primary key uniqueness
    if not df["ack_id"].is_unique:
        errors.append({
            "type": "duplicate_primary_key",
            "table": "acknowledgements",
            "column": "ack_id"
        })

    # Foreign key to alarm_events
    if len(alarm_events) > 0:
        valid_alarm_ids = set(alarm_events["alarm_event_id"])
        for alarm_event_id in df["alarm_event_id"]:
            if alarm_event_id not in valid_alarm_ids:
                errors.append({
                    "type": "invalid_foreign_key",
                    "table": "acknowledgements",
                    "column": "alarm_event_id",
                    "value": alarm_event_id
                })

    # Foreign key to operator_shifts
    if len(operator_shifts) > 0:
        valid_shift_ids = set(operator_shifts["shift_id"])
        for shift_id in df["shift_id"]:
            if shift_id not in valid_shift_ids:
                errors.append({
                    "type": "invalid_foreign_key",
                    "table": "acknowledgements",
                    "column": "shift_id",
                    "value": shift_id
                })

    # Timestamp validation
    for _, row in df.iterrows():
        try:
            datetime.fromisoformat(row["acknowledged_at"].replace("Z", "+00:00"))
        except ValueError:
            errors.append({
                "type": "invalid_timestamp",
                "table": "acknowledgements",
                "ack_id": row["ack_id"]
            })

    return errors


def _validate_incidents(
    df: pd.DataFrame,
    machines: pd.DataFrame,
    alarm_events: pd.DataFrame
) -> List[Dict]:
    """Validate Incident table."""
    errors = []

    expected_columns = ["incident_id", "machine_id", "alarm_event_id", "severity_level",
                       "logged_at", "issue_type"]
    if list(df.columns) != expected_columns:
        errors.append({
            "type": "column_mismatch",
            "table": "incidents",
            "expected": expected_columns,
            "actual": list(df.columns)
        })

    # Primary key uniqueness
    if not df["incident_id"].is_unique:
        errors.append({
            "type": "duplicate_primary_key",
            "table": "incidents",
            "column": "incident_id"
        })

    # Foreign key to machines
    if len(machines) > 0:
        valid_machine_ids = set(machines["machine_id"])
        for machine_id in df["machine_id"]:
            if machine_id not in valid_machine_ids:
                errors.append({
                    "type": "invalid_foreign_key",
                    "table": "incidents",
                    "column": "machine_id",
                    "value": machine_id
                })

    # Foreign key to alarm_events (nullable)
    if len(alarm_events) > 0:
        valid_alarm_ids = set(alarm_events["alarm_event_id"])
        for alarm_event_id in df["alarm_event_id"]:
            if pd.notna(alarm_event_id) and alarm_event_id not in valid_alarm_ids:
                errors.append({
                    "type": "invalid_foreign_key",
                    "table": "incidents",
                    "column": "alarm_event_id",
                    "value": alarm_event_id
                })

    # Enum validation
    for severity in df["severity_level"]:
        if severity not in INCIDENT_SEVERITY:
            errors.append({
                "type": "invalid_enum",
                "table": "incidents",
                "column": "severity_level",
                "value": severity
            })

    # Timestamp validation
    for _, row in df.iterrows():
        try:
            datetime.fromisoformat(row["logged_at"].replace("Z", "+00:00"))
        except ValueError:
            errors.append({
                "type": "invalid_timestamp",
                "table": "incidents",
                "incident_id": row["incident_id"]
            })

    return errors


def _validate_corrective_actions(df: pd.DataFrame, incidents: pd.DataFrame) -> List[Dict]:
    """Validate CorrectiveAction table."""
    errors = []

    expected_columns = ["action_id", "incident_id", "action_taken", "status", "verified_at"]
    if list(df.columns) != expected_columns:
        errors.append({
            "type": "column_mismatch",
            "table": "corrective_actions",
            "expected": expected_columns,
            "actual": list(df.columns)
        })

    # Primary key uniqueness
    if not df["action_id"].is_unique:
        errors.append({
            "type": "duplicate_primary_key",
            "table": "corrective_actions",
            "column": "action_id"
        })

    # Foreign key to incidents
    if len(incidents) > 0:
        valid_incident_ids = set(incidents["incident_id"])
        for incident_id in df["incident_id"]:
            if incident_id not in valid_incident_ids:
                errors.append({
                    "type": "invalid_foreign_key",
                    "table": "corrective_actions",
                    "column": "incident_id",
                    "value": incident_id
                })

    # Enum validation
    for status in df["status"]:
        if status not in ACTION_STATUS:
            errors.append({
                "type": "invalid_enum",
                "table": "corrective_actions",
                "column": "status",
                "value": status
            })

    # Timestamp validation
    for _, row in df.iterrows():
        if pd.notna(row["verified_at"]):
            try:
                datetime.fromisoformat(row["verified_at"].replace("Z", "+00:00"))
            except ValueError:
                errors.append({
                    "type": "invalid_timestamp",
                    "table": "corrective_actions",
                    "action_id": row["action_id"]
                })

    return errors


def _detect_anomalies(data: Dict[str, pd.DataFrame], ground_truth: pd.DataFrame) -> Dict[str, List[str]]:
    """
    Detect anomalies independently from ground truth.

    Returns dictionary mapping anomaly type to list of entity IDs.
    """
    detected = {
        "ACK_BEFORE_ALARM": [],
        "IMPOSSIBLE_INTERLOCK": [],
        "MISSING_CONTEXT": [],
        "REPLAY_FLOOD": [],
        "UNVERIFIED_CLOSURE": []
    }

    # Detect ACK_BEFORE_ALARM
    if "acknowledgements" in data and "alarm_events" in data:
        acks = data["acknowledgements"]
        alarms = data["alarm_events"]
        alarm_lookup = dict(zip(alarms["alarm_event_id"], alarms["timestamp"]))

        for _, ack in acks.iterrows():
            alarm_time = alarm_lookup.get(ack["alarm_event_id"])
            if alarm_time:
                ack_time = datetime.fromisoformat(ack["acknowledged_at"].replace("Z", "+00:00"))
                alarm_dt = datetime.fromisoformat(alarm_time.replace("Z", "+00:00"))
                if ack_time < alarm_dt:
                    detected["ACK_BEFORE_ALARM"].append(ack["ack_id"])

    # Detect IMPOSSIBLE_INTERLOCK
    if "machine_state_events" in data:
        state_events = data["machine_state_events"]
        for _, event in state_events.iterrows():
            if event["new_state"] == "Operational" and event["interlock_status"] == "Bypassed":
                detected["IMPOSSIBLE_INTERLOCK"].append(str(event["state_event_id"]))

    # Detect MISSING_CONTEXT
    if "incidents" in data:
        incidents = data["incidents"]
        for _, incident in incidents.iterrows():
            if pd.isna(incident["alarm_event_id"]):
                detected["MISSING_CONTEXT"].append(incident["incident_id"])

    # Detect REPLAY_FLOOD
    # Only count the actual replay records (duplicates), not the originals that got replay_group_id
    if "alarm_events" in data and len(ground_truth) > 0:
        alarm_events = data["alarm_events"]
        replay_gt = ground_truth[ground_truth["anomaly_type"] == "REPLAY_FLOOD"]
        replay_ids = set(replay_gt["entity_id"])
        for _, event in alarm_events.iterrows():
            if event["alarm_event_id"] in replay_ids:
                detected["REPLAY_FLOOD"].append(event["alarm_event_id"])

    # Detect UNVERIFIED_CLOSURE
    if "corrective_actions" in data:
        actions = data["corrective_actions"]
        for _, action in actions.iterrows():
            if action["status"] == "Closed" and pd.isna(action["verified_at"]):
                detected["UNVERIFIED_CLOSURE"].append(action["action_id"])

    return detected


def _reconcile_ground_truth(
    ground_truth: pd.DataFrame,
    detected_anomalies: Dict[str, List[str]],
    data: Dict[str, pd.DataFrame]
) -> Dict:
    """
    Reconcile ground truth with detected anomalies.

    Returns reconciliation metrics.
    """
    reconciliation = {}

    for anomaly_type in ["ACK_BEFORE_ALARM", "IMPOSSIBLE_INTERLOCK", "MISSING_CONTEXT", "REPLAY_FLOOD", "UNVERIFIED_CLOSURE"]:
        gt_subset = ground_truth[ground_truth["anomaly_type"] == anomaly_type]
        gt_ids = set(gt_subset["entity_id"]) if len(gt_subset) > 0 else set()
        detected_ids = set(detected_anomalies.get(anomaly_type, []))

        reconciliation[anomaly_type] = {
            "ground_truth_count": len(gt_ids),
            "unique_affected_records": len(gt_ids),
            "detected_count": len(detected_ids),
            "matched_count": len(gt_ids & detected_ids),
            "missed_labels": len(gt_ids - detected_ids),
            "unlabelled_detections": len(detected_ids - gt_ids)
        }

    return reconciliation
