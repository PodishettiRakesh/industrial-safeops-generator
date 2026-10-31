"""
Anomaly injection module.

This module injects labelled anomalies into valid data and generates ground truth.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, Tuple
from safeops.config import (
    get_profile,
    ANOMALY_TYPES,
    ANOMALY_BUDGET_PERCENT,
    TIMESTAMP_FORMAT
)


def inject_anomalies(
    master_data: Dict[str, pd.DataFrame],
    event_data: Dict[str, pd.DataFrame],
    profile: str,
    rng: np.random.Generator
) -> Tuple[Dict[str, pd.DataFrame], pd.DataFrame, Dict]:
    """
    Inject labelled anomalies and return modified data, ground truth, and summary.

    Anomaly allocation (approximately 1% of relevant records):
    - ACK_BEFORE_ALARM: ~1% of acknowledgements
    - IMPOSSIBLE_INTERLOCK: ~1% of machine state events
    - MISSING_CONTEXT: ~1% of incidents
    - REPLAY_FLOOD: 50 replay records (fixed, not percentage-based)
    - UNVERIFIED_CLOSURE: ~1% of closed corrective actions

    Args:
        master_data: Dictionary of master DataFrames.
        event_data: Dictionary of event DataFrames.
        profile: Profile name ('dev' or 'full').
        rng: Random number generator.

    Returns:
        Tuple of:
        - Modified event data dictionary
        - Ground truth DataFrame with columns: target_table, entity_id, anomaly_type, description
        - Injection summary dictionary
    """
    # Create copies to avoid mutating original DataFrames
    event_data = {key: df.copy() for key, df in event_data.items()}

    ground_truth_data = []
    summary = {
        "anomaly_cases": 0,
        "ground_truth_rows": 0,
        "unique_affected_records": 0,
        "added_replay_records": 0,
        "affected_percentage_by_table": {}
    }

    # Extract DataFrames
    acknowledgements = event_data["acknowledgements"]
    machine_state_events = event_data["machine_state_events"]
    incidents = event_data["incidents"]
    alarm_events = event_data["alarm_events"]
    corrective_actions = event_data["corrective_actions"]

    # Inject anomalies in order
    ground_truth_data.extend(_inject_ack_before_alarm(acknowledgements, alarm_events, rng))
    ground_truth_data.extend(_inject_impossible_interlock(machine_state_events, rng))
    ground_truth_data.extend(_inject_missing_context(incidents, rng))
    alarm_events, replay_count, replay_ground_truth = _inject_replay_flood(
        alarm_events,
        master_data["alarm_definitions"],
        profile,
        rng
    )
    event_data["alarm_events"] = alarm_events
    ground_truth_data.extend(replay_ground_truth)
    ground_truth_data.extend(_inject_unverified_closure(corrective_actions, rng))

    # Create ground truth DataFrame
    ground_truth = pd.DataFrame(ground_truth_data)
    ground_truth = ground_truth.sort_values(["target_table", "entity_id"]).reset_index(drop=True)

    # Calculate summary statistics
    summary["anomaly_cases"] = len(ground_truth["anomaly_type"].unique())
    summary["ground_truth_rows"] = len(ground_truth)
    summary["unique_affected_records"] = ground_truth["entity_id"].nunique()
    summary["added_replay_records"] = replay_count

    # Calculate percentages by table
    for table in ground_truth["target_table"].unique():
        table_count = len(ground_truth[ground_truth["target_table"] == table])
        if table == "alarm_events":
            total = len(alarm_events)
        elif table == "acknowledgements":
            total = len(acknowledgements)
        elif table == "machine_state_events":
            total = len(machine_state_events)
        elif table == "incidents":
            total = len(incidents)
        elif table == "corrective_actions":
            total = len(corrective_actions)
        else:
            total = 1
        summary["affected_percentage_by_table"][table] = round(table_count / total * 100, 2)

    return event_data, ground_truth, summary


def _inject_ack_before_alarm(
    acknowledgements: pd.DataFrame,
    alarm_events: pd.DataFrame,
    rng: np.random.Generator
) -> list:
    """
    Inject ACK_BEFORE_ALARM anomalies.

    Select ~1% of acknowledgements and set acknowledged_at earlier than alarm timestamp.
    """
    if len(acknowledgements) == 0:
        return []

    # Create alarm lookup
    alarm_lookup = dict(zip(alarm_events["alarm_event_id"], alarm_events["timestamp"]))

    # Select ~1% of acknowledgements
    num_anomalies = max(1, int(len(acknowledgements) * ANOMALY_BUDGET_PERCENT))
    selected_indices = rng.choice(len(acknowledgements), num_anomalies, replace=False)

    ground_truth = []

    for idx in selected_indices:
        ack = acknowledgements.iloc[idx]
        ack_id = ack["ack_id"]
        alarm_event_id = ack["alarm_event_id"]
        alarm_timestamp = alarm_lookup.get(alarm_event_id)

        if alarm_timestamp is None:
            continue

        # Set acknowledged_at to 1 hour before alarm timestamp
        alarm_dt = datetime.fromisoformat(alarm_timestamp.replace("Z", "+00:00"))
        new_ack_time = (alarm_dt - timedelta(hours=1)).strftime(TIMESTAMP_FORMAT)

        # Modify the acknowledgement
        acknowledgements.at[idx, "acknowledged_at"] = new_ack_time

        ground_truth.append({
            "target_table": "acknowledgements",
            "entity_id": ack_id,
            "anomaly_type": "ACK_BEFORE_ALARM",
            "description": f"Acknowledgement timestamp precedes alarm timestamp"
        })

    return ground_truth


def _inject_impossible_interlock(
    machine_state_events: pd.DataFrame,
    rng: np.random.Generator
) -> list:
    """
    Inject IMPOSSIBLE_INTERLOCK anomalies.

    Select ~1% of machine state events where machine is Operational and set interlock to Bypassed.
    This violates the safety rule: Operational machines must have Secure interlock.
    """
    if len(machine_state_events) == 0:
        return []

    # Filter for Operational state events
    operational_events = machine_state_events[machine_state_events["new_state"] == "Operational"].index.tolist()

    if len(operational_events) == 0:
        return []

    # Select ~1% of operational events
    num_anomalies = max(1, int(len(operational_events) * ANOMALY_BUDGET_PERCENT))
    num_anomalies = min(num_anomalies, len(operational_events))
    selected_indices = rng.choice(operational_events, num_anomalies, replace=False)

    ground_truth = []

    for idx in selected_indices:
        state_event_id = machine_state_events.at[idx, "state_event_id"]

        # Set interlock to Bypassed (unsafe for Operational state)
        machine_state_events.at[idx, "interlock_status"] = "Bypassed"

        ground_truth.append({
            "target_table": "machine_state_events",
            "entity_id": str(state_event_id),
            "anomaly_type": "IMPOSSIBLE_INTERLOCK",
            "description": "Machine Operational with Bypassed interlock (safety rule violation)"
        })

    return ground_truth


def _inject_missing_context(
    incidents: pd.DataFrame,
    rng: np.random.Generator
) -> list:
    """
    Inject MISSING_CONTEXT anomalies.

    Select ~1% of incidents and set alarm_event_id to null.
    """
    if len(incidents) == 0:
        return []

    # Select ~1% of incidents
    num_anomalies = max(1, int(len(incidents) * ANOMALY_BUDGET_PERCENT))
    selected_indices = rng.choice(len(incidents), num_anomalies, replace=False)

    ground_truth = []

    for idx in selected_indices:
        incident_id = incidents.at[idx, "incident_id"]

        # Set alarm_event_id to null
        incidents.at[idx, "alarm_event_id"] = None

        ground_truth.append({
            "target_table": "incidents",
            "entity_id": incident_id,
            "anomaly_type": "MISSING_CONTEXT",
            "description": "Incident missing alarm_event_id reference"
        })

    return ground_truth


def _inject_replay_flood(
    alarm_events: pd.DataFrame,
    alarm_definitions: pd.DataFrame,
    profile: str,
    rng: np.random.Generator
) -> Tuple[pd.DataFrame, int, list]:
    """
    Inject REPLAY_FLOOD anomalies.

    Duplicate 50 contiguous alarm events with new IDs and replay_group_id.
    Ensures final alarm event count matches profile target.

    Returns:
        Tuple of (modified alarm_events DataFrame, replay_count, ground_truth list)
    """
    REPLAY_COUNT = 50

    if len(alarm_events) < REPLAY_COUNT:
        return alarm_events, 0, []

    # Select 50 contiguous events (deterministic selection)
    start_idx = rng.integers(0, len(alarm_events) - REPLAY_COUNT + 1)
    original_events = alarm_events.iloc[start_idx:start_idx + REPLAY_COUNT].copy()

    # Generate replay group ID
    replay_group_id = f"RPG-{start_idx:06d}"

    # Get machine alarm counters for new IDs
    machine_alarm_counters = {}
    for _, event in alarm_events.iterrows():
        alarm_event_id = event["alarm_event_id"]
        # Extract machine_id from format: ALM-MCH-001-000001
        parts = alarm_event_id.split("-")
        machine_id = f"{parts[1]}-{parts[2]}"
        counter = int(parts[3])
        if machine_id not in machine_alarm_counters or counter > machine_alarm_counters[machine_id]:
            machine_alarm_counters[machine_id] = counter

    replay_events = []
    ground_truth = []

    for _, orig_event in original_events.iterrows():
        orig_id = orig_event["alarm_event_id"]
        parts = orig_id.split("-")
        machine_id = f"{parts[1]}-{parts[2]}"

        # Increment counter for this machine
        machine_alarm_counters[machine_id] += 1
        new_counter = machine_alarm_counters[machine_id]
        new_alarm_event_id = f"ALM-{machine_id}-{new_counter:06d}"

        # Assign replay_group_id to both original and replay
        orig_idx = alarm_events[alarm_events["alarm_event_id"] == orig_id].index[0]
        alarm_events.at[orig_idx, "replay_group_id"] = replay_group_id

        # Create replay event
        replay_event = orig_event.copy()
        replay_event["alarm_event_id"] = new_alarm_event_id
        replay_event["replay_group_id"] = replay_group_id

        replay_events.append(replay_event)

        ground_truth.append({
            "target_table": "alarm_events",
            "entity_id": new_alarm_event_id,
            "anomaly_type": "REPLAY_FLOOD",
            "description": f"Replay of {orig_id} in group {replay_group_id}"
        })

    # Append replay events to alarm_events
    replay_df = pd.DataFrame(replay_events)
    alarm_events = pd.concat([alarm_events, replay_df], ignore_index=True)
    alarm_events = alarm_events.sort_values(["timestamp", "alarm_event_id"]).reset_index(drop=True)

    return alarm_events, REPLAY_COUNT, ground_truth


def _inject_unverified_closure(
    corrective_actions: pd.DataFrame,
    rng: np.random.Generator
) -> list:
    """
    Inject UNVERIFIED_CLOSURE anomalies.

    Select ~1% of Closed corrective actions and set verified_at to null.
    """
    if len(corrective_actions) == 0:
        return []

    # Filter for Closed actions
    closed_actions = corrective_actions[corrective_actions["status"] == "Closed"].index.tolist()

    if len(closed_actions) == 0:
        return []

    # Select ~1% of closed actions
    num_anomalies = max(1, int(len(closed_actions) * ANOMALY_BUDGET_PERCENT))
    num_anomalies = min(num_anomalies, len(closed_actions))
    selected_indices = rng.choice(closed_actions, num_anomalies, replace=False)

    ground_truth = []

    for idx in selected_indices:
        action_id = corrective_actions.at[idx, "action_id"]

        # Set verified_at to null
        corrective_actions.at[idx, "verified_at"] = None

        ground_truth.append({
            "target_table": "corrective_actions",
            "entity_id": action_id,
            "anomaly_type": "UNVERIFIED_CLOSURE",
            "description": "Closed corrective action without verification timestamp"
        })

    return ground_truth
